"""
Interprétation des ratios : statut, score, commentaire en langage simple,
synthèse globale, points forts, points de vigilance et recommandations.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from . import referentiel as ref
from .ratios import ResultatRatios

# Bornes de score : elles coïncident avec les seuils, ce qui garantit qu'un
# badge « Bon » correspond toujours à un score >= 85.
SEUIL_SCORE_BON = ref.SEUIL_SCORE_BON
SEUIL_SCORE_ACCEPTABLE = ref.SEUIL_SCORE_ACCEPTABLE


# ---------------------------------------------------------------------------
# Notation
# ---------------------------------------------------------------------------

def _interpoler_bas(valeur: float, plancher: float, plafond: float, mini: float, maxi: float) -> float:
    """Interpolation linéaire entre mini (valeur=plancher) et maxi (valeur=plafond)."""
    if abs(plafond - plancher) < 1e-9:
        return maxi if valeur >= plafond else mini
    ratio = (valeur - plancher) / (plafond - plancher)
    ratio = min(max(ratio, 0.0), 1.0)
    return mini + ratio * (maxi - mini)


def score_ratio(ratio: ref.DefinitionRatio, valeur: Optional[float], secteur: Optional[str]) -> Optional[float]:
    """Score sur 100 d'un ratio, cohérent avec les seuils affichés à l'utilisateur."""
    if valeur is None:
        return None
    seuils = ref.seuils_ratio(ratio, secteur)
    if not seuils:
        return None

    if ratio.sens == "haut":
        bon, ok = seuils[0], seuils[1]
        if valeur >= bon:
            return 100.0
        if valeur >= ok:
            return _interpoler_bas(valeur, ok, bon, SEUIL_SCORE_ACCEPTABLE, SEUIL_SCORE_BON)
        if ok > 0:
            return max(0.0, SEUIL_SCORE_ACCEPTABLE * (valeur / ok))
        # seuil acceptable négatif ou nul : on dégrade encore plus vite
        echelle = max(abs(bon), 1.0)
        return max(0.0, SEUIL_SCORE_ACCEPTABLE * (1.0 + valeur / echelle))

    if ratio.sens == "bas":
        bon, ok = seuils[0], seuils[1]
        if valeur <= bon:
            return 100.0
        if valeur <= ok:
            return _interpoler_bas(valeur, bon, ok, SEUIL_SCORE_BON, SEUIL_SCORE_ACCEPTABLE)
        echelle = max(abs(ok), 1.0)
        return max(0.0, SEUIL_SCORE_ACCEPTABLE * (1.0 - (valeur - ok) / echelle))

    if ratio.sens == "cible":
        min_bon, max_bon, min_ok, max_ok = seuils
        if min_bon <= valeur <= max_bon:
            return 100.0
        if min_ok <= valeur < min_bon:
            return _interpoler_bas(valeur, min_ok, min_bon, SEUIL_SCORE_ACCEPTABLE, SEUIL_SCORE_BON)
        if max_bon < valeur <= max_ok:
            return _interpoler_bas(valeur, max_bon, max_ok, SEUIL_SCORE_BON, SEUIL_SCORE_ACCEPTABLE)
        if valeur < min_ok:
            span = max(min_ok, 1.0)
            return max(0.0, SEUIL_SCORE_ACCEPTABLE * (valeur / span))
        span = max(max_ok, 1.0)
        return max(0.0, SEUIL_SCORE_ACCEPTABLE * (1.0 - (valeur - max_ok) / span))

    return None


def statut_depuis_score(score: Optional[float]) -> str:
    if score is None:
        return ref.STATUT_NA
    if score >= SEUIL_SCORE_BON:
        return ref.STATUT_BON
    if score >= SEUIL_SCORE_ACCEPTABLE:
        return ref.STATUT_ACCEPTABLE
    return ref.STATUT_VIGILANCE


def couleur_score(score: Optional[float]) -> str:
    """Couleur d'affichage associée à une note sur 100."""
    return ref.COULEURS_STATUT.get(statut_depuis_score(score), ref.COULEURS_STATUT[ref.STATUT_NA])


# ---------------------------------------------------------------------------
# Commentaires en langage simple
# ---------------------------------------------------------------------------

COMMENTAIRES_GENERIQUES: Dict[Tuple[str, str], str] = {
    ("haut", ref.STATUT_BON): "C'est un bon niveau, avec une marge de sécurité confortable.",
    ("haut", ref.STATUT_ACCEPTABLE): "C'est un niveau moyen : cela passe, mais il n'y a pratiquement aucune marge de sécurité.",
    ("haut", ref.STATUT_VIGILANCE): "C'est un niveau faible : c'est un vrai point de vigilance.",
    ("bas", ref.STATUT_BON): "C'est un bon niveau, bien maîtrisé.",
    ("bas", ref.STATUT_ACCEPTABLE): "C'est un peu élevé : à surveiller, cela consomme des ressources ou de la trésorerie.",
    ("bas", ref.STATUT_VIGILANCE): "C'est trop élevé : c'est un vrai point de vigilance.",
    ("cible", ref.STATUT_BON): "C'est dans la norme usuelle.",
    ("cible", ref.STATUT_ACCEPTABLE): "C'est un peu en dehors de la norme : à surveiller.",
    ("cible", ref.STATUT_VIGILANCE): "C'est nettement en dehors de la norme : c'est un point de vigilance.",
}

# Commentaires spécifiques, quand la formule générique est trop vague
COMMENTAIRES_SPECIFIQUES: Dict[str, Dict[str, str]] = {
    "LIQ_GENERALE": {
        ref.STATUT_BON: "L'entreprise peut faire face à ses échéances court terme sans difficulté.",
        ref.STATUT_ACCEPTABLE: "Les échéances court terme sont justes couvertes : le moindre retard de paiement d'un client peut créer une tension.",
        ref.STATUT_VIGILANCE: "L'entreprise n'a pas assez d'actifs à court terme pour honorer ses dettes à court terme : un risque de cessation de paiement existe.",
    },
    "LIQ_IMMEDIATE": {
        ref.STATUT_BON: "Le compte bancaire est bien approvisionné : c'est rassurant pour les créanciers.",
        ref.STATUT_ACCEPTABLE: "Le cash disponible reste juste : il faut piloter la trésorerie de près.",
        ref.STATUT_VIGILANCE: "Le cash disponible est très insuffisant pour payer les échéances immédiates.",
    },
    "AUTONOMIE_FINANCIERE": {
        ref.STATUT_BON: "L'entreprise travaille majoritairement avec ses propres ressources : elle est indépendante vis-à-vis des banques.",
        ref.STATUT_ACCEPTABLE: "L'équilibre reste acceptable, mais les créanciers financent une part importante de l'activité.",
        ref.STATUT_VIGILANCE: "L'activité est surtout financée par des dettes : l'entreprise est fragile face à une banque qui se retire.",
    },
    "LEVIER": {
        ref.STATUT_BON: "L'endettement bancaire est limité : il reste de la capacité d'emprunt si un projet se présente.",
        ref.STATUT_ACCEPTABLE: "L'endettement est significatif mais reste dans des proportions gérables.",
        ref.STATUT_VIGILANCE: "L'entreprise dépend fortement de ses banques : une hausse des taux ou un refus de crédit la mettrait en difficulté.",
    },
    "CAPACITE_REMBOURSEMENT": {
        ref.STATUT_BON: "La dette est remboursable rapidement grâce aux résultats dégagés.",
        ref.STATUT_ACCEPTABLE: "Le remboursement reste possible, mais il consomme une grande partie de ce que l'entreprise gagne.",
        ref.STATUT_VIGILANCE: "L'entreprise ne dégage pas assez de trésorerie pour rembourser sa dette : celle-ci devra être restructurée ou renforcée par des fonds propres.",
    },
    "MARGE_NETTE": {
        ref.STATUT_BON: "L'activité est réellement rentable : chaque vente laisse une marge appréciable.",
        ref.STATUT_ACCEPTABLE: "L'activité est faiblement rentable : un petit choc (hausse de coûts, baisse d'activité) suffirait à effacer le bénéfice.",
        ref.STATUT_VIGILANCE: "L'activité ne laisse presque rien, voire détruit de la valeur à chaque vente.",
    },
    "ROE": {
        ref.STATUT_BON: "Les propriétaires obtiennent un rendement attractif sur leur mise.",
        ref.STATUT_ACCEPTABLE: "Le rendement reste modeste au regard du risque pris.",
        ref.STATUT_VIGILANCE: "Les fonds investis ne sont pas rémunérés : à terme, les associés peuvent envisager de désinvestir.",
    },
    "DELAI_CLIENTS": {
        ref.STATUT_BON: "Les clients paient rapidement : le cash revient vite dans l'entreprise.",
        ref.STATUT_ACCEPTABLE: "Le délai de paiement est un peu long et immobilise de la trésorerie.",
        ref.STATUT_VIGILANCE: "Les clients paient très lentement : l'entreprise finance en réalité son activité à leur place, avec un risque d'impayés.",
    },
    "DELAI_STOCK": {
        ref.STATUT_BON: "Les stocks tournent vite : peu d'argent dort dans l'entrepôt.",
        ref.STATUT_ACCEPTABLE: "Les stocks tournent un peu lentement : du cash reste mobilisé.",
        ref.STATUT_VIGILANCE: "Les stocks restent très longtemps : ils immobilisent de la trésorerie et risquent de devenir invendables.",
    },
    "DELAI_FOURNISSEURS": {
        ref.STATUT_BON: "L'entreprise se fait financer par ses fournisseurs : c'est bon pour sa trésorerie.",
        ref.STATUT_ACCEPTABLE: "Le délai de paiement fournisseurs est raisonnable.",
        ref.STATUT_VIGILANCE: "Soit l'entreprise paie très vite (ce qui lui coûte du cash), soit elle paie trop tard (ce qui dégrade ses relations et expose à des pénalités).",
    },
    "TRESO_NETTE_CA": {
        ref.STATUT_BON: "L'activité dégage un excédent de trésorerie : c'est un signe de bonne santé.",
        ref.STATUT_ACCEPTABLE: "La trésorerie est à l'équilibre, sans réserve de sécurité.",
        ref.STATUT_VIGILANCE: "L'exploitation consomme de la trésorerie : l'entreprise doit financer ce trou par de la dette.",
    },
    "BFR_JOURS_CA": {
        ref.STATUT_BON: "Le cycle d'exploitation mobilise peu de cash : c'est efficace.",
        ref.STATUT_ACCEPTABLE: "Le cycle d'exploitation mobilise une part importante du chiffre d'affaires.",
        ref.STATUT_VIGILANCE: "Le cycle d'exploitation absorbe énormément de trésorerie : c'est la première cause à traiter.",
    },
}


def _commentaire(ratio: ref.DefinitionRatio, statut: str) -> str:
    specifique = COMMENTAIRES_SPECIFIQUES.get(ratio.code, {}).get(statut)
    if specifique:
        return specifique
    return COMMENTAIRES_GENERIQUES.get((ratio.sens, statut), "")


# ---------------------------------------------------------------------------
# Structures de résultat
# ---------------------------------------------------------------------------

@dataclass
class LigneDiagnostic:
    code: str
    libelle: str
    axe: str
    libelle_axe: str
    formule: str
    definition: str
    unite: str
    valeur: Optional[float]
    valeur_n1: Optional[float]
    statut: str
    score: Optional[float]
    texte: str
    conseil: str = ""
    evolution: Optional[str] = None
    tendance: Optional[str] = None  # "hausse", "baisse", "stable"
    icone: str = "🔹"

    @property
    def couleur(self) -> str:
        return ref.COULEURS_STATUT.get(self.statut, "#9e9e9e")

    @property
    def pastille(self) -> str:
        """Pastille colorée du statut (🟢 / 🟠 / 🔴)."""
        return ref.ICONES_STATUT.get(self.statut, "⚪")

    @property
    def note(self) -> bool:
        ratio = ref.RATIOS_PAR_CODE.get(self.code)
        return bool(ratio and ratio.calcule)


@dataclass
class Diagnostic:
    lignes: List[LigneDiagnostic] = field(default_factory=list)
    scores_axes: Dict[str, Optional[float]] = field(default_factory=dict)
    score_global: Optional[float] = None
    appreciation: str = ""
    synthese: str = ""
    points_forts: List[str] = field(default_factory=list)
    points_vigilance: List[str] = field(default_factory=list)
    recommandations: List[str] = field(default_factory=list)
    alertes: List[Dict[str, object]] = field(default_factory=list)
    unite_courte: str = ""

    @property
    def ligne_par_code(self) -> Dict[str, LigneDiagnostic]:
        return {l.code: l for l in self.lignes}


def _texte_commentaire_indicateur(code: str, valeur: float, agregats: Dict[str, float], cpc: Dict[str, float]) -> str:
    """Commentaire pour les indicateurs non notés (fonds de roulement, BFR)."""
    ca = cpc.get("ca", 0.0)
    if code == "FONDS_ROULEMENT":
        if valeur >= 0:
            return (
                "Positif : les ressources durables financent la totalité des investissements et laissent "
                "de quoi financer le cycle d'exploitation."
            )
        return (
            "Négatif : les investissements durables sont financés en partie par des dettes à court terme, "
            "ce qui fragilise la trésorerie."
        )
    if code == "BFR":
        if abs(ca) > 1e-9:
            jours = 360.0 * valeur / ca
            if valeur >= 0:
                return f"C'est un besoin à financer (environ {jours:.0f} jours de chiffre d'affaires)."
            return "Il est négatif : les clients et les fournisseurs financent l'activité, ce qui libère de la trésorerie."
        return "Besoin de financement du cycle d'exploitation." if valeur >= 0 else "Ressource de financement du cycle d'exploitation."
    return ""


def _format_evolution(valeur: Optional[float], valeur_n1: Optional[float], unite: str) -> Tuple[Optional[str], Optional[str]]:
    if valeur is None or valeur_n1 is None:
        return None, None
    ecart = valeur - valeur_n1
    if abs(ecart) < 1e-9:
        return "stable", "stable"
    if unite == "%":
        texte = f"{ecart:+.1f} pt".replace(".", ",")
    elif unite == "x":
        texte = f"{ecart:+.2f} pt".replace(".", ",")
    elif unite == "années":
        texte = f"{ecart:+.1f} an(s)".replace(".", ",")
    else:
        texte = f"{ecart:+.0f} j"
    return texte, ("hausse" if ecart > 0 else "baisse")


# ---------------------------------------------------------------------------
# Diagnostic complet
# ---------------------------------------------------------------------------

def construire_diagnostic(
    resultat: ResultatRatios,
    secteur: Optional[str] = None,
    nom_entreprise: str = "L'entreprise",
    alertes: Optional[Sequence[Dict[str, object]]] = None,
    unite_courte: str = "",
) -> Diagnostic:
    diag = Diagnostic(
        alertes=list(alertes or []),
        unite_courte=unite_courte.strip(),
    )
    scores_par_axe: Dict[str, List[Tuple[float, float]]] = {}

    for ratio in ref.RATIOS:
        valeur = resultat.valeurs.get(ratio.code)
        valeur_n1 = resultat.valeurs_n1.get(ratio.code) if resultat.valeurs_n1 else None
        score = score_ratio(ratio, valeur, secteur)
        statut = statut_depuis_score(score)

        if ratio.calcule:
            commentaire = _commentaire(ratio, statut) if valeur is not None else (
                "Ratio non calculable avec les données saisies (dénominateur nul ou donnée manquante)."
            )
            texte = ratio.lecture.format(valeur=_fmt(valeur, ratio.unite), commentaire=commentaire)
        else:
            commentaire = _texte_commentaire_indicateur(ratio.code, valeur or 0.0, resultat.bilan, resultat.cpc)
            texte = ratio.lecture.format(valeur=_fmt(valeur, ratio.unite), commentaire=commentaire)

        evolution, tendance = _format_evolution(valeur, valeur_n1, ratio.unite)

        diag.lignes.append(
            LigneDiagnostic(
                code=ratio.code,
                libelle=ratio.libelle,
                axe=ratio.axe,
                libelle_axe=ratio.libelle_axe,
                formule=ratio.formule,
                definition=ratio.definition,
                unite=ratio.unite,
                valeur=valeur,
                valeur_n1=valeur_n1,
                statut=statut,
                score=score,
                texte=texte,
                conseil=ratio.conseil,
                evolution=evolution,
                tendance=tendance,
                icone=ratio.icone,
            )
        )

        if ratio.calcule and score is not None and ratio.poids > 0:
            scores_par_axe.setdefault(ratio.axe, []).append((score, ratio.poids))

    # --- Scores par axe et note globale -----------------------------------
    for axe, couples in scores_par_axe.items():
        poids_total = sum(p for _, p in couples)
        diag.scores_axes[axe] = sum(s * p for s, p in couples) / poids_total if poids_total else None
    for axe in ref.AXES:
        diag.scores_axes.setdefault(axe, None)

    poids_axes = {a: ref.POIDS_AXES[a] for a, s in diag.scores_axes.items() if s is not None}
    if poids_axes:
        poids_total = sum(poids_axes.values())
        diag.score_global = sum(diag.scores_axes[a] * p for a, p in poids_axes.items()) / poids_total

    diag.appreciation = appreciation(diag.score_global)
    diag.synthese = _synthese(diag, resultat, nom_entreprise, secteur)
    diag.points_forts = _points_forts(diag)
    diag.points_vigilance = _points_vigilance(diag)
    diag.recommandations = _recommandations(diag, resultat)
    return diag


def appreciation(score: Optional[float]) -> str:
    if score is None:
        return "non évaluable"
    if score >= 85:
        return "très solide"
    if score >= 70:
        return "solide"
    if score >= 55:
        return "satisfaisante"
    if score >= 40:
        return "fragile"
    return "critique"


def note_affichee(score: Optional[float]) -> Optional[int]:
    """Note entière affichée : tronquée, pour rester cohérente avec l'appréciation (55 = satisfaisante)."""
    if score is None:
        return None
    return int(math.floor(score))


def _fmt(valeur: Optional[float], unite: str) -> str:
    """Formatage français des nombres."""
    if valeur is None:
        return "n.d."
    if unite == "%":
        return f"{valeur:.1f} %".replace(".", ",")
    if unite == "x":
        return f"{valeur:.2f}".replace(".", ",")
    if unite == "jours":
        return f"{valeur:.0f} jours"
    if unite == "années":
        return f"{valeur:.1f} an(s)".replace(".", ",")
    return f"{valeur:,.0f}".replace(",", " ")


def _synthese(diag: Diagnostic, resultat: ResultatRatios, nom_entreprise: str, secteur: Optional[str]) -> str:
    if diag.score_global is None:
        return "Les données fournies ne permettent pas de calculer suffisamment de ratios pour établir un diagnostic."

    lignes: List[str] = []
    lignes.append(
        f"**{nom_entreprise}** obtient une note globale de **{note_affichee(diag.score_global)}/100**, ce qui correspond "
        f"à une situation financière **{diag.appreciation}**."
    )

    meilleur = max(
        ((a, s) for a, s in diag.scores_axes.items() if s is not None), key=lambda x: x[1], default=None
    )
    pire = min(
        ((a, s) for a, s in diag.scores_axes.items() if s is not None), key=lambda x: x[1], default=None
    )
    if meilleur and pire and meilleur[0] != pire[0]:
        lignes.append(
            f"Le point le plus favorable concerne **{ref.AXES[meilleur[0]].lower()}** "
            f"({note_affichee(meilleur[1])}/100), tandis que **{ref.AXES[pire[0]].lower()}** est le domaine "
            f"le plus fragile ({note_affichee(pire[1])}/100)."
        )

    b = resultat.bilan
    c = resultat.cpc
    unite = f" {diag.unite_courte}" if diag.unite_courte else ""

    def montant(valeur: float) -> str:
        return _fmt(valeur, "montant") + unite

    if c["ca"]:
        lignes.append(
            f"Avec un chiffre d'affaires de {montant(c['ca'])} et un résultat net de "
            f"{montant(c['resultat_net'])}, l'entreprise dégage une marge nette de "
            f"{_fmt(resultat.valeurs.get('MARGE_NETTE'), '%')}."
        )
    lignes.append(
        f"Elle finance son activité avec {montant(b['capitaux_propres'])} de capitaux propres et "
        f"{montant(b['total_dettes'])} de dettes, et sa trésorerie nette s'élève à "
        f"{montant(resultat.tresorerie_nette)}."
    )
    if secteur and secteur != ref.SECTEURS[0]:
        lignes.append(
            f"Les repères utilisés sont adaptés au secteur retenu : **{secteur}**."
        )
    return "\n\n".join(lignes)


def _points_forts(diag: Diagnostic, limite: int = 4) -> List[str]:
    notes = [l for l in diag.lignes if l.note and l.statut == ref.STATUT_BON and l.valeur is not None]
    notes.sort(key=lambda l: -(ref.RATIOS_PAR_CODE[l.code].poids))
    resultat = []
    for l in notes[:limite]:
        resultat.append(f"**{l.libelle}** ({_fmt(l.valeur, l.unite)}) : {l.texte}")
    return resultat


def _points_vigilance(diag: Diagnostic, limite: int = 5) -> List[str]:
    notes = [l for l in diag.lignes if l.note and l.statut == ref.STATUT_VIGILANCE]
    notes.sort(key=lambda l: (l.score if l.score is not None else 0, -ref.RATIOS_PAR_CODE[l.code].poids))
    resultat = []
    for l in notes[:limite]:
        conseil = f" → {l.conseil}" if l.conseil else ""
        resultat.append(f"**{l.libelle}** ({_fmt(l.valeur, l.unite)}) : {l.texte}{conseil}")
    return resultat


def _recommandations(diag: Diagnostic, resultat: ResultatRatios) -> List[str]:
    """Priorités d'action concrètes, classées par impact."""
    lignes = diag.ligne_par_code
    recos: List[str] = []

    def valeur(code: str) -> Optional[float]:
        ligne = lignes.get(code)
        return ligne.valeur if ligne else None

    dettes_fin = resultat.bilan.get("dettes_financieres", 0.0)
    levier = valeur("LEVIER")
    treso = resultat.tresorerie_nette
    ca = resultat.cpc.get("ca", 0.0)

    # 1. Problème de liquidité immédiat
    if (valeur("LIQ_GENERALE") is not None and valeur("LIQ_GENERALE") < 1.0) or treso < 0:
        recos.append(
            "**Sécuriser la trésorerie à court terme.** Un excédent de financement court terme fait défaut : "
            "négociez ou faites confirmer une ligne de crédit, échelonnez les décaissements importants et "
            "mettez en place un suivi hebdomadaire de la trésorerie."
        )

    # 2. Délai clients
    delai_clients = valeur("DELAI_CLIENTS")
    if delai_clients is not None and delai_clients > 60:
        recos.append(
            f"**Réduire le délai clients ({delai_clients:.0f} jours).** Facturation immédiate à la livraison, "
            "acompte à la commande, relances automatiques à J+5 et J+15, blocage des livraisons au-delà de "
            "2 relances. Passer de 60 à 45 jours libère environ 15 jours de CA en cash."
        )

    # 3. Stocks
    delai_stock = valeur("DELAI_STOCK")
    if delai_stock is not None and delai_stock > 90:
        recos.append(
            f"**Déstocker ({delai_stock:.0f} jours de stockage).** Identifiez les références qui ne bougent pas "
            "depuis plus de 6 mois, liquidez-les (promotions, lots, déstockage) et réduisez les quantités "
            "commandées sur les références les plus lentes."
        )

    # 4. Rentabilité
    marge = valeur("MARGE_NETTE")
    if marge is not None and marge < 2:
        recos.append(
            "**Reconstruire la marge.** Passez en revue les prix de vente (beaucoup de petites entreprises "
            "sous-facturent), la remise maximale autorisée par commercial, et les postes de charges non "
            "directement productifs (loyers, abonnements, frais généraux)."
        )

    # 5. Endettement
    if levier is not None and levier > 1.0:
        recos.append(
            f"**Alléger la dette financière (levier de {levier:.2f}).** Envisagez un remboursement anticipé "
            "des crédits les plus chers, un rééchelonnement de la dette sur une durée plus longue, et "
            "privilégiez l'autofinancement pour les prochains investissements."
        )

    # 6. Rentabilité vs coût de la dette
    re_eco = valeur("RENTABILITE_ECONOMIQUE")
    if re_eco is not None and dettes_fin > 0 and re_eco < 5:
        recos.append(
            "**Vérifier la rentabilité du capital investi.** La rentabilité économique est faible par rapport "
            "au coût du financement : chaque euro emprunté rapporte moins qu'il ne coûte. Priorisez les "
            "investissements à retour rapide."
        )

    # 7. Si tout va bien
    if not recos:
        recos.append(
            "**Consolider les acquis.** La situation est équilibrée : mettez en place un tableau de bord "
            "mensuel (trésorerie, marge, délais clients) pour détecter au plus vite une dégradation, et "
            "profitez de la capacité d'endettement disponible pour financer la croissance."
        )

    if ca and treso > 0:
        recos.append(
            f"**Utiliser l'excédent de trésorerie ({_fmt(treso, 'montant')}).** Placez la trésorerie "
            "excédentaire à court terme ou utilisez-la pour réduire la dette la plus coûteuse : laisser "
            "dormir du cash sur un compte courant est un manque à gagner."
        )
    return recos
