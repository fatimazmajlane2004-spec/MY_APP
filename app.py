"""
Diagnostic financier automatique — application Streamlit.

L'utilisateur importe (ou saisit) un bilan et un compte de produits et charges.
L'application calcule les ratios de liquidité, solvabilité, rentabilité et
rotation, puis produit un diagnostic rédigé en langage simple.

Lancement :  streamlit run app.py
"""

from __future__ import annotations

import datetime as _dt
import html as _html
import inspect
from typing import List

import altair as alt
import pandas as pd
import streamlit as st
import streamlit.components.v1 as composants

from finance import io_utils as iou
from finance import referentiel as ref
from finance import reporting as rep
from finance.diagnostic import (
    Diagnostic,
    LigneDiagnostic,
    construire_diagnostic,
    couleur_score,
    note_affichee as _note_affichee,
    statut_depuis_score,
)
from finance.ratios import calculer_ratios, controler_coherence


def _api_largeur_moderne() -> bool:
    """True si la version de Streamlit installée utilise ``width="stretch"``
    (les anciennes versions utilisaient ``use_container_width=True``)."""
    try:
        annotation = inspect.signature(st.dataframe).parameters["use_container_width"].annotation
        return "None" in str(annotation)
    except (KeyError, ValueError, TypeError):
        return False


#: Arguments de largeur à passer aux composants, selon la version de Streamlit
PLEINE_LARGEUR = {"width": "stretch"} if _api_largeur_moderne() else {"use_container_width": True}

# ---------------------------------------------------------------------------
# Configuration générale
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Diagnostic financier",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

UNITES = ["en euros", "en milliers d'euros", "en millions d'euros", "en francs CFA", "en dirhams", "en dollars"]

# Symbole affiché après les montants, en cohérence avec l'unité choisie
SYMBOLES_UNITE = {
    "en euros": "€",
    "en milliers d'euros": "k€",
    "en millions d'euros": "M€",
    "en francs CFA": "FCFA",
    "en dirhams": "MAD",
    "en dollars": "$",
}

CSS = """
<style>
    /* ===== Palette ==================================================== */
    :root {
        --vert: #1a9850; --orange: #f4a300; --rouge: #d73027;
        --bleu: #2563eb; --bleu-fonce: #1e3a8a; --ardoise: #334155;
        --gris: #64748b; --bord: #e6eaf1; --fond: #f6f8fc;
    }
    .stApp { background: var(--fond); }
    .block-container { padding-top: 2rem; }

    /* ===== Barre latérale ============================================= */
    [data-testid="stSidebar"] { background: #ffffff; border-right: 1px solid var(--bord); }
    [data-testid="stSidebar"] h2 { color: var(--bleu); font-size: 1.05rem;
        border-left: 5px solid var(--bleu); border-bottom: none; padding-left: 10px; }
    [data-testid="stSidebar"] hr { border-color: var(--bord); }

    /* ===== Titres ===================================================== */
    h1, h2, h3 { color: var(--ardoise); }
    h2 { border-left: 5px solid var(--bleu); padding-left: 11px; border-bottom: none; }
    h3 { border-left: 4px solid #cbd5e1; padding-left: 10px; }

    /* ===== Onglets ==================================================== */
    .stTabs [data-baseweb="tab"], .stTabs [data-testid="stTab"] {
        background: #eef2f9; border-radius: 10px 10px 0 0; padding: 7px 15px;
        margin-right: 6px; height: auto; min-height: 40px; align-items: center;
    }
    .stTabs [data-baseweb="tab"] p, .stTabs [data-testid="stTab"] p {
        color: #475569; font-weight: 600; font-size: .92rem;
    }
    .stTabs [data-baseweb="tab"]:hover, .stTabs [data-testid="stTab"]:hover { background: #e2e9f6; }
    .stTabs [aria-selected="true"] { background: #ffffff !important; }
    .stTabs [aria-selected="true"] p { color: var(--bleu); }
    .stTabs [data-baseweb="tab-list"], .stTabs [role="tablist"] { gap: 6px; border-bottom: 2px solid var(--bord); }
    .stTabs .react-aria-SelectionIndicator { background: var(--bleu) !important; }

    /* ===== Indicateurs ================================================ */
    [data-testid="stMetric"] {
        background: #ffffff; border: 1px solid var(--bord); border-left: 6px solid var(--bleu);
        border-radius: 14px; padding: 14px 18px; box-shadow: 0 1px 4px rgba(15, 23, 42, .05);
    }
    [data-testid="stMetricLabel"] { color: var(--gris); font-size: .85rem; }
    [data-testid="stMetricValue"] { color: var(--ardoise); font-size: 1.45rem; font-weight: 700; }

    /* ===== Boutons ==================================================== */
    .stButton > button, .stDownloadButton > button {
        border-radius: 10px; font-weight: 600; border: 1px solid var(--bord);
    }
    .stButton > button:hover, .stDownloadButton > button:hover {
        border-color: var(--bleu); color: var(--bleu);
    }
    .stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"] {
        background: linear-gradient(135deg, #2563eb, #1e40af); border: none; color: #ffffff;
    }

    /* ===== Conteneurs ================================================= */
    [data-testid="stExpander"] { border: 1px solid var(--bord); border-radius: 12px; background: #ffffff; }
    [data-testid="stExpander"] summary { font-weight: 600; }
    [data-testid="stExpander"] summary:hover { color: var(--bleu); }
    [data-testid="stDataFrame"], [data-testid="stDataEditor"] {
        border-radius: 12px; border: 1px solid var(--bord); overflow: hidden;
    }

    /* ===== Bandeau d'en-tête ========================================== */
    .hero {
        background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 55%, #0ea5e9 100%);
        border-radius: 16px; padding: 22px 28px; margin-bottom: 16px; color: #ffffff;
        box-shadow: 0 8px 22px rgba(37, 99, 235, .28);
    }
    .hero h1 { color: #ffffff; margin: 0; font-size: 1.65rem; border: none; padding: 0; }
    .hero p { margin: 6px 0 0; font-size: .95rem; opacity: .93; }
    .hero .puces { margin-top: 12px; }
    .hero .puces span {
        display: inline-block; background: rgba(255, 255, 255, .18); border: 1px solid rgba(255,255,255,.25);
        padding: 4px 13px; border-radius: 999px; margin: 0 7px 6px 0; font-size: .82rem; font-weight: 500;
    }

    /* ===== Anneau de score ============================================ */
    .carte-note {
        background: #ffffff; border: 1px solid var(--bord); border-radius: 16px;
        padding: 16px; text-align: center; height: 100%;
        box-shadow: 0 1px 4px rgba(15, 23, 42, .05);
    }
    .anneau { width: 152px; height: 152px; border-radius: 50%; padding: 13px; margin: 0 auto; }
    .anneau-centre {
        width: 100%; height: 100%; border-radius: 50%; background: #ffffff;
        display: flex; flex-direction: column; align-items: center; justify-content: center;
        box-shadow: inset 0 0 0 1px #eef2f9;
    }
    .anneau-valeur { font-size: 2.05rem; font-weight: 800; line-height: 1; }
    .anneau-centre small { font-size: .72rem; color: #94a3b8; }
    .anneau-legende { font-size: .74rem; color: var(--gris); margin-top: 8px; }
    .anneau-legende strong { display: block; font-size: .86rem; color: var(--ardoise); }

    /* ===== Cartes par axe ============================================= */
    .carte-axe {
        background: #ffffff; border: 1px solid var(--bord); border-radius: 14px;
        padding: 14px 16px; height: 100%; box-shadow: 0 1px 4px rgba(15, 23, 42, .05);
    }
    .carte-axe .titre { font-size: .88rem; color: var(--ardoise); font-weight: 600; }
    .carte-axe .score { font-size: 1.75rem; font-weight: 800; line-height: 1.3; }
    .carte-axe .score small, .carte-axe .detail small { font-size: .7rem; color: var(--gris); font-weight: 500; }
    .carte-axe .detail { font-size: .72rem; color: var(--gris); }
    .barre { height: 7px; background: #eef2f9; border-radius: 999px; overflow: hidden; margin: 6px 0 8px; }
    .barre span { display: block; height: 100%; border-radius: 999px; }

    /* ===== Cartes de ratio ============================================ */
    .bloc-ratio {
        border-left: 5px solid #cbd5e1; background: #ffffff; padding: 14px 18px;
        border-radius: 0 10px 10px 0; margin: 10px 0; border-top: 1px solid var(--bord);
        border-right: 1px solid var(--bord); border-bottom: 1px solid var(--bord);
    }
    .bloc-ratio h4 { margin: 0 0 6px 0; font-size: 1.02rem; color: var(--ardoise); }
    .badge {
        display: inline-block; padding: 2px 11px; border-radius: 999px; color: #ffffff;
        font-size: 0.74rem; font-weight: 600; margin-left: 6px; vertical-align: middle;
    }
    .formule { font-family: Consolas, monospace; font-size: 0.78rem; color: var(--gris); margin-bottom: 6px; }
    .petit { font-size: 0.83rem; color: var(--gris); }

    /* ===== Récapitulatif (barre latérale) ============================= */
    .recap {
        background: linear-gradient(135deg, #eef4ff, #ffffff); border: 1px solid var(--bord);
        border-radius: 14px; padding: 14px 16px; margin: 4px 0 10px;
    }
    .recap-note { font-size: 2rem; font-weight: 800; line-height: 1; display: inline-block; }
    .recap-note small { font-size: .78rem; color: var(--gris); font-weight: 500; }
    .recap-situation { font-size: .79rem; color: var(--gris); margin-top: 6px; }
    .recap-ligne {
        display: flex; justify-content: space-between; align-items: center;
        padding: 5px 2px; font-size: .82rem; color: var(--ardoise);
        border-bottom: 1px dashed #eef2f9;
    }

    /* ===== Légende ==================================================== */
    .legende { display: flex; flex-wrap: wrap; gap: 18px; align-items: center;
               background: #ffffff; border: 1px solid var(--bord); border-radius: 12px;
               padding: 10px 16px; font-size: .84rem; color: var(--gris); margin: 6px 0 14px; }
    .legende b { color: var(--ardoise); }
    .pastille { display: inline-block; width: 11px; height: 11px; border-radius: 50%;
                margin-right: 6px; vertical-align: middle; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# État de session
# ---------------------------------------------------------------------------

def initialiser_etat() -> None:
    defauts = {
        "entreprise": "Ma société",
        "exercice": str(_dt.date.today().year - 1),
        "secteur": ref.SECTEURS[0],
        "unite": UNITES[0],
        "taux_tva": 20.0,
    }
    for cle, valeur in defauts.items():
        st.session_state.setdefault(cle, valeur)
    if "tableau_bilan" not in st.session_state:
        st.session_state["tableau_bilan"] = iou.modele_editeur(ref.POSTES_BILAN)
    if "tableau_cpc" not in st.session_state:
        st.session_state["tableau_cpc"] = iou.modele_editeur(ref.POSTES_CPC)


def remplacer_tableaux(df_bilan: pd.DataFrame, df_cpc: pd.DataFrame) -> None:
    """Remplace les données saisies et réinitialise les éditeurs Streamlit."""
    st.session_state["tableau_bilan"] = df_bilan
    st.session_state["tableau_cpc"] = df_cpc
    for cle in ("editeur_bilan", "editeur_cpc"):
        st.session_state.pop(cle, None)


initialiser_etat()


# ---------------------------------------------------------------------------
# Barre latérale : paramètres
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("## ⚙️ Paramètres")
    st.session_state["entreprise"] = st.text_input("Nom de l'entreprise", st.session_state["entreprise"])
    colonne_1, colonne_2 = st.columns(2)
    with colonne_1:
        st.session_state["exercice"] = st.text_input("Exercice analysé (N)", st.session_state["exercice"])
    with colonne_2:
        st.session_state["taux_tva"] = st.number_input(
            "TVA (%)", min_value=0.0, max_value=30.0, step=1.0,
            value=float(st.session_state["taux_tva"]),
            help="Utilisée pour remettre les flux d'achats en TTC dans le délai fournisseurs.",
        )
    st.session_state["secteur"] = st.selectbox(
        "Secteur d'activité",
        ref.SECTEURS,
        index=ref.SECTEURS.index(st.session_state["secteur"]),
        help="Les repères (seuils) des ratios s'adaptent au secteur choisi.",
    )
    st.session_state["unite"] = st.selectbox(
        "Unité des montants", UNITES, index=UNITES.index(st.session_state["unite"])
    )

    st.divider()
    if st.button("🎲 Charger un exemple", **PLEINE_LARGEUR):
        bilan, cpc = iou.exemple_dataframe()
        remplacer_tableaux(bilan, cpc)
        st.session_state["entreprise"] = "Société Industrielle Dupont"
        st.rerun()
    if st.button("🧹 Tout effacer", **PLEINE_LARGEUR):
        remplacer_tableaux(iou.modele_editeur(ref.POSTES_BILAN), iou.modele_editeur(ref.POSTES_CPC))
        st.rerun()

    st.divider()
    with st.expander("📥 Modèles de fichiers"):
        st.download_button(
            "Modèle Excel (.xlsx)",
            data=iou.exporter_modele_excel(),
            file_name="modele_bilan_cpc.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            **PLEINE_LARGEUR,
        )
        for nom, contenu in iou.exporter_modele_csv().items():
            st.download_button(nom, data=contenu, file_name=nom, mime="text/csv", **PLEINE_LARGEUR)

    st.caption(
        "Les ratios sont calculés sur la base d'une année de 360 jours. "
        "Les repères sont des moyennes de marché : adaptez-les à votre activité."
    )


# ---------------------------------------------------------------------------
# Bandeau d'en-tête
# ---------------------------------------------------------------------------

_e = _html.escape

_puces = [
    f"🏢 {_e(st.session_state['entreprise'] or 'Entreprise à nommer')}",
    f"📅 Exercice {_e(st.session_state['exercice'])}",
    f"🏭 {_e(st.session_state['secteur'])}",
    f"💰 {_e(st.session_state['unite'])}",
]
st.markdown(
    "<div class='hero'>"
    "<h1>📊 Diagnostic financier automatique</h1>"
    "<p>Importez votre bilan et votre compte de produits et charges : les ratios et le "
    "diagnostic s'affichent automatiquement, expliqués sans jargon.</p>"
    f"<div class='puces'>{''.join(f'<span>{p}</span>' for p in _puces)}</div>"
    "</div>",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Onglets
# ---------------------------------------------------------------------------

onglet_donnees, onglet_ratios, onglet_diagnostic, onglet_rapport = st.tabs(
    ["1️⃣ Données", "2️⃣ Ratios", "3️⃣ Diagnostic", "4️⃣ Rapport"]
)


# --- Onglet 1 : saisie / import -------------------------------------------

with onglet_donnees:
    st.markdown("### 📥 Importez vos états financiers")
    st.caption(
        "Déposez un classeur Excel contenant deux feuilles (Bilan et CPC) ou deux fichiers séparés. "
        "Le modèle téléchargeable (barre latérale) contient les codes de postes reconnus automatiquement. "
        "Vous pouvez aussi tout saisir à la main dans les tableaux ci-dessous."
    )

    fichiers = st.file_uploader(
        "Fichiers Excel ou CSV",
        type=["xlsx", "xlsm", "xls", "csv"],
        accept_multiple_files=True,
        help="Formats acceptés : .xlsx, .xlsm, .xls, .csv (séparateur virgule, point-virgule ou tabulation).",
    )
    if fichiers:
        if st.button("📤 Importer ces fichiers", type="primary"):
            contenu = [(f.name, f.getvalue()) for f in fichiers]
            try:
                importe = iou.importer_fichiers(contenu)
            except ValueError as erreur:
                st.error(str(erreur))
            else:
                tableau_bilan = iou.appliquer_import(
                    st.session_state["tableau_bilan"], importe["bilan"], "Exercice N"
                )
                tableau_bilan = iou.appliquer_import(tableau_bilan, importe["bilan_n1"], "Exercice N-1")
                tableau_cpc = iou.appliquer_import(
                    st.session_state["tableau_cpc"], importe["cpc"], "Exercice N"
                )
                tableau_cpc = iou.appliquer_import(tableau_cpc, importe["cpc_n1"], "Exercice N-1")

                if not importe["bilan"] and not importe["cpc"]:
                    st.error("Aucun poste reconnu. Vérifiez que le fichier suit le modèle fourni.")
                else:
                    remplacer_tableaux(tableau_bilan, tableau_cpc)
                    st.session_state["_messages_import"] = importe["messages"]
                    st.rerun()

    for message in st.session_state.pop("_messages_import", []):
        if str(message).startswith("✅"):
            st.success(message)
        elif str(message).startswith("⚠️"):
            st.warning(message)
        else:
            st.info(message)

    with st.expander("❓ Que mettre dans chaque poste ?", expanded=False):
        st.markdown(
            "**Bilan** — les montants *nets* (après amortissements) à la clôture de l'exercice. "
            "Le total de l'actif doit être égal au total du passif.\n\n"
            "**CPC** — les flux de l'exercice (produits et charges), enregistrés en HT. "
            "Les dotations aux amortissements doivent être saisies : elles servent à calculer la capacité "
            "d'autofinancement (CAF), donc la capacité de remboursement."
        )
        st.dataframe(
            pd.DataFrame(
                [
                    [ref.GROUPES[p.groupe], p.libelle, p.aide]
                    for p in ref.POSTES_BILAN + ref.POSTES_CPC
                ],
                columns=["Rubrique", "Poste", "Explication"],
            ),
            hide_index=True,
            **PLEINE_LARGEUR,
            height=280,
        )

    st.divider()

    sous_bilan, sous_cpc = st.tabs(["📗 Bilan", "📘 Compte de produits et charges"])

    def config_montant(titre: str):
        return st.column_config.NumberColumn(
            titre,
            help="Montant dans l'unité choisie dans la barre latérale. Laissez vide si le poste n'existe pas.",
            format="localized",
        )

    with sous_bilan:
        st.markdown("#### 📗 Bilan (montants nets, à la clôture)")
        tableau_bilan = st.data_editor(
            st.session_state["tableau_bilan"],
            key="editeur_bilan",
            **PLEINE_LARGEUR,
            hide_index=True,
            height=560,
            disabled=["Code", "Rubrique", "Poste"],
            column_config={
                "Code": None,
                "Rubrique": st.column_config.TextColumn("Rubrique"),
                "Poste": st.column_config.TextColumn("Poste", width="large"),
                "Exercice N": config_montant(f"Exercice {st.session_state['exercice']} (N)"),
                "Exercice N-1": config_montant("Exercice N-1 (facultatif)"),
            },
        )

    with sous_cpc:
        st.markdown("#### 📘 Compte de produits et charges (flux de l'exercice)")
        tableau_cpc = st.data_editor(
            st.session_state["tableau_cpc"],
            key="editeur_cpc",
            **PLEINE_LARGEUR,
            hide_index=True,
            height=460,
            disabled=["Code", "Rubrique", "Poste"],
            column_config={
                "Code": None,
                "Rubrique": st.column_config.TextColumn("Rubrique"),
                "Poste": st.column_config.TextColumn("Poste", width="large"),
                "Exercice N": config_montant(f"Exercice {st.session_state['exercice']} (N)"),
                "Exercice N-1": config_montant("Exercice N-1 (facultatif)"),
            },
        )

    st.session_state["tableau_bilan"] = tableau_bilan
    st.session_state["tableau_cpc"] = tableau_cpc


# --- Calculs ---------------------------------------------------------------

postes_bilan, postes_bilan_n1 = iou.postes_depuis_editeur(st.session_state["tableau_bilan"], ref.POSTES_BILAN)
postes_cpc, postes_cpc_n1 = iou.postes_depuis_editeur(st.session_state["tableau_cpc"], ref.POSTES_CPC)

if not any(postes_bilan.values()):
    st.info(
        "👈 Commencez par saisir ou importer un bilan et un compte de produits et charges, "
        "ou cliquez sur **🎲 Charger un exemple** dans la barre latérale pour voir le fonctionnement."
    )
    st.stop()

# L'exercice précédent n'est retenu que s'il contient réellement des montants
if not any(postes_bilan_n1.values()):
    postes_bilan_n1 = {}
if not any(postes_cpc_n1.values()):
    postes_cpc_n1 = {}

resultat = calculer_ratios(
    postes_bilan,
    postes_cpc,
    postes_bilan_n1 or None,
    postes_cpc_n1 or None,
    taux_tva=st.session_state["taux_tva"] / 100.0,
)
alertes = controler_coherence(postes_bilan, postes_cpc)
diag = construire_diagnostic(
    resultat,
    secteur=st.session_state["secteur"],
    nom_entreprise=st.session_state["entreprise"] or "L'entreprise",
    alertes=alertes,
    unite_courte=SYMBOLES_UNITE.get(st.session_state["unite"], ""),
)
meta = {
    "entreprise": st.session_state["entreprise"] or "Entreprise",
    "exercice": st.session_state["exercice"],
    "secteur": st.session_state["secteur"],
    "unite": st.session_state["unite"],
}


# --- Récapitulatif dans la barre latérale ----------------------------------

with st.sidebar:
    st.divider()
    st.markdown("## 🧾 Récapitulatif")
    if diag.score_global is not None:
        couleur_note = couleur_score(diag.score_global)
        icone_note = ref.ICONES_APPRECIATION.get(diag.appreciation, "")
        st.markdown(
            f"<div class='recap'><div class='recap-note' style='color:{couleur_note}'>"
            f"{_note_affichee(diag.score_global)}<small>/100</small></div>"
            f"<div class='recap-situation'>Situation <strong>{icone_note} {_html.escape(diag.appreciation)}</strong><br>"
            f"{len(diag.points_forts)} point(s) fort(s) · {len(diag.points_vigilance)} point(s) de vigilance</div></div>",
            unsafe_allow_html=True,
        )
    for axe in ref.AXES:
        score = diag.scores_axes.get(axe)
        pastille = ref.ICONES_STATUT.get(statut_depuis_score(score), "⚪")
        valeur = f"{_note_affichee(score)}/100" if score is not None else "n.d."
        st.markdown(
            f"<div class='recap-ligne'><span>{ref.AXES_ICONES[axe]} {ref.AXES[axe]}</span>"
            f"<span>{pastille} {valeur}</span></div>",
            unsafe_allow_html=True,
        )


# --- Composants d'affichage ------------------------------------------------

def badge(statut: str) -> str:
    couleur = ref.COULEURS_STATUT.get(statut, "#9e9e9e")
    return f'<span class="badge" style="background:{couleur}">{_html.escape(statut)}</span>'


def carte_ratio_html(ligne: LigneDiagnostic, symbole: str = "", avec_conseil: bool = True) -> str:
    morceaux = [f'<div class="bloc-ratio" style="border-left-color:{ligne.couleur}">']
    morceaux.append(
        f"<h4>{ligne.icone} {_html.escape(ligne.libelle)} : "
        f"<strong>{rep._valeur_texte(ligne.valeur, ligne.unite, symbole)}</strong>"
        f"{badge(ligne.statut)}</h4>"
    )
    morceaux.append(f'<div class="formule">{ligne.formule}</div>')
    if ligne.evolution:
        fleche = "↗️" if ligne.tendance == "hausse" else ("↘️" if ligne.tendance == "baisse" else "→")
        morceaux.append(
            f'<div class="petit">Évolution : {fleche} {ligne.evolution} '
            f"(N-1 : {rep._valeur_texte(ligne.valeur_n1, ligne.unite, symbole)})</div>"
        )
    morceaux.append(f"<p style='margin:8px 0 4px'>{ligne.texte}</p>")
    morceaux.append(f"<p class='petit' style='margin:0'><em>À quoi ça sert :</em> {ligne.definition}</p>")
    if avec_conseil and ligne.conseil and ligne.statut == ref.STATUT_VIGILANCE:
        morceaux.append(f"<p class='petit' style='margin:6px 0 0'><strong>Piste d'amélioration :</strong> {ligne.conseil}</p>")
    morceaux.append("</div>")
    return "".join(morceaux)


def graphique_scores(diag: Diagnostic) -> alt.Chart:
    donnees = pd.DataFrame(
        [
            {
                "Axe": f"{ref.AXES_ICONES.get(axe, '')} {ref.AXES[axe]}",
                "Score": diag.scores_axes.get(axe),
            }
            for axe in ref.AXES
        ]
    ).dropna()
    return (
        alt.Chart(donnees)
        .mark_bar(cornerRadiusEnd=4)
        .encode(
            x=alt.X("Score:Q", scale=alt.Scale(domain=[0, 100]), title="Score / 100"),
            y=alt.Y("Axe:N", sort="-x", title=None),
            color=alt.Color(
                "Score:Q",
                scale=alt.Scale(domain=[0, 55, 85, 100], range=["#d73027", "#f4a300", "#1a9850", "#1a9850"]),
                legend=None,
            ),
            tooltip=["Axe", alt.Tooltip("Score:Q", format=".0f")],
        )
        .properties(height=180)
    )


def graphique_structure(resultat) -> alt.Chart:
    b = resultat.bilan
    lignes = [
        ("Actif", "Immobilisations", b["immobilisations"]),
        ("Actif", "Stocks", b["stocks"]),
        ("Actif", "Créances clients et autres", b["actif_circulant"] - b["stocks"]),
        ("Actif", "Trésorerie", b["tresorerie_actif"]),
        ("Passif", "Capitaux propres", b["capitaux_propres"]),
        ("Passif", "Dettes financières", b["dettes_financieres"]),
        ("Passif", "Dettes à court terme", b["passif_circulant"]),
        ("Passif", "Concours bancaires", b["tresorerie_passif"]),
    ]
    donnees = pd.DataFrame(lignes, columns=["Côté", "Poste", "Montant"])
    donnees = donnees[donnees["Montant"] != 0]
    return (
        alt.Chart(donnees)
        .mark_bar()
        .encode(
            x=alt.X("Montant:Q", title=f"Montant ({st.session_state['unite']})"),
            y=alt.Y("Côté:N", title=None),
            color=alt.Color("Poste:N", legend=alt.Legend(orient="bottom", columns=3)),
            order=alt.Order("Montant:Q", sort="descending"),
            tooltip=["Côté", "Poste", alt.Tooltip("Montant:Q", format=",.0f")],
        )
        .properties(height=170)
    )


def graphique_evolution(diag: Diagnostic, codes: List[str]) -> alt.Chart:
    donnees = []
    for code in codes:
        ligne = diag.ligne_par_code.get(code)
        if not ligne or ligne.valeur is None or ligne.valeur_n1 is None:
            continue
        donnees.append({"Ratio": ligne.libelle, "Exercice": f"N-1 ({st.session_state['exercice'][:4]})", "Valeur": ligne.valeur_n1})
        donnees.append({"Ratio": ligne.libelle, "Exercice": "N", "Valeur": ligne.valeur})
    df = pd.DataFrame(donnees)
    return (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X("Ratio:N", title=None, axis=alt.Axis(labelAngle=-25)),
            xOffset="Exercice:N",
            y=alt.Y("Valeur:Q", title="Valeur"),
            color=alt.Color("Exercice:N", scale=alt.Scale(range=["#94a3b8", "#2563eb"]), legend=alt.Legend(orient="top")),
            tooltip=["Ratio", "Exercice", alt.Tooltip("Valeur:Q", format=",.2f")],
        )
        .properties(height=300)
    )


# --- Onglet 2 : ratios -----------------------------------------------------

with onglet_ratios:
    colonnes = st.columns([1.3, 1, 1, 1, 1])

    with colonnes[0]:
        note = _note_affichee(diag.score_global)
        couleur_note = couleur_score(diag.score_global)
        remplissage = max(0.0, min(100.0, diag.score_global or 0.0))
        icone_note = ref.ICONES_APPRECIATION.get(diag.appreciation, "")
        st.markdown(
            "<div class='carte-note'>"
            f"<div class='anneau' style='background:conic-gradient({couleur_note} 0% {remplissage:.1f}%, #e6eaf1 0%)'>"
            "<div class='anneau-centre'>"
            f"<span class='anneau-valeur' style='color:{couleur_note}'>{note if note is not None else 'n.d.'}</span>"
            "<small>/100</small></div></div>"
            f"<div class='anneau-legende'><strong>{icone_note} {diag.appreciation}</strong>"
            "Note globale pondérée</div></div>",
            unsafe_allow_html=True,
        )

    for colonne, axe in zip(colonnes[1:], ref.AXES):
        score = diag.scores_axes.get(axe)
        with colonne:
            couleur_axe = couleur_score(score)
            largeur_barre = max(3.0, min(100.0, score or 0.0))
            st.markdown(
                f"<div class='carte-axe' style='border-top:4px solid {couleur_axe}' "
                f"title='{_e(ref.AXES_DESCRIPTIONS[axe])}'>"
                f"<div class='titre'>{ref.AXES_ICONES[axe]} {ref.AXES[axe]}</div>"
                f"<div class='score' style='color:{couleur_axe}'>"
                f"{_note_affichee(score) if score is not None else 'n.d.'}<small>/100</small></div>"
                f"<div class='barre'><span style='width:{largeur_barre:.0f}%;background:{couleur_axe}'></span></div>"
                f"<div class='detail'>Poids {ref.POIDS_AXES[axe]:.0%} de la note globale</div></div>",
                unsafe_allow_html=True,
            )

    st.markdown(
        "<div class='legende'><b>Comment lire les notes :</b>"
        f"<span><span class='pastille' style='background:{ref.COULEURS_STATUT[ref.STATUT_BON]}'></span>"
        f"Bon — score ≥ {ref.SEUIL_SCORE_BON:.0f}</span>"
        f"<span><span class='pastille' style='background:{ref.COULEURS_STATUT[ref.STATUT_ACCEPTABLE]}'></span>"
        f"Acceptable — de {ref.SEUIL_SCORE_ACCEPTABLE:.0f} à {ref.SEUIL_SCORE_BON:.0f}</span>"
        f"<span><span class='pastille' style='background:{ref.COULEURS_STATUT[ref.STATUT_VIGILANCE]}'></span>"
        f"À surveiller — moins de {ref.SEUIL_SCORE_ACCEPTABLE:.0f}</span>"
        f"<span><span class='pastille' style='background:{ref.COULEURS_STATUT[ref.STATUT_NA]}'></span>"
        "Non calculable — donnée manquante</span></div>",
        unsafe_allow_html=True,
    )

    st.divider()
    gauche, droite = st.columns([3, 2])
    with gauche:
        st.markdown("#### 📈 Score par axe")
        st.altair_chart(graphique_scores(diag), **PLEINE_LARGEUR)
    with droite:
        st.markdown("#### 🏗️ Structure financière")
        st.altair_chart(graphique_structure(resultat), **PLEINE_LARGEUR)

    st.markdown("#### 📋 Tableau des ratios")
    tableau = rep.tableau_ratios(diag)
    st.dataframe(
        tableau,
        hide_index=True,
        **PLEINE_LARGEUR,
        column_config={
            "Score /100": st.column_config.ProgressColumn("Score /100", min_value=0, max_value=100, format="%.0f"),
        },
    )

    if diag.lignes and any(l.valeur_n1 is not None for l in diag.lignes):
        st.markdown("#### 🔄 Évolution par rapport à N-1")
        st.altair_chart(
            graphique_evolution(
                diag,
                ["LIQ_GENERALE", "AUTONOMIE_FINANCIERE", "MARGE_NETTE", "ROE", "DELAI_CLIENTS", "DELAI_STOCK"],
            ),
            **PLEINE_LARGEUR,
        )

    with st.expander("📖 Comprendre le calcul des ratios"):
        st.markdown(
            "- **Liquidité** : ce que l'entreprise possède à court terme (stocks, créances, cash) comparé à ce "
            "qu'elle doit payer à court terme.\n"
            "- **Solvabilité** : la solidité du financement (fonds propres, dettes) et la capacité à rembourser.\n"
            "- **Rentabilité** : ce que l'entreprise gagne par rapport à ses ventes, ses fonds propres et ses actifs.\n"
            "- **Rotation** : la vitesse à laquelle circulent stocks, créances clients et dettes fournisseurs.\n\n"
            "**Fonds de roulement (FR)** = capitaux permanents − actif immobilisé. "
            "**BFR** = (stocks + créances) − dettes à court terme hors trésorerie. "
            "**Trésorerie nette** = FR − BFR = trésorerie d'actif − concours bancaires.\n\n"
            "Lorsque l'exercice N-1 est renseigné, les ratios de rotation et de rentabilité utilisent les "
            "**moyennes** des deux exercices, ce qui est plus juste."
        )


# --- Onglet 3 : diagnostic -------------------------------------------------

with onglet_diagnostic:
    if alertes:
        for alerte in alertes:
            message = f"**{alerte['titre']}** — {alerte['message']}"
            if alerte["niveau"] == "erreur":
                st.error(message)
            elif alerte["niveau"] == "avertissement":
                st.warning(message)
            else:
                st.info(message)

    st.markdown("## 💡 Diagnostic en langage simple")
    st.markdown(diag.synthese)

    colonne_gauche, colonne_droite = st.columns(2)
    with colonne_gauche:
        st.markdown("### ✅ Points forts")
        if diag.points_forts:
            for point in diag.points_forts:
                st.markdown(f"- {point}")
        else:
            st.markdown("- Aucun ratio n'atteint le niveau « bon » avec les données fournies.")
    with colonne_droite:
        st.markdown("### ⚠️ Points de vigilance")
        if diag.points_vigilance:
            for point in diag.points_vigilance:
                st.markdown(f"- {point}")
        else:
            st.markdown("- Aucun point de vigilance majeur détecté : continuez ainsi.")

    st.markdown("### 🎯 Priorités d'action")
    for i, recommandation in enumerate(diag.recommandations, start=1):
        st.markdown(f"**{i}.** {recommandation}")

    st.divider()
    st.markdown("### 🔎 Détail par thème")
    for axe, libelle_axe in ref.AXES.items():
        lignes_axe = [l for l in diag.lignes if l.axe == axe]
        scores = [l.score for l in lignes_axe if l.score is not None]
        moyenne = sum(scores) / len(scores) if scores else None
        titre = (
            f"{ref.AXES_ICONES[axe]} {libelle_axe} — "
            + (f"{moyenne:.0f}/100" if moyenne is not None else "non calculable")
        )
        with st.expander(titre, expanded=(axe in ("LIQUIDITE", "SOLVABILITE"))):
            st.caption(ref.AXES_DESCRIPTIONS[axe])
            for ligne in lignes_axe:
                if not ligne.note:
                    st.markdown(
                        f"<div class='bloc-ratio'><h4>{ligne.icone} {_html.escape(ligne.libelle)} : "
                        f"<strong>{rep._valeur_texte(ligne.valeur, ligne.unite, diag.unite_courte)}</strong></h4>"
                        f"<div class='formule'>{ligne.formule}</div>"
                        f"<p style='margin:6px 0 0'>{ligne.texte}</p></div>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(carte_ratio_html(ligne, diag.unite_courte), unsafe_allow_html=True)


# --- Onglet 4 : rapport ----------------------------------------------------

with onglet_rapport:
    st.markdown("### 📄 Rapport")
    st.caption(
        "Le rapport HTML est le format recommandé : il conserve la mise en forme, peut être envoyé par e-mail "
        "et s'imprime en PDF (Ctrl+P → « Enregistrer au format PDF »)."
    )

    date = _dt.date.today().strftime("%Y-%m-%d")
    nom_fichier = (meta["entreprise"] or "entreprise").replace(" ", "_").lower()
    colonne_1, colonne_2, colonne_3, colonne_4 = st.columns(4)
    with colonne_1:
        st.download_button(
            "📄 Rapport HTML",
            data=rep.rapport_html(diag, resultat, meta).encode("utf-8"),
            file_name=f"diagnostic_{nom_fichier}_{date}.html",
            mime="text/html",
            type="primary",
            **PLEINE_LARGEUR,
        )
    with colonne_2:
        st.download_button(
            "📝 Rapport Markdown",
            data=rep.rapport_markdown(diag, resultat, meta).encode("utf-8"),
            file_name=f"diagnostic_{nom_fichier}_{date}.md",
            mime="text/markdown",
            **PLEINE_LARGEUR,
        )
    with colonne_3:
        st.download_button(
            "📊 Ratios (CSV)",
            data=rep.tableau_ratios(diag).to_csv(index=False).encode("utf-8-sig"),
            file_name=f"ratios_{nom_fichier}_{date}.csv",
            mime="text/csv",
            **PLEINE_LARGEUR,
        )
    with colonne_4:
        st.download_button(
            "💾 Données (Excel)",
            data=iou.exporter_donnees_excel(postes_bilan, postes_bilan_n1, postes_cpc, postes_cpc_n1),
            file_name=f"donnees_{nom_fichier}_{date}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            **PLEINE_LARGEUR,
        )

    st.divider()
    apercu_markdown, apercu_html = st.tabs(["Aperçu Markdown", "Aperçu HTML (imprimable)"])
    with apercu_markdown:
        st.markdown(rep.rapport_markdown(diag, resultat, meta))
    with apercu_html:
        rapport = rep.rapport_html(diag, resultat, meta)
        if hasattr(st, "iframe"):
            st.iframe(rapport, height=760)
        else:  # versions plus anciennes de Streamlit
            composants.html(rapport, height=760, scrolling=True)
