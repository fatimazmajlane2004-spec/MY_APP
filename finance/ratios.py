"""
Calcul des agrégats comptables et des ratios financiers.

Les fonctions de ce module ne font aucun affichage : elles reçoivent un
dictionnaire ``{code_poste: montant}`` et renvoient des valeurs numériques.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Mapping, Optional

from .referentiel import POSTES_BILAN, POSTES_CPC, RATIOS, RATIOS_PAR_CODE

VALEUR_NULLE = 1e-9   # en dessous, on considère que le dénominateur est nul
JOURS = 360.0         # année commerciale


# ---------------------------------------------------------------------------
# Outils
# ---------------------------------------------------------------------------

def nombre(valeur) -> float:
    """Convertit une saisie (str, None, NaN...) en float robuste."""
    if valeur is None:
        return 0.0
    if isinstance(valeur, str):
        valeur = valeur.replace(" ", "").replace("\u00a0", "").replace(",", ".")
    try:
        v = float(valeur)
    except (TypeError, ValueError):
        return 0.0
    if math.isnan(v) or math.isinf(v):
        return 0.0
    return v


def _div(num: Optional[float], den: Optional[float], defaut: Optional[float] = None) -> Optional[float]:
    """Division protégée : renvoie ``defaut`` si le dénominateur est nul."""
    if num is None or den is None:
        return defaut
    if abs(den) < VALEUR_NULLE:
        return defaut
    return num / den


def _moyenne(a: float, b: Optional[float]) -> float:
    """Moyenne des valeurs disponibles (bilan d'ouverture utile pour les ratios de rotation)."""
    if b is None:
        return a
    return (a + b) / 2.0


def _somme(postes: Mapping[str, float], codes: Iterable[str]) -> float:
    return sum(nombre(postes.get(c)) for c in codes)


# ---------------------------------------------------------------------------
# Agrégats
# ---------------------------------------------------------------------------

def agreger_bilan(postes: Mapping[str, float]) -> Dict[str, float]:
    """Regroupe les postes du bilan en masses significatives."""
    immo = _somme(postes, ["IMMO_INCORP_CORP", "IMMO_FINANCIERES"])
    actif_circulant = _somme(postes, ["STOCKS", "CLIENTS", "AUTRES_CREANCES"])
    tresorerie_actif = _somme(postes, ["VMP", "DISPONIBILITES"])

    capitaux_propres = _somme(postes, ["CAPITAL", "RESERVES", "RESULTAT"])
    dettes_financieres = _somme(postes, ["EMPRUNTS"])
    passif_circulant = _somme(postes, ["FOURNISSEURS", "DETTES_SOCIALES", "DETTES_FISCALES", "AUTRES_DETTES_CT"])
    tresorerie_passif = _somme(postes, ["CONCOURS_BANCAIRES"])

    return {
        "immobilisations": immo,
        "actif_circulant": actif_circulant,
        "tresorerie_actif": tresorerie_actif,
        "total_actif": immo + actif_circulant + tresorerie_actif,
        "capitaux_propres": capitaux_propres,
        "dettes_financieres": dettes_financieres,
        "passif_circulant": passif_circulant,
        "tresorerie_passif": tresorerie_passif,
        "capitaux_permanents": capitaux_propres + dettes_financieres,
        "total_dettes": dettes_financieres + passif_circulant + tresorerie_passif,
        "total_passif": capitaux_propres + dettes_financieres + passif_circulant + tresorerie_passif,
        "dettes_ct_total": passif_circulant + tresorerie_passif,
        "stocks": nombre(postes.get("STOCKS")),
        "clients": nombre(postes.get("CLIENTS")),
        "fournisseurs": nombre(postes.get("FOURNISSEURS")),
        "autres_creances": nombre(postes.get("AUTRES_CREANCES")),
    }


def agreger_cpc(postes: Mapping[str, float]) -> Dict[str, float]:
    """Regroupe les postes du CPC en soldes de gestion."""
    ca = nombre(postes.get("CA"))
    autres_produits = nombre(postes.get("AUTRES_PRODUITS"))
    achats = nombre(postes.get("ACHATS"))
    charges_externes = nombre(postes.get("CHARGES_EXTERNES"))
    personnel = nombre(postes.get("PERSONNEL"))
    impots_taxes = nombre(postes.get("IMPOTS_TAXES"))
    dotations = nombre(postes.get("DOTATIONS"))
    produits_fin = nombre(postes.get("PRODUITS_FIN"))
    charges_fin = nombre(postes.get("CHARGES_FIN"))
    impot = nombre(postes.get("IMPOT_RESULTAT"))

    produits_exploitation = ca + autres_produits
    charges_exploitation = achats + charges_externes + personnel + impots_taxes + dotations
    resultat_exploitation = produits_exploitation - charges_exploitation
    resultat_financier = produits_fin - charges_fin
    resultat_avant_impot = resultat_exploitation + resultat_financier
    resultat_net = resultat_avant_impot - impot

    valeur_ajoutee = ca + autres_produits - achats - charges_externes
    ebe = resultat_exploitation + dotations          # excédent brut d'exploitation
    caf = resultat_net + dotations                   # capacité d'autofinancement

    return {
        "ca": ca,
        "autres_produits": autres_produits,
        "achats": achats,
        "charges_externes": charges_externes,
        "personnel": personnel,
        "impots_taxes": impots_taxes,
        "dotations": dotations,
        "produits_fin": produits_fin,
        "charges_fin": charges_fin,
        "impot": impot,
        "produits_exploitation": produits_exploitation,
        "charges_exploitation": charges_exploitation,
        "resultat_exploitation": resultat_exploitation,
        "resultat_financier": resultat_financier,
        "resultat_avant_impot": resultat_avant_impot,
        "resultat_net": resultat_net,
        "valeur_ajoutee": valeur_ajoutee,
        "ebe": ebe,
        "caf": caf,
    }


# ---------------------------------------------------------------------------
# Ratios
# ---------------------------------------------------------------------------

@dataclass
class ResultatRatios:
    """Valeurs des ratios pour l'exercice N (et N-1 si disponible)."""

    valeurs: Dict[str, Optional[float]] = field(default_factory=dict)
    valeurs_n1: Dict[str, Optional[float]] = field(default_factory=dict)
    bilan: Dict[str, float] = field(default_factory=dict)
    bilan_n1: Optional[Dict[str, float]] = None
    cpc: Dict[str, float] = field(default_factory=dict)
    cpc_n1: Optional[Dict[str, float]] = None
    fonds_roulement: float = 0.0
    bfr: float = 0.0
    tresorerie_nette: float = 0.0
    fonds_roulement_n1: Optional[float] = None
    bfr_n1: Optional[float] = None
    tresorerie_nette_n1: Optional[float] = None

    def avec_n1(self) -> bool:
        return self.bilan_n1 is not None and self.cpc_n1 is not None


def calculer_ratios(
    postes_bilan: Mapping[str, float],
    postes_cpc: Mapping[str, float],
    postes_bilan_n1: Optional[Mapping[str, float]] = None,
    postes_cpc_n1: Optional[Mapping[str, float]] = None,
    taux_tva: float = 0.20,
) -> ResultatRatios:
    """Calcule tous les ratios pour l'exercice N (et N-1 en option).

    ``taux_tva`` sert uniquement à remettre les flux d'achats en TTC pour le
    délai fournisseurs (les dettes fournisseurs sont comptabilisées TTC).
    """
    bilan = agreger_bilan(postes_bilan)
    cpc = agreger_cpc(postes_cpc)

    bilan_n1 = agreger_bilan(postes_bilan_n1) if postes_bilan_n1 else None
    cpc_n1 = agreger_cpc(postes_cpc_n1) if postes_cpc_n1 else None

    res = ResultatRatios(
        bilan=bilan,
        bilan_n1=bilan_n1,
        cpc=cpc,
        cpc_n1=cpc_n1,
    )

    def _bloc(b: Dict[str, float], c: Dict[str, float], b_prec, c_prec) -> Dict[str, Optional[float]]:
        """Calcule les ratios d'un exercice. ``b_prec``/``c_prec`` servent aux moyennes."""
        v: Dict[str, Optional[float]] = {}

        fr = b["capitaux_permanents"] - b["immobilisations"]
        bfr = (b["stocks"] + b["clients"] + b["autres_creances"]) - b["passif_circulant"]
        treso_nette = b["tresorerie_actif"] - b["tresorerie_passif"]

        ca = c["ca"]
        actif_moyen = _moyenne(b["total_actif"], b_prec["total_actif"] if b_prec else None)
        cp_moyens = _moyenne(b["capitaux_propres"], b_prec["capitaux_propres"] if b_prec else None)
        stock_moyen = _moyenne(b["stocks"], b_prec["stocks"] if b_prec else None)
        clients_moyens = _moyenne(b["clients"], b_prec["clients"] if b_prec else None)
        fournisseurs_moyens = _moyenne(b["fournisseurs"], b_prec["fournisseurs"] if b_prec else None)

        # --- Liquidité -----------------------------------------------------
        v["LIQ_GENERALE"] = _div(b["actif_circulant"] + b["tresorerie_actif"], b["passif_circulant"] + b["tresorerie_passif"])
        v["LIQ_REDUITE"] = _div((b["actif_circulant"] - b["stocks"]) + b["tresorerie_actif"], b["passif_circulant"] + b["tresorerie_passif"])
        v["LIQ_IMMEDIATE"] = _div(b["tresorerie_actif"], b["passif_circulant"] + b["tresorerie_passif"])
        v["TRESO_NETTE_CA"] = _div(treso_nette * 100.0, ca)
        v["FONDS_ROULEMENT"] = fr
        v["BFR"] = bfr

        # --- Solvabilité ---------------------------------------------------
        v["AUTONOMIE_FINANCIERE"] = _div(b["capitaux_propres"] * 100.0, b["total_passif"])
        v["SOLVABILITE_GENERALE"] = _div(b["capitaux_propres"], b["total_dettes"])
        v["LEVIER"] = _div(b["dettes_financieres"], b["capitaux_propres"])
        # Une capacité de remboursement n'a de sens que si l'entreprise dégage de la trésorerie
        if abs(b["dettes_financieres"]) < VALEUR_NULLE:
            v["CAPACITE_REMBOURSEMENT"] = 0.0
        else:
            v["CAPACITE_REMBOURSEMENT"] = _div(b["dettes_financieres"], c["caf"]) if c["caf"] > 0 else None

        # --- Rentabilité ---------------------------------------------------
        v["MARGE_NETTE"] = _div(c["resultat_net"] * 100.0, ca)
        v["MARGE_EXPLOITATION"] = _div(c["resultat_exploitation"] * 100.0, ca)
        v["ROE"] = _div(c["resultat_net"] * 100.0, cp_moyens)
        v["ROA"] = _div(c["resultat_exploitation"] * 100.0, actif_moyen)
        v["RENTABILITE_ECONOMIQUE"] = _div(c["resultat_exploitation"] * 100.0, b["immobilisations"] + bfr)
        v["TAUX_VA"] = _div(c["valeur_ajoutee"] * 100.0, ca)

        # --- Rotation ------------------------------------------------------
        base_stock = c["achats"] if abs(c["achats"]) > VALEUR_NULLE else ca
        v["DELAI_STOCK"] = _div(JOURS * stock_moyen, base_stock)
        v["DELAI_CLIENTS"] = _div(JOURS * clients_moyens * (1 + taux_tva), ca * (1 + taux_tva) if ca else None)
        base_fournisseurs = (c["achats"] + c["charges_externes"])
        if abs(base_fournisseurs) < VALEUR_NULLE:
            base_fournisseurs = ca
        v["DELAI_FOURNISSEURS"] = _div(JOURS * fournisseurs_moyens * (1 + taux_tva), base_fournisseurs * (1 + taux_tva) if base_fournisseurs else None)
        v["BFR_JOURS_CA"] = _div(JOURS * bfr, ca)
        v["ROTATION_ACTIF"] = _div(ca, actif_moyen)
        v["ROTATION_IMMO"] = _div(ca, b["immobilisations"])

        return v

    res.valeurs = _bloc(bilan, cpc, bilan_n1, cpc_n1)
    res.fonds_roulement = bilan["capitaux_permanents"] - bilan["immobilisations"]
    res.bfr = (bilan["stocks"] + bilan["clients"] + bilan["autres_creances"]) - bilan["passif_circulant"]
    res.tresorerie_nette = bilan["tresorerie_actif"] - bilan["tresorerie_passif"]

    if bilan_n1 and cpc_n1:
        res.valeurs_n1 = _bloc(bilan_n1, cpc_n1, None, None)
        res.fonds_roulement_n1 = bilan_n1["capitaux_permanents"] - bilan_n1["immobilisations"]
        res.bfr_n1 = (bilan_n1["stocks"] + bilan_n1["clients"] + bilan_n1["autres_creances"]) - bilan_n1["passif_circulant"]
        res.tresorerie_nette_n1 = bilan_n1["tresorerie_actif"] - bilan_n1["tresorerie_passif"]

    return res


# ---------------------------------------------------------------------------
# Contrôles de cohérence
# ---------------------------------------------------------------------------

def controler_coherence(
    postes_bilan: Mapping[str, float],
    postes_cpc: Mapping[str, float],
) -> List[Dict[str, object]]:
    """Vérifications utiles avant d'interpréter les ratios."""
    bilan = agreger_bilan(postes_bilan)
    cpc = agreger_cpc(postes_cpc)
    alertes: List[Dict[str, object]] = []

    ecart_equilibre = bilan["total_actif"] - bilan["total_passif"]
    if abs(ecart_equilibre) > max(1.0, 0.005 * max(bilan["total_actif"], 1.0)):
        alertes.append(
            {
                "niveau": "erreur",
                "titre": "Le bilan n'est pas équilibré",
                "message": (
                    f"Total actif = {bilan['total_actif']:,.2f} contre total passif = "
                    f"{bilan['total_passif']:,.2f} (écart de {ecart_equilibre:,.2f}). "
                    "Vérifiez les montants saisis : un bilan doit toujours être équilibré."
                ),
            }
        )

    ecart_resultat = cpc["resultat_net"] - nombre(postes_bilan.get("RESULTAT"))
    seuil = max(1.0, 0.01 * max(abs(cpc["resultat_net"]), 1.0))
    if abs(ecart_resultat) > seuil:
        alertes.append(
            {
                "niveau": "avertissement",
                "titre": "Le résultat net du CPC et celui du bilan diffèrent",
                "message": (
                    f"Résultat net calculé au CPC : {cpc['resultat_net']:,.2f} ; résultat inscrit au "
                    f"passif du bilan : {nombre(postes_bilan.get('RESULTAT')):,.2f}. "
                    "Les deux devraient être identiques."
                ),
            }
        )

    if not any(abs(nombre(v)) > 0 for v in postes_cpc.values()):
        alertes.append(
            {
                "niveau": "info",
                "titre": "Aucun montant dans le CPC",
                "message": "Les ratios de rentabilité et de rotation ne pourront pas être calculés.",
            }
        )
    elif abs(cpc["ca"]) < 1e-9:
        alertes.append(
            {
                "niveau": "avertissement",
                "titre": "Chiffre d'affaires à zéro",
                "message": "La plupart des ratios de rentabilité et de rotation utilisent le CA en dénominateur.",
            }
        )

    if cpc["caf"] <= 0 and abs(bilan["dettes_financieres"]) > 0:
        alertes.append(
            {
                "niveau": "avertissement",
                "titre": "Capacité d'autofinancement nulle ou négative",
                "message": (
                    f"La capacité d'autofinancement (CAF) s'établit à {cpc['caf']:,.2f}. L'entreprise ne dégage "
                    "pas de trésorerie avec son activité : elle ne peut pas rembourser sa dette financière sur "
                    "ses résultats. La capacité de remboursement n'est pas calculable."
                ),
            }
        )

    return alertes


def codes_ratios_calcules() -> List[str]:
    return [r.code for r in RATIOS if r.calcule]


def libelle_ratio(code: str) -> str:
    r = RATIOS_PAR_CODE.get(code)
    return r.libelle if r else code
