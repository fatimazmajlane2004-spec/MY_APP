"""Tests du moteur de calcul (ratios, diagnostics, import/export).

Exécution :  pytest -q
"""

from __future__ import annotations

import math

import pandas as pd
import pytest

from finance import io_utils as iou
from finance import referentiel as ref
from finance import reporting as rep
from finance.diagnostic import (
    appreciation,
    construire_diagnostic,
    note_affichee,
    score_ratio,
    statut_depuis_score,
)
from finance.ratios import agreger_bilan, agreger_cpc, calculer_ratios, controler_coherence


# ---------------------------------------------------------------------------
# Jeux de données de test
# ---------------------------------------------------------------------------

BILAN_SAIN = {
    "IMMO_INCORP_CORP": 500_000,
    "IMMO_FINANCIERES": 50_000,
    "STOCKS": 200_000,
    "CLIENTS": 250_000,
    "AUTRES_CREANCES": 50_000,
    "VMP": 20_000,
    "DISPONIBILITES": 180_000,
    "CAPITAL": 400_000,
    "RESERVES": 50_000,
    "RESULTAT": 120_000,
    "EMPRUNTS": 300_000,
    "FOURNISSEURS": 220_000,
    "DETTES_SOCIALES": 80_000,
    "DETTES_FISCALES": 60_000,
    "AUTRES_DETTES_CT": 20_000,
    "CONCOURS_BANCAIRES": 0,
}

CPC_SAIN = {
    "CA": 2_000_000,
    "AUTRES_PRODUITS": 20_000,
    "ACHATS": 1_100_000,
    "CHARGES_EXTERNES": 250_000,
    "PERSONNEL": 400_000,
    "IMPOTS_TAXES": 30_000,
    "DOTATIONS": 80_000,
    "PRODUITS_FIN": 10_000,
    "CHARGES_FIN": 20_000,
    "IMPOT_RESULTAT": 30_000,
}


def _bilan_equilibre(valeurs):
    """Construit un bilan équilibré : les capitaux propres absorbent l'écart actif/passif."""
    actif = (
        valeurs.get("IMMO_INCORP_CORP", 0)
        + valeurs.get("IMMO_FINANCIERES", 0)
        + valeurs.get("STOCKS", 0)
        + valeurs.get("CLIENTS", 0)
        + valeurs.get("AUTRES_CREANCES", 0)
        + valeurs.get("VMP", 0)
        + valeurs.get("DISPONIBILITES", 0)
    )
    dettes = (
        valeurs.get("EMPRUNTS", 0)
        + valeurs.get("FOURNISSEURS", 0)
        + valeurs.get("DETTES_SOCIALES", 0)
        + valeurs.get("DETTES_FISCALES", 0)
        + valeurs.get("AUTRES_DETTES_CT", 0)
        + valeurs.get("CONCOURS_BANCAIRES", 0)
    )
    complet = dict(valeurs)
    complet["CAPITAL"] = actif - dettes  # capitaux propres = actif - dettes
    complet.setdefault("RESERVES", 0)
    complet.setdefault("RESULTAT", 0)
    return complet


# ---------------------------------------------------------------------------
# Agrégats
# ---------------------------------------------------------------------------

def test_agregats_bilan():
    agregats = agreger_bilan(BILAN_SAIN)
    assert agregats["immobilisations"] == 550_000
    assert agregats["actif_circulant"] == 500_000
    assert agregats["tresorerie_actif"] == 200_000
    assert agregats["total_actif"] == 1_250_000
    assert agregats["capitaux_propres"] == 570_000
    assert agregats["dettes_financieres"] == 300_000
    assert agregats["passif_circulant"] == 380_000
    assert agregats["total_passif"] == 1_250_000


def test_bilan_exemple_equilibre():
    bilan, cpc = iou.exemple_dataframe()
    postes_bilan, postes_bilan_n1 = iou.postes_depuis_editeur(bilan, ref.POSTES_BILAN)
    postes_cpc, postes_cpc_n1 = iou.postes_depuis_editeur(cpc, ref.POSTES_CPC)

    agregats = agreger_bilan(postes_bilan)
    assert math.isclose(agregats["total_actif"], agregats["total_passif"], rel_tol=1e-9)
    # le résultat du CPC doit correspondre à celui du bilan
    assert math.isclose(agreger_cpc(postes_cpc)["resultat_net"], postes_bilan["RESULTAT"], rel_tol=1e-9)

    # même contrôle sur l'exercice précédent
    agregats_n1 = agreger_bilan(postes_bilan_n1)
    assert math.isclose(agregats_n1["total_actif"], agregats_n1["total_passif"], rel_tol=1e-9)
    assert math.isclose(
        agreger_cpc(postes_cpc_n1)["resultat_net"], postes_bilan_n1["RESULTAT"], rel_tol=1e-9
    )
    # aucune alerte de cohérence ne doit être levée sur le jeu d'exemple
    assert controler_coherence(postes_bilan, postes_cpc) == []
    assert controler_coherence(postes_bilan_n1, postes_cpc_n1) == []


def test_agregats_cpc():
    agregats = agreger_cpc(CPC_SAIN)
    assert agregats["resultat_exploitation"] == pytest.approx(2_020_000 - 1_860_000)
    assert agregats["resultat_net"] == pytest.approx(120_000)
    assert agregats["caf"] == pytest.approx(200_000)
    assert agregats["valeur_ajoutee"] == pytest.approx(670_000)


# ---------------------------------------------------------------------------
# Ratios
# ---------------------------------------------------------------------------

def test_liquidite_et_fonds_de_roulement():
    res = calculer_ratios(BILAN_SAIN, CPC_SAIN)
    # Capitaux permanents (570 000 + 300 000) - immobilisations (550 000)
    assert res.fonds_roulement == pytest.approx(320_000)
    # BFR = (stocks 200 000 + clients 250 000 + autres 50 000) - 380 000
    assert res.bfr == pytest.approx(120_000)
    assert res.tresorerie_nette == pytest.approx(200_000)
    assert res.tresorerie_nette == pytest.approx(res.fonds_roulement - res.bfr)
    assert res.valeurs["LIQ_GENERALE"] == pytest.approx(700_000 / 380_000)


def test_ratios_solvabilite_et_rentabilite():
    res = calculer_ratios(BILAN_SAIN, CPC_SAIN)
    assert res.valeurs["AUTONOMIE_FINANCIERE"] == pytest.approx(570_000 / 1_250_000 * 100)
    assert res.valeurs["LEVIER"] == pytest.approx(300_000 / 570_000)
    assert res.valeurs["CAPACITE_REMBOURSEMENT"] == pytest.approx(300_000 / 200_000)
    assert res.valeurs["MARGE_NETTE"] == pytest.approx(6.0)
    assert res.valeurs["ROE"] == pytest.approx(120_000 / 570_000 * 100)
    # 360 x 250 000 / 2 000 000 = 45 jours
    assert res.valeurs["DELAI_CLIENTS"] == pytest.approx(45.0)
    # 360 x 200 000 / 1 100 000 = 65,45 jours
    assert res.valeurs["DELAI_STOCK"] == pytest.approx(360 * 200_000 / 1_100_000)


def test_moyennes_avec_exercice_precedent():
    bilan_n1, cpc_n1 = iou.exemple_dataframe()
    postes_bilan_n1, _ = iou.postes_depuis_editeur(bilan_n1, ref.POSTES_BILAN)
    postes_cpc_n1, _ = iou.postes_depuis_editeur(cpc_n1, ref.POSTES_CPC)

    res = calculer_ratios(BILAN_SAIN, CPC_SAIN, postes_bilan_n1, postes_cpc_n1)
    assert res.avec_n1()
    assert res.valeurs_n1["DELAI_CLIENTS"] is not None
    # le délai clients de N utilise la moyenne des créances N et N-1
    attendu = 360 * ((250_000 + 690_000) / 2) * 1.2 / (2_000_000 * 1.2)
    assert res.valeurs["DELAI_CLIENTS"] == pytest.approx(attendu)


def test_division_par_zero_protegee():
    bilan = _bilan_equilibre({"IMMO_INCORP_CORP": 100_000, "EMPRUNTS": 0})
    postes_cpc = {"CA": 0}
    res = calculer_ratios(bilan, postes_cpc)
    assert res.valeurs["MARGE_NETTE"] is None          # résultat nul / CA nul
    assert res.valeurs["LIQ_GENERALE"] is None         # passif circulant nul
    assert res.valeurs["ROTATION_ACTIF"] == 0.0        # aucun CA : aucune rotation


def test_capacite_remboursement_nulle_si_caf_negative():
    cpc = dict(CPC_SAIN)
    cpc["DOTATIONS"] = 0
    cpc["IMPOT_RESULTAT"] = 300_000  # provoque un résultat net négatif
    res = calculer_ratios(BILAN_SAIN, cpc)
    assert res.cpc["caf"] < 0
    assert res.valeurs["CAPACITE_REMBOURSEMENT"] is None
    titres = [a["titre"] for a in controler_coherence(BILAN_SAIN, cpc)]
    assert any("autofinancement" in t for t in titres)


def test_capacite_remboursement_nulle_sans_dette():
    bilan = _bilan_equilibre({"IMMO_INCORP_CORP": 100_000, "DISPONIBILITES": 100_000})
    res = calculer_ratios(bilan, CPC_SAIN)
    assert res.valeurs["CAPACITE_REMBOURSEMENT"] == 0.0


# ---------------------------------------------------------------------------
# Notation
# ---------------------------------------------------------------------------

def test_score_et_statut_coherents():
    ratio = ref.RATIOS_PAR_CODE["LIQ_GENERALE"]
    assert score_ratio(ratio, 1.8, None) == 100.0
    assert statut_depuis_score(score_ratio(ratio, 1.8, None)) == ref.STATUT_BON
    assert statut_depuis_score(score_ratio(ratio, 1.2, None)) == ref.STATUT_ACCEPTABLE
    assert statut_depuis_score(score_ratio(ratio, 0.6, None)) == ref.STATUT_VIGILANCE
    assert score_ratio(ratio, None, None) is None

    levier = ref.RATIOS_PAR_CODE["LEVIER"]
    assert statut_depuis_score(score_ratio(levier, 0.2, None)) == ref.STATUT_BON
    assert statut_depuis_score(score_ratio(levier, 0.8, None)) == ref.STATUT_ACCEPTABLE
    assert statut_depuis_score(score_ratio(levier, 2.5, None)) == ref.STATUT_VIGILANCE


def test_seuils_secteur_influencent_le_score():
    ratio = ref.RATIOS_PAR_CODE["DELAI_STOCK"]
    # 70 jours : vigilance pour les services, acceptable pour l'industrie
    assert statut_depuis_score(score_ratio(ratio, 70.0, "Services / conseil")) == ref.STATUT_VIGILANCE
    assert statut_depuis_score(score_ratio(ratio, 70.0, "Industrie / production")) == ref.STATUT_ACCEPTABLE


def test_note_affichee_ne_contredit_pas_l_appreciation():
    """La note affichée (tronquée) doit rester cohérente avec la mention qualitative."""
    assert note_affichee(54.6) == 54 and appreciation(54.6) == "fragile"
    assert note_affichee(55.0) == 55 and appreciation(55.0) == "satisfaisante"
    assert note_affichee(69.9) == 69 and appreciation(69.9) == "satisfaisante"
    assert note_affichee(70.0) == 70 and appreciation(70.0) == "solide"
    assert note_affichee(84.9) == 84 and appreciation(84.9) == "solide"
    assert note_affichee(85.0) == 85 and appreciation(85.0) == "très solide"
    assert note_affichee(None) is None

    for score in (0.0, 12.4, 39.9, 40.0, 54.9, 55.0, 69.9, 70.0, 84.9, 85.0, 100.0):
        affichee = note_affichee(score)
        assert affichee <= score < affichee + 1
        assert (affichee >= 55) == (score >= 55)


def test_evolution_formatee_selon_l_unite():
    from finance.diagnostic import _format_evolution

    assert _format_evolution(4.1, 3.5, "années") == ("+0,6 an(s)", "hausse")
    assert _format_evolution(76.0, 70.0, "jours") == ("+6 j", "hausse")
    assert _format_evolution(2.0, 3.5, "%") == ("-1,5 pt", "baisse")
    assert _format_evolution(1.27, 1.33, "x") == ("-0,06 pt", "baisse")
    assert _format_evolution(5.0, 5.0, "%") == ("stable", "stable")
    assert _format_evolution(None, 5.0, "%") == (None, None)


# ---------------------------------------------------------------------------
# Diagnostic
# ---------------------------------------------------------------------------

def test_diagnostic_complet():
    res = calculer_ratios(BILAN_SAIN, CPC_SAIN)
    diag = construire_diagnostic(res, secteur=ref.SECTEURS[0], nom_entreprise="Test SA")
    assert diag.score_global is not None
    assert 0 <= diag.score_global <= 100
    assert set(diag.scores_axes) == set(ref.AXES)
    assert diag.lignes, "le diagnostic doit contenir des lignes"
    assert all(l.texte for l in diag.lignes)
    assert "n.d." not in diag.lignes[0].texte or diag.lignes[0].valeur is None
    assert diag.recommandations
    # chaque ratio noté doit avoir un statut connu
    for ligne in diag.lignes:
        assert ligne.statut in ref.COULEURS_STATUT


def test_diagnostic_entreprise_fragile():
    bilan = _bilan_equilibre(
        {
            "IMMO_INCORP_CORP": 900_000,
            "STOCKS": 700_000,
            "CLIENTS": 900_000,
            "DISPONIBILITES": 10_000,
            "EMPRUNTS": 800_000,
            "FOURNISSEURS": 800_000,
            "DETTES_SOCIALES": 200_000,
            "DETTES_FISCALES": 150_000,
            "CONCOURS_BANCAIRES": 400_000,
        }
    )
    cpc = {
        "CA": 3_000_000,
        "ACHATS": 2_400_000,
        "CHARGES_EXTERNES": 400_000,
        "PERSONNEL": 300_000,
        "DOTATIONS": 60_000,
        "CHARGES_FIN": 80_000,
        "IMPOT_RESULTAT": 0,
    }
    res = calculer_ratios(bilan, cpc)
    diag = construire_diagnostic(res, nom_entreprise="Société fragile")
    assert diag.score_global is not None
    assert diag.score_global < 55
    assert diag.points_vigilance, "une situation dégradée doit générer des points de vigilance"
    assert diag.appreciation in ("fragile", "critique")


# ---------------------------------------------------------------------------
# Contrôles de cohérence
# ---------------------------------------------------------------------------

def test_alertes_coherence():
    bilan_desequilibre = dict(BILAN_SAIN)
    bilan_desequilibre["DISPONIBILITES"] = 999_000  # déséquilibre le bilan
    titres = [a["titre"] for a in controler_coherence(bilan_desequilibre, CPC_SAIN)]
    assert any("équilibré" in t for t in titres)

    cpc_incoherent = dict(CPC_SAIN)
    cpc_incoherent["IMPOT_RESULTAT"] = 60_000  # résultat net du CPC ≠ résultat du bilan
    titres = [a["titre"] for a in controler_coherence(BILAN_SAIN, cpc_incoherent)]
    assert any("résultat net" in t for t in titres)


def test_aucune_alerte_sur_bilan_correct():
    assert controler_coherence(BILAN_SAIN, CPC_SAIN) == []


# ---------------------------------------------------------------------------
# Import / export
# ---------------------------------------------------------------------------

def test_aller_retour_modele_excel():
    contenu = iou.exporter_modele_excel()
    assert contenu[:2] == b"PK"  # signature d'un fichier xlsx
    resultat = iou.importer_fichiers([("modele.xlsx", contenu)])
    assert resultat["bilan"] and resultat["cpc"]
    assert all(v == 0.0 for v in resultat["bilan"].values())


def test_aller_retour_donnees_excel():
    bilan, cpc = iou.exemple_dataframe()
    postes_bilan, postes_bilan_n1 = iou.postes_depuis_editeur(bilan, ref.POSTES_BILAN)
    postes_cpc, postes_cpc_n1 = iou.postes_depuis_editeur(cpc, ref.POSTES_CPC)

    contenu = iou.exporter_donnees_excel(postes_bilan, postes_bilan_n1, postes_cpc, postes_cpc_n1)
    importe = iou.importer_fichiers([("donnees.xlsx", contenu)])
    assert importe["bilan"] == pytest.approx(postes_bilan)
    assert importe["cpc"] == pytest.approx(postes_cpc)
    assert importe["bilan_n1"] == pytest.approx(postes_bilan_n1)


def test_import_csv_avec_libelles():
    df = pd.DataFrame(
        {
            "Poste": ["Chiffre d'affaires (CA)", "Charges de personnel", "Achats consommés (marchandises, matières premières)"],
            "Montant": ["1 500 000", 300000, "800 000"],
        }
    )
    postes_n, postes_n1, avertissements = iou.df_vers_postes(df)
    assert postes_n["CA"] == 1_500_000
    assert postes_n["PERSONNEL"] == 300_000
    assert postes_n["ACHATS"] == 800_000
    assert postes_n1 == {}


def test_import_ignore_lignes_inconnues():
    df = pd.DataFrame({"Code": ["CA", "XXX_INCONNU"], "Poste": ["Chiffre d'affaires", "Ligne bizarre"], "N": [1000, 500]})
    postes_n, _, avertissements = iou.df_vers_postes(df)
    assert postes_n == {"CA": 1000.0}
    assert any("Ligne ignorée" in a for a in avertissements)


def test_editeur_aller_retour():
    df = iou.modele_editeur(ref.POSTES_BILAN)
    df.loc[df["Code"] == "STOCKS", "Exercice N"] = 123456
    postes_n, postes_n1 = iou.postes_depuis_editeur(df, ref.POSTES_BILAN)
    assert postes_n["STOCKS"] == 123456
    assert postes_n1 == {}, "un exercice N-1 vide ne doit pas être interprété comme des zéros"


# ---------------------------------------------------------------------------
# Rapports
# ---------------------------------------------------------------------------

def test_rapports_generes():
    res = calculer_ratios(BILAN_SAIN, CPC_SAIN)
    diag = construire_diagnostic(res, nom_entreprise="Test SA")
    meta = {"entreprise": "Test SA", "exercice": "2025", "secteur": ref.SECTEURS[0], "unite": "en euros"}

    markdown = rep.rapport_markdown(diag, res, meta)
    assert "Test SA" in markdown and "Synthèse" in markdown

    html = rep.rapport_html(diag, res, meta)
    assert html.startswith("<!DOCTYPE html>")
    assert html.count("<div class='ratio'") == len([l for l in diag.lignes])

    tableau = rep.tableau_ratios(diag)
    assert len(tableau) == len(diag.lignes)
    assert set(["Axe", "Ratio", "Valeur", "Statut"]).issubset(tableau.columns)


def test_echappement_html():
    res = calculer_ratios(BILAN_SAIN, CPC_SAIN)
    diag = construire_diagnostic(res, nom_entreprise="<script>alert(1)</script>")
    meta = {"entreprise": "<script>alert(1)</script>", "exercice": "2025", "secteur": "", "unite": ""}
    html = rep.rapport_html(diag, res, meta)
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html
