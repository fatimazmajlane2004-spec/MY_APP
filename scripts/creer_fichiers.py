"""Génère les fichiers d'aide livrés avec l'application.

Crée dans le dossier ``data`` :
    - modele_bilan_cpc.xlsx      : modèle vierge à remplir (Bilan + CPC + Aide)
    - exemple_bilan_cpc.xlsx     : jeu de données d'exemple (2 exercices)
    - exemple_rapport.html       : exemple de rapport de diagnostic

Utilisation :  python scripts/creer_fichiers.py
"""

from __future__ import annotations

import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

from finance import io_utils as iou  # noqa: E402
from finance import referentiel as ref  # noqa: E402
from finance import reporting as rep  # noqa: E402
from finance.diagnostic import construire_diagnostic, note_affichee  # noqa: E402
from finance.ratios import calculer_ratios, controler_coherence  # noqa: E402

DOSSIER = RACINE / "data"


def main() -> None:
    DOSSIER.mkdir(exist_ok=True)

    # 1. Modèle vierge
    (DOSSIER / "modele_bilan_cpc.xlsx").write_bytes(iou.exporter_modele_excel())

    # 2. Exemple rempli (réimportable dans l'application)
    bilan, cpc = iou.exemple_dataframe()
    postes_bilan, postes_bilan_n1 = iou.postes_depuis_editeur(bilan, ref.POSTES_BILAN)
    postes_cpc, postes_cpc_n1 = iou.postes_depuis_editeur(cpc, ref.POSTES_CPC)
    (DOSSIER / "exemple_bilan_cpc.xlsx").write_bytes(
        iou.exporter_donnees_excel(postes_bilan, postes_bilan_n1, postes_cpc, postes_cpc_n1)
    )

    # 3. Exemple de rapport
    resultat = calculer_ratios(postes_bilan, postes_cpc, postes_bilan_n1, postes_cpc_n1)
    diagnostic = construire_diagnostic(
        resultat,
        secteur="Industrie / production",
        nom_entreprise="Société Industrielle Dupont",
        alertes=controler_coherence(postes_bilan, postes_cpc),
        unite_courte="€",
    )
    meta = {
        "entreprise": "Société Industrielle Dupont",
        "exercice": "2025",
        "secteur": "Industrie / production",
        "unite": "en euros",
    }
    (DOSSIER / "exemple_rapport.html").write_text(
        rep.rapport_html(diagnostic, resultat, meta), encoding="utf-8"
    )
    (DOSSIER / "exemple_rapport.md").write_text(
        rep.rapport_markdown(diagnostic, resultat, meta), encoding="utf-8"
    )
    rep.tableau_ratios(diagnostic).to_csv(DOSSIER / "exemple_ratios.csv", index=False, encoding="utf-8-sig")

    print(f"Note globale de l'exemple : {note_affichee(diagnostic.score_global)}/100 ({diagnostic.appreciation})")
    for axe, libelle in ref.AXES.items():
        score = diagnostic.scores_axes.get(axe)
        print(f"  - {libelle:12s} : {note_affichee(score)}/100" if score is not None else f"  - {libelle:12s} : n.d.")
    print(f"Fichiers écrits dans {DOSSIER}")


if __name__ == "__main__":
    main()
