"""Affiche le contenu réellement rendu par l'application (contrôle qualité manuel).

Utilisation :  python scripts/verifier_rendu.py > rendu.txt
"""

from __future__ import annotations

import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

from streamlit.testing.v1 import AppTest  # noqa: E402


def texte_sans_balises(valeur: str) -> str:
    import html
    import re

    valeur = re.sub(r"<[^>]+>", " ", valeur or "")
    return " ".join(html.unescape(valeur).split())


def main() -> None:
    at = AppTest.from_file(str(RACINE / "app.py"), default_timeout=120)
    at.run()
    print("### ETAT INITIAL (sans données)")
    for info in at.info:
        print("  info   :", texte_sans_balises(info.value)[:160])
    print("  exceptions :", len(at.exception))

    [b for b in at.sidebar.button if "exemple" in b.label.lower()][0].click().run()
    print("\n### APRES CHARGEMENT DE L'EXEMPLE")
    print("  exceptions :", len(at.exception))
    for e in at.exception:
        print("  ERREUR :", e.value)

    print("\n### BARRE LATERALE")
    for w in at.sidebar.text_input:
        print(f"  texte   {w.label} = {w.value}")
    for w in at.sidebar.selectbox:
        print(f"  choix   {w.label} = {w.value}")
    for w in at.sidebar.number_input:
        print(f"  nombre  {w.label} = {w.value}")

    print("\n### HABILLAGE (extraits des blocs HTML)")
    for m in at.markdown:
        valeur = m.value or ""
        for classe in ("hero", "carte-note", "carte-axe", "legende", "recap"):
            if f"class='{classe}'" in valeur:
                print(f"  [{classe}] {texte_sans_balises(valeur)[:220]}")
                break

    print("\n### TITRES ET TEXTES")
    for t in at.subheader:
        print(f"  ## {texte_sans_balises(t.value)}")
    for m in at.markdown:
        texte = texte_sans_balises(m.value)
        if texte:
            print(f"  - {texte}")

    print("\n### BOUTONS DE TELECHARGEMENT")
    for b in at.get("download_button"):
        print(f"  {b.label}")

    print("\n### ONGLETS")
    for i, lbl in enumerate(["1 Donnees", "2 Ratios", "3 Diagnostic", "4 Rapport"]):
        print(f"  {i + 1}. {lbl}")

    print("\n### TABLEAUX DE SAISIE")
    for editeur in at.get("data_editor"):
        valeur = editeur.value
        print(f"  lignes : {len(valeur)}  colonnes : {list(valeur.columns)}")
        lignes_remplies = valeur[valeur["Exercice N"].notna()]
        print(f"  lignes remplies : {len(lignes_remplies)}")
        if len(lignes_remplies):
            print(lignes_remplies.head(4).to_string(index=False)[:400])


if __name__ == "__main__":
    main()
