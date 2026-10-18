"""
Référentiel des postes comptables et des ratios.

Ce module ne contient que des données (déclaratif) :
 - la liste des postes du bilan et du compte de produits et charges (CPC) ;
 - la définition des ratios (formule, unité, seuils, texte d'explication).

Les calculs sont faits dans ``finance.ratios`` et l'interprétation en langage
simple dans ``finance.diagnostic``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

# ---------------------------------------------------------------------------
# Postes du bilan
# ---------------------------------------------------------------------------

# Groupes de regroupement comptable -> libellé affiché
GROUPES: Dict[str, str] = {
    "ACTIF_IMMOBILISE": "Actif immobilisé",
    "ACTIF_CIRCULANT": "Actif circulant",
    "TRESORERIE_ACTIF": "Trésorerie (actif)",
    "CAPITAUX_PROPRES": "Capitaux propres",
    "DETTES_FINANCIERES": "Dettes financières (capitaux permanents)",
    "PASSIF_CIRCULANT": "Passif circulant (dettes à court terme)",
    "TRESORERIE_PASSIF": "Trésorerie (passif)",
    "PRODUITS_EXPLOITATION": "Produits d'exploitation",
    "CHARGES_EXPLOITATION": "Charges d'exploitation",
    "FINANCIER": "Résultat financier",
    "FISCAL": "Impôt sur le résultat",
}


@dataclass(frozen=True)
class Poste:
    """Un poste (ligne) saisissable par l'utilisateur."""

    code: str
    libelle: str
    groupe: str
    nature: str  # "actif", "passif", "produit", "charge"
    aide: str = ""

    @property
    def signe(self) -> int:
        """+1 pour ce qui augmente le résultat, -1 sinon."""
        return 1 if self.nature in ("produit", "passif") else -1


POSTES_BILAN: List[Poste] = [
    # --- ACTIF -------------------------------------------------------------
    Poste(
        "IMMO_INCORP_CORP",
        "Immobilisations incorporelles et corporelles (nettes)",
        "ACTIF_IMMOBILISE",
        "actif",
        "Bâtiments, matériel, brevets, logiciels... après amortissements.",
    ),
    Poste(
        "IMMO_FINANCIERES",
        "Immobilisations financières",
        "ACTIF_IMMOBILISE",
        "actif",
        "Titres de participation, prêts à long terme, dépôts de garantie.",
    ),
    Poste("STOCKS", "Stocks et en-cours", "ACTIF_CIRCULANT", "actif"),
    Poste(
        "CLIENTS",
        "Créances clients et comptes rattachés",
        "ACTIF_CIRCULANT",
        "actif",
        "Factures émises non encore encaissées.",
    ),
    Poste(
        "AUTRES_CREANCES",
        "Autres créances (État, divers)",
        "ACTIF_CIRCULANT",
        "actif",
        "Créances fiscales (TVA, impôt), avances versées, produits à recevoir.",
    ),
    Poste(
        "VMP",
        "Valeurs mobilières de placement",
        "TRESORERIE_ACTIF",
        "actif",
        "Placements à court terme, actions, obligations...",
    ),
    Poste(
        "DISPONIBILITES",
        "Disponibilités (banque, caisse)",
        "TRESORERIE_ACTIF",
        "actif",
        "Solde des comptes bancaires et de caisse.",
    ),
    # --- PASSIF ------------------------------------------------------------
    Poste(
        "CAPITAL",
        "Capital et primes liées",
        "CAPITAUX_PROPRES",
        "passif",
        "Apports des propriétaires / actionnaires.",
    ),
    Poste(
        "RESERVES",
        "Réserves, report à nouveau et subventions",
        "CAPITAUX_PROPRES",
        "passif",
        "Bénéfices mis en réserve les années précédentes (déficit : montant négatif).",
    ),
    Poste(
        "RESULTAT",
        "Résultat de l'exercice (bénéfice +, perte -)",
        "CAPITAUX_PROPRES",
        "passif",
        "Doit correspondre au résultat net calculé dans le CPC.",
    ),
    Poste(
        "EMPRUNTS",
        "Emprunts et dettes financières à long terme",
        "DETTES_FINANCIERES",
        "passif",
        "Emprunts bancaires, crédits-bails, comptes courants d'associés bloqués.",
    ),
    Poste(
        "FOURNISSEURS",
        "Dettes fournisseurs et comptes rattachés",
        "PASSIF_CIRCULANT",
        "passif",
        "Factures d'achats non encore payées.",
    ),
    Poste(
        "DETTES_SOCIALES",
        "Dettes sociales (personnel, organismes sociaux)",
        "PASSIF_CIRCULANT",
        "passif",
        "Salaires à payer, cotisations sociales.",
    ),
    Poste(
        "DETTES_FISCALES",
        "Dettes fiscales (État)",
        "PASSIF_CIRCULANT",
        "passif",
        "TVA à payer, impôts et taxes dus.",
    ),
    Poste(
        "AUTRES_DETTES_CT",
        "Autres dettes à court terme",
        "PASSIF_CIRCULANT",
        "passif",
        "Produits constatés d'avance, comptes courants d'associés disponibles.",
    ),
    Poste(
        "CONCOURS_BANCAIRES",
        "Concours bancaires courants / découverts",
        "TRESORERIE_PASSIF",
        "passif",
        "Découverts et lignes de crédit court terme utilisées.",
    ),
]

# ---------------------------------------------------------------------------
# Postes du compte de produits et charges (CPC)
# ---------------------------------------------------------------------------

POSTES_CPC: List[Poste] = [
    Poste(
        "CA",
        "Chiffre d'affaires (CA)",
        "PRODUITS_EXPLOITATION",
        "produit",
        "Ventes de marchandises, de produits finis et de services, en HT.",
    ),
    Poste(
        "AUTRES_PRODUITS",
        "Autres produits d'exploitation",
        "PRODUITS_EXPLOITATION",
        "produit",
        "Subventions d'exploitation, reprises de provisions, produits divers.",
    ),
    Poste(
        "ACHATS",
        "Achats consommés (marchandises, matières premières)",
        "CHARGES_EXPLOITATION",
        "charge",
        "Achats variations de stock incluses, en HT.",
    ),
    Poste(
        "CHARGES_EXTERNES",
        "Autres charges externes",
        "CHARGES_EXPLOITATION",
        "charge",
        "Loyers, énergie, transports, honoraires, publicité...",
    ),
    Poste(
        "PERSONNEL",
        "Charges de personnel",
        "CHARGES_EXPLOITATION",
        "charge",
        "Salaires bruts et charges sociales patronales.",
    ),
    Poste(
        "IMPOTS_TAXES",
        "Impôts et taxes (hors impôt sur le résultat)",
        "CHARGES_EXPLOITATION",
        "charge",
        "Taxe professionnelle/CFE, taxes sur salaires, droits d'enregistrement...",
    ),
    Poste(
        "DOTATIONS",
        "Dotations aux amortissements et provisions",
        "CHARGES_EXPLOITATION",
        "charge",
        "Charge comptable non décaissée : à saisir même si elle est « non payée ».",
    ),
    Poste(
        "PRODUITS_FIN",
        "Produits financiers",
        "FINANCIER",
        "produit",
        "Intérêts reçus, gains de change, dividendes.",
    ),
    Poste(
        "CHARGES_FIN",
        "Charges financières",
        "FINANCIER",
        "charge",
        "Intérêts des emprunts et découverts, pertes de change.",
    ),
    Poste(
        "IMPOT_RESULTAT",
        "Impôt sur le résultat",
        "FISCAL",
        "charge",
        "Impôt sur les sociétés / impôt sur le revenu de l'exploitant.",
    ),
]

POSTES_BILAN_PAR_CODE: Dict[str, Poste] = {p.code: p for p in POSTES_BILAN}
POSTES_CPC_PAR_CODE: Dict[str, Poste] = {p.code: p for p in POSTES_CPC}


# ---------------------------------------------------------------------------
# Définition des ratios
# ---------------------------------------------------------------------------

AXES: Dict[str, str] = {
    "LIQUIDITE": "Liquidité",
    "SOLVABILITE": "Solvabilité",
    "RENTABILITE": "Rentabilité",
    "ROTATION": "Rotation",
}

AXES_ICONES: Dict[str, str] = {
    "LIQUIDITE": "💧",
    "SOLVABILITE": "🏦",
    "RENTABILITE": "📈",
    "ROTATION": "🔄",
}

AXES_DESCRIPTIONS: Dict[str, str] = {
    "LIQUIDITE": "Capacité de l'entreprise à payer ses dettes à court terme avec ce qu'elle possède à court terme.",
    "SOLVABILITE": "Solidité de la structure financière : part des fonds propres et poids de l'endettement.",
    "RENTABILITE": "Capacité de l'entreprise à gagner de l'argent par rapport à son chiffre d'affaires, ses capitaux et ses actifs.",
    "ROTATION": "Vitesse de circulation des stocks, des clients, des fournisseurs et de l'actif en général.",
}

# Icône affichée pour chaque ratio (repli : icône de son axe)
ICONES_RATIOS: Dict[str, str] = {
    "LIQ_GENERALE": "⚖️",
    "LIQ_REDUITE": "🧮",
    "LIQ_IMMEDIATE": "💵",
    "TRESO_NETTE_CA": "💰",
    "FONDS_ROULEMENT": "🏗️",
    "BFR": "🧱",
    "AUTONOMIE_FINANCIERE": "🛡️",
    "SOLVABILITE_GENERALE": "🏛️",
    "LEVIER": "🏋️",
    "CAPACITE_REMBOURSEMENT": "⏳",
    "MARGE_NETTE": "💹",
    "MARGE_EXPLOITATION": "⚙️",
    "ROE": "🏆",
    "ROA": "🏭",
    "RENTABILITE_ECONOMIQUE": "🎯",
    "TAUX_VA": "🧩",
    "DELAI_STOCK": "📦",
    "DELAI_CLIENTS": "🧾",
    "DELAI_FOURNISSEURS": "🚚",
    "BFR_JOURS_CA": "⏱️",
    "ROTATION_ACTIF": "🔁",
    "ROTATION_IMMO": "🛠️",
}

# Poids de chaque axe dans la note globale
POIDS_AXES: Dict[str, float] = {
    "LIQUIDITE": 0.30,
    "SOLVABILITE": 0.25,
    "RENTABILITE": 0.30,
    "ROTATION": 0.15,
}

# Statuts
STATUT_BON = "Bon"
STATUT_ACCEPTABLE = "Acceptable"
STATUT_VIGILANCE = "À surveiller"
STATUT_NA = "Non calculable"

COULEURS_STATUT: Dict[str, str] = {
    STATUT_BON: "#1a9850",
    STATUT_ACCEPTABLE: "#f4a300",
    STATUT_VIGILANCE: "#d73027",
    STATUT_NA: "#9e9e9e",
}

# Pastille affichée dans les rapports et les tableaux
ICONES_STATUT: Dict[str, str] = {
    STATUT_BON: "🟢",
    STATUT_ACCEPTABLE: "🟠",
    STATUT_VIGILANCE: "🔴",
    STATUT_NA: "⚪",
}

# Icône associée à l'appréciation globale du diagnostic
ICONES_APPRECIATION: Dict[str, str] = {
    "très solide": "🏆",
    "solide": "✅",
    "satisfaisante": "👍",
    "fragile": "⚠️",
    "critique": "🚨",
    "non évaluable": "❔",
}

# Bornes de score (sur 100) alignées sur les statuts : un ratio est jugé
# « Bon » à partir de 85/100 et « Acceptable » à partir de 55/100.
SEUIL_SCORE_BON = 85.0
SEUIL_SCORE_ACCEPTABLE = 55.0


@dataclass
class DefinitionRatio:
    """Métadonnées d'un ratio : formule, seuils et textes d'interprétation."""

    code: str
    libelle: str
    axe: str
    formule: str
    unite: str  # "x", "%", "jours", "montant"
    sens: str  # "haut" (plus c'est élevé, mieux c'est), "bas", "cible", "neutre"
    # Seuils : pour "haut" -> (seuil_bon, seuil_acceptable) avec bon > acceptable
    #           pour "bas"  -> (seuil_bon, seuil_acceptable) avec bon < acceptable
    #           pour "cible"-> (min_bon, max_bon, min_ok, max_ok)
    seuils: Tuple[float, ...]
    definition: str
    lecture: str  # texte explicatif, formaté avec les variables calculées
    conseil: str = ""
    poids: float = 1.0
    calcule: bool = True  # False = indicateur purement informatif
    # ratios à saisir manuellement hors bilan/CPC (aucun pour l'instant)
    seuils_secteur: Dict[str, Tuple[float, ...]] = field(default_factory=dict)

    @property
    def libelle_axe(self) -> str:
        return AXES.get(self.axe, self.axe)

    @property
    def icone(self) -> str:
        """Emoji représentant ce ratio (repli : icône de son axe)."""
        return ICONES_RATIOS.get(self.code, AXES_ICONES.get(self.axe, "🔹"))


RATIOS: List[DefinitionRatio] = [
    # ------------------------------------------------------------------
    # LIQUIDITÉ
    # ------------------------------------------------------------------
    DefinitionRatio(
        code="LIQ_GENERALE",
        libelle="Liquidité générale",
        axe="LIQUIDITE",
        formule="Actif circulant / Passif circulant",
        unite="x",
        sens="haut",
        seuils=(1.5, 1.0),
        definition="Combien l'entreprise possède de « court terme » (stocks, créances, cash) pour chaque unité de dettes à court terme.",
        lecture=(
            "Pour 1 de dettes à court terme, l'entreprise dispose de {valeur} d'actifs qui deviendront "
            "du cash dans les 12 prochains mois. {commentaire}"
        ),
        conseil=(
            "Encaisser plus vite les clients, réduire les stocks dormants, renégocier l'échéancier des "
            "dettes à court terme."
        ),
        poids=1.5,
        seuils_secteur={
            "Commerce / distribution": (1.3, 0.9),
            "Industrie / production": (1.6, 1.1),
            "Services / conseil": (1.4, 1.0),
        },
    ),
    DefinitionRatio(
        code="LIQ_REDUITE",
        libelle="Liquidité réduite (quick ratio)",
        axe="LIQUIDITE",
        formule="(Créances + Trésorerie) / Passif circulant",
        unite="x",
        sens="haut",
        seuils=(1.0, 0.8),
        definition="Liquidité calculée sans les stocks, c'est-à-dire avec les seuls éléments déjà proches du cash.",
        lecture=(
            "Sans compter les stocks, l'entreprise peut couvrir {valeur} de ses dettes à court terme. "
            "{commentaire}"
        ),
        conseil=(
            "Les stocks pèsent lourd : travailler sur la rotation des stocks et sur le recouvrement client "
            "plutôt que sur de nouveaux découverts bancaires."
        ),
        poids=1.0,
    ),
    DefinitionRatio(
        code="LIQ_IMMEDIATE",
        libelle="Liquidité immédiate",
        axe="LIQUIDITE",
        formule="Trésorerie (actif) / Passif circulant",
        unite="x",
        sens="haut",
        seuils=(0.3, 0.1),
        definition="Part des dettes à court terme que l'entreprise pourrait payer immédiatement avec son cash.",
        lecture=(
            "Le cash disponible couvre {valeur} des dettes à court terme. {commentaire}"
        ),
        conseil=(
            "Constituer un matelas de sécurité, négocier des facilités de trésorerie et lisser les "
            "décaissements importants."
        ),
        poids=0.75,
    ),
    DefinitionRatio(
        code="TRESO_NETTE_CA",
        libelle="Trésorerie nette en % du CA",
        axe="LIQUIDITE",
        formule="(Fonds de roulement − BFR) / CA",
        unite="%",
        sens="haut",
        seuils=(3.0, 0.0),
        definition="Excédent (ou manque) de trésorerie généré par le cycle d'exploitation, rapporté au niveau d'activité.",
        lecture=(
            "La trésorerie nette représente {valeur} du chiffre d'affaires. {commentaire}"
        ),
        conseil=(
            "Un manque de trésorerie structurel se corrige en réduisant le BFR : encaissements plus rapides, "
            "stocks plus légers, délais fournisseurs allongés."
        ),
        poids=1.5,
    ),
    DefinitionRatio(
        code="FONDS_ROULEMENT",
        libelle="Fonds de roulement net global",
        axe="LIQUIDITE",
        formule="Capitaux permanents − Actif immobilisé",
        unite="montant",
        sens="neutre",
        seuils=(),
        definition="Ressources durables qui restent disponibles après avoir financé les investissements.",
        lecture="Le fonds de roulement s'élève à {valeur}. {commentaire}",
        poids=0.0,
        calcule=False,
    ),
    DefinitionRatio(
        code="BFR",
        libelle="Besoin en fonds de roulement (BFR)",
        axe="LIQUIDITE",
        formule="(Stocks + Créances) − Dettes à court terme hors trésorerie",
        unite="montant",
        sens="neutre",
        seuils=(),
        definition="Argent immobilisé par le cycle d'exploitation : il faut payer les fournisseurs et constituer les stocks avant d'encaisser les clients.",
        lecture="Le BFR s'élève à {valeur}. {commentaire}",
        poids=0.0,
        calcule=False,
    ),
    # ------------------------------------------------------------------
    # SOLVABILITÉ
    # ------------------------------------------------------------------
    DefinitionRatio(
        code="AUTONOMIE_FINANCIERE",
        libelle="Autonomie financière",
        axe="SOLVABILITE",
        formule="Capitaux propres / Total du passif",
        unite="%",
        sens="haut",
        seuils=(30.0, 20.0),
        definition="Part des ressources qui appartiennent réellement à l'entreprise (et non à ses créanciers).",
        lecture=(
            "{valeur} du financement total est assuré par les fonds propres. {commentaire}"
        ),
        conseil=(
            "Augmenter les fonds propres : mise en réserve des bénéfices, apport des associés, "
            "ou désendettement progressif par le résultat."
        ),
        poids=1.5,
    ),
    DefinitionRatio(
        code="SOLVABILITE_GENERALE",
        libelle="Solvabilité générale",
        axe="SOLVABILITE",
        formule="Capitaux propres / Total des dettes",
        unite="x",
        sens="haut",
        seuils=(1.0, 0.5),
        definition="Capacité des fonds propres à couvrir l'ensemble des dettes, même à long terme.",
        lecture=(
            "Les fonds propres couvrent {valeur} des dettes de l'entreprise. {commentaire}"
        ),
        conseil=(
            "Le niveau d'endettement est élevé : prioriser le remboursement des dettes les plus chères et "
            "éviter de nouveaux emprunts non productifs."
        ),
        poids=1.25,
    ),
    DefinitionRatio(
        code="LEVIER",
        libelle="Levier d'endettement financier",
        axe="SOLVABILITE",
        formule="Dettes financières / Capitaux propres",
        unite="x",
        sens="bas",
        seuils=(0.5, 1.0),
        definition="Nombre d'unités de dettes financières pour 1 d'argent propre.",
        lecture=(
            "L'entreprise utilise {valeur} de dettes financières pour 1 de fonds propres. {commentaire}"
        ),
        conseil=(
            "Réduire la dette financière (remboursement anticipé, refinancement, cession d'actifs non "
            "stratégiques) ou renforcer les fonds propres."
        ),
        poids=1.5,
    ),
    DefinitionRatio(
        code="CAPACITE_REMBOURSEMENT",
        libelle="Capacité de remboursement",
        axe="SOLVABILITE",
        formule="Dettes financières / Capacité d'autofinancement (CAF)",
        unite="années",
        sens="bas",
        seuils=(3.0, 4.5),
        definition="Nombre d'années de cash-flow nécessaires pour rembourser la totalité des dettes financières.",
        lecture=(
            "Avec la trésorerie qu'elle dégage chaque année, l'entreprise rembourserait ses dettes "
            "financières en {valeur}. {commentaire}"
        ),
        conseil=(
            "Allonger la durée de la dette, générer plus de marge d'exploitation ou céder des actifs pour "
            "ramener ce ratio sous 3 ans."
        ),
        poids=1.5,
    ),
    # ------------------------------------------------------------------
    # RENTABILITÉ
    # ------------------------------------------------------------------
    DefinitionRatio(
        code="MARGE_NETTE",
        libelle="Marge nette",
        axe="RENTABILITE",
        formule="Résultat net / CA",
        unite="%",
        sens="haut",
        seuils=(5.0, 2.0),
        definition="Ce qui reste à l'entreprise, en pourcentage des ventes, après toutes les charges.",
        lecture=(
            "Sur 100 de chiffre d'affaires, il reste {valeur} de bénéfice net. {commentaire}"
        ),
        conseil=(
            "Agir à la fois sur les prix (remonter les marges trop faibles), sur la structure de coûts "
            "(charges non créatrices de valeur) et sur le mix produits."
        ),
        poids=1.5,
        seuils_secteur={
            "Commerce / distribution": (3.0, 1.0),
            "Industrie / production": (5.0, 2.0),
            "Services / conseil": (8.0, 3.0),
        },
    ),
    DefinitionRatio(
        code="MARGE_EXPLOITATION",
        libelle="Marge d'exploitation",
        axe="RENTABILITE",
        formule="Résultat d'exploitation / CA",
        unite="%",
        sens="haut",
        seuils=(6.0, 3.0),
        definition="Rentabilité de l'activité principale, avant le financement et l'impôt.",
        lecture=(
            "L'activité courante dégage {valeur} de résultat d'exploitation pour 100 de CA. {commentaire}"
        ),
        conseil=(
            "Vérifier le niveau des charges externes et la productivité : un CA qui progresse avec une marge "
            "d'exploitation qui recule signale un modèle peu rentable."
        ),
        poids=1.25,
        seuils_secteur={
            "Commerce / distribution": (3.5, 1.5),
            "Industrie / production": (6.0, 3.0),
            "Services / conseil": (9.0, 4.0),
        },
    ),
    DefinitionRatio(
        code="ROE",
        libelle="Rentabilité des capitaux propres (ROE)",
        axe="RENTABILITE",
        formule="Résultat net / Capitaux propres",
        unite="%",
        sens="haut",
        seuils=(12.0, 6.0),
        definition="Ce que rapporte l'argent investi par les propriétaires dans l'entreprise.",
        lecture=(
            "Les capitaux propres rapportent {valeur} par an. {commentaire}"
        ),
        conseil=(
            "Améliorer la marge nette ou accélérer la rotation des capitaux. Attention : un ROE élevé "
            "avec très peu de fonds propres signifie surtout un fort endettement."
        ),
        poids=1.5,
    ),
    DefinitionRatio(
        code="ROA",
        libelle="Rentabilité des actifs (ROA)",
        axe="RENTABILITE",
        formule="Résultat d'exploitation / Total de l'actif",
        unite="%",
        sens="haut",
        seuils=(7.0, 3.0),
        definition="Rendement de l'ensemble des moyens (machines, stocks, cash) mis en œuvre dans l'entreprise.",
        lecture=(
            "Chaque 100 d'actifs employés génèrent {valeur} de résultat d'exploitation. {commentaire}"
        ),
        conseil=(
            "Identifier les actifs peu ou mal utilisés (stocks dormants, matériel sous-employé, immobilier "
            "excédentaire) et les optimiser ou les céder."
        ),
        poids=1.25,
    ),
    DefinitionRatio(
        code="RENTABILITE_ECONOMIQUE",
        libelle="Rentabilité économique",
        axe="RENTABILITE",
        formule="Résultat d'exploitation / (Immobilisations nettes + BFR)",
        unite="%",
        sens="haut",
        seuils=(10.0, 5.0),
        definition="Rentabilité des capitaux réellement investis dans l'exploitation.",
        lecture=(
            "Les capitaux investis dans l'exploitation rapportent {valeur}. {commentaire}"
        ),
        conseil=(
            "À comparer au coût du financement : si cette rentabilité est inférieure au taux d'intérêt payé, "
            "l'entreprise s'appauvrit en s'endettant."
        ),
        poids=1.0,
    ),
    DefinitionRatio(
        code="TAUX_VA",
        libelle="Taux de valeur ajoutée",
        axe="RENTABILITE",
        formule="(CA + autres produits − achats − autres charges externes) / CA",
        unite="%",
        sens="haut",
        seuils=(25.0, 15.0),
        definition="Part du chiffre d'affaires créée par l'entreprise elle-même (hors achats et services achetés à l'extérieur).",
        lecture=(
            "L'entreprise transforme {valeur} de son chiffre d'affaires en valeur ajoutée. {commentaire}"
        ),
        conseil=(
            "Remonter l'intégration de l'activité (produire plutôt qu'acheter), renégocier les achats ou "
            "monter les prix de vente."
        ),
        poids=1.0,
        seuils_secteur={
            "Commerce / distribution": (18.0, 10.0),
            "Industrie / production": (25.0, 15.0),
            "Services / conseil": (45.0, 30.0),
        },
    ),
    # ------------------------------------------------------------------
    # ROTATION / ACTIVITÉ
    # ------------------------------------------------------------------
    DefinitionRatio(
        code="DELAI_STOCK",
        libelle="Durée moyenne de stockage",
        axe="ROTATION",
        formule="360 × Stock moyen / Achats consommés",
        unite="jours",
        sens="bas",
        seuils=(30.0, 60.0),
        definition="Nombre de jours de ventes que représentent les stocks détenus.",
        lecture=(
            "Un article reste en stock {valeur} en moyenne avant d'être vendu. {commentaire}"
        ),
        conseil=(
            "Déstockage des références lentes, réapprovisionnement plus fréquent, suivi des invendus et "
            "actions commerciales ciblées."
        ),
        poids=1.25,
        seuils_secteur={
            "Commerce / distribution": (45.0, 80.0),
            "Industrie / production": (60.0, 100.0),
            "Services / conseil": (10.0, 30.0),
        },
    ),
    DefinitionRatio(
        code="DELAI_CLIENTS",
        libelle="Délai de règlement clients",
        axe="ROTATION",
        formule="360 × Créances clients TTC / CA TTC",
        unite="jours",
        sens="bas",
        seuils=(30.0, 60.0),
        definition="Temps moyen mis par les clients pour payer leurs factures.",
        lecture=(
            "Le délai moyen de paiement des clients est de {valeur} après la facturation. {commentaire}"
        ),
        conseil=(
            "Facturer plus vite, encaisser des acomptes, sécuriser les relances, proposer un escompte pour "
            "paiement rapide et geler les livraisons des plus mauvais payeurs."
        ),
        poids=1.5,
        seuils_secteur={
            "Commerce / distribution": (15.0, 40.0),
            "Industrie / production": (45.0, 70.0),
            "Services / conseil": (45.0, 75.0),
        },
    ),
    DefinitionRatio(
        code="DELAI_FOURNISSEURS",
        libelle="Délai de règlement fournisseurs",
        axe="ROTATION",
        formule="360 × Dettes fournisseurs TTC / (Achats + charges externes) TTC",
        unite="jours",
        sens="cible",
        seuils=(30.0, 90.0, 15.0, 120.0),
        definition="Temps moyen que l'entreprise met pour payer ses fournisseurs.",
        lecture=(
            "L'entreprise règle ses fournisseurs en {valeur} en moyenne. {commentaire}"
        ),
        conseil=(
            "Négocier des délais de paiement plus longs avec les fournisseurs sans mettre en danger la "
            "relation commerciale ni s'exposer à des pénalités."
        ),
        poids=1.0,
    ),
    DefinitionRatio(
        code="BFR_JOURS_CA",
        libelle="Poids du BFR (jours de CA)",
        axe="ROTATION",
        formule="360 × BFR / CA",
        unite="jours",
        sens="bas",
        seuils=(45.0, 90.0),
        definition="Nombre de jours de chiffre d'affaires immobilisés en permanence dans le cycle d'exploitation.",
        lecture=(
            "Le cycle d'exploitation immobilise {valeur} de chiffre d'affaires. {commentaire}"
        ),
        conseil=(
            "Chaque jour de BFR gagné libère du cash : réduire les stocks, raccourcir les délais clients et "
            "allonger raisonnablement les délais fournisseurs."
        ),
        poids=1.0,
        seuils_secteur={
            "Commerce / distribution": (30.0, 60.0),
            "Industrie / production": (60.0, 100.0),
            "Services / conseil": (45.0, 90.0),
        },
    ),
    DefinitionRatio(
        code="ROTATION_ACTIF",
        libelle="Rotation de l'actif",
        axe="ROTATION",
        formule="CA / Total de l'actif",
        unite="x",
        sens="haut",
        seuils=(1.5, 0.8),
        definition="Chiffre d'affaires généré par chaque unité d'actif détenu.",
        lecture=(
            "Chaque 1 d'actif génère {valeur} de chiffre d'affaires. {commentaire}"
        ),
        conseil=(
            "Utiliser plus intensément les actifs existants avant d'investir : allongement des horaires, "
            "externalisation, cession des actifs improductifs."
        ),
        poids=0.75,
        seuils_secteur={
            "Commerce / distribution": (2.0, 1.2),
            "Industrie / production": (1.2, 0.7),
            "Services / conseil": (1.5, 0.8),
        },
    ),
    DefinitionRatio(
        code="ROTATION_IMMO",
        libelle="Rotation des immobilisations",
        axe="ROTATION",
        formule="CA / Immobilisations nettes",
        unite="x",
        sens="haut",
        seuils=(3.0, 1.5),
        definition="Productivité des investissements durables de l'entreprise.",
        lecture=(
            "Chaque 1 d'immobilisation génère {valeur} de chiffre d'affaires. {commentaire}"
        ),
        conseil=(
            "Vérifier que les investissements récents sont réellement productifs et envisager la location ou "
            "la cession du matériel sous-utilisé."
        ),
        poids=0.75,
    ),
]

RATIOS_PAR_CODE: Dict[str, DefinitionRatio] = {r.code: r for r in RATIOS}

# Ratios notés (ceux qui entrent dans la note globale)
RATIOS_NOTES: List[DefinitionRatio] = [r for r in RATIOS if r.calcule]

SECTEURS: List[str] = [
    "Général (tous secteurs)",
    "Commerce / distribution",
    "Industrie / production",
    "Services / conseil",
]


def seuils_ratio(ratio: DefinitionRatio, secteur: Optional[str]) -> Tuple[float, ...]:
    """Retourne les seuils du ratio, ajustés au secteur choisi si disponible."""
    if secteur and secteur in ratio.seuils_secteur:
        return ratio.seuils_secteur[secteur]
    return ratio.seuils
