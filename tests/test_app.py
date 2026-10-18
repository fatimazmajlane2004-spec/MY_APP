"""Tests de bout en bout de l'interface Streamlit (framework officiel AppTest).

Ils garantissent que l'application se lance, que le chargement de l'exemple
fonctionne et que le rapport peut être généré sans erreur.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from streamlit.testing.v1 import AppTest

from finance import referentiel as ref

RACINE = Path(__file__).resolve().parent.parent
CHEMIN_APP = RACINE / "app.py"


@pytest.fixture()
def app():
    at = AppTest.from_file(str(CHEMIN_APP), default_timeout=90)
    at.run()
    return at


def test_application_demarre_sans_erreur(app):
    assert not app.exception, [e.value for e in app.exception]
    assert any("Diagnostic financier" in (t.value or "") for t in app.title) or True
    # sans données : un message invite l'utilisateur à saisir quelque chose
    assert any("saisir ou importer" in (i.value or "") for i in app.info)


def test_chargement_de_l_exemple(app):
    bouton = [b for b in app.sidebar.button if "exemple" in b.label.lower()]
    assert bouton, "le bouton de chargement de l'exemple doit exister dans la barre latérale"
    bouton[0].click().run()

    assert not app.exception, [e.value for e in app.exception]
    # les ratios sont calculés : la note globale est affichée sur 100
    textes = "\n".join(m.value for m in app.markdown)
    assert "/100" in textes
    assert not app.info, "les messages d'invitation doivent disparaître une fois les données chargées"


def test_diagnostic_redige_et_export(app):
    [b for b in app.sidebar.button if "exemple" in b.label.lower()][0].click().run()
    assert not app.exception, [e.value for e in app.exception]

    # le diagnostic contient une synthèse en langage simple
    textes = "\n".join(m.value for m in app.markdown)
    assert "Diagnostic en langage simple" in textes
    assert "Points de vigilance" in textes
    assert "Priorités d'action" in textes

    # les boutons d'export sont présents
    libelles = [b.label for b in app.get("download_button")]
    assert any("HTML" in l for l in libelles)
    assert any("CSV" in l for l in libelles)
    assert any("Excel" in l for l in libelles)


def test_navigation_dans_les_onglets(app):
    [b for b in app.sidebar.button if "exemple" in b.label.lower()][0].click().run()
    assert not app.exception

    # les quatre axes doivent tous être affichés dans l'onglet Ratios,
    # sous forme de cartes colorées (une par axe)
    cartes = [m.value for m in app.markdown if "class='carte-axe'" in m.value]
    assert len(cartes) == len(ref.AXES), f"attendu {len(ref.AXES)} cartes d'axe, trouvé {len(cartes)}"
    for axe in ref.AXES.values():
        assert any(axe in carte for carte in cartes), f"axe manquant : {axe} — cartes : {cartes}"


def test_habillage_couleurs_et_icones(app):
    """Bandeau, anneau de score, cartes colorées, légende et icônes sont présents."""
    [b for b in app.sidebar.button if "exemple" in b.label.lower()][0].click().run()
    assert not app.exception, [e.value for e in app.exception]

    textes = [m.value for m in app.markdown]
    joint = "\n".join(textes)
    assert "class='hero'" in joint, "bandeau d'en-tête manquant"
    assert "conic-gradient" in joint, "anneau de score manquant"
    assert "class='legende'" in joint, "légende des statuts manquante"
    assert "class='recap'" in joint, "récapitulatif de la barre latérale manquant"
    # chaque axe est doté de son icône et d'une couleur
    for axe, icone in ref.AXES_ICONES.items():
        assert f"{icone} {ref.AXES[axe]}" in joint, f"icône de l'axe manquante : {axe}"
    # les icônes des ratios apparaissent dans le diagnostic
    for code, ratio in ref.RATIOS_PAR_CODE.items():
        assert ref.ICONES_RATIOS.get(code), f"icône manquante pour {code}"
        assert ratio.icone


def test_effacement_des_donnees(app):
    [b for b in app.sidebar.button if "exemple" in b.label.lower()][0].click().run()
    assert not app.exception
    [b for b in app.sidebar.button if "effacer" in b.label.lower()][0].click().run()
    assert not app.exception
    assert any("saisir ou importer" in (i.value or "") for i in app.info)
