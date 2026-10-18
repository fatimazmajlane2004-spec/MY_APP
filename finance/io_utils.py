"""
Import et export de fichiers : modèle Excel/CSV, lecture des bilans et CPC
déposés par l'utilisateur, export du rapport.

Le principe : un fichier importable doit contenir une colonne avec le *code*
des postes (recommandé, voir la feuille « Aide ») ou, à défaut, le *libellé*
du poste tel qu'il apparaît dans le modèle.
"""

from __future__ import annotations

import difflib
import io
import unicodedata
from typing import Dict, List, Optional, Tuple

import pandas as pd
from openpyxl.styles import Font

from . import referentiel as ref
from .ratios import nombre

ETAT_BILAN = "Bilan"
ETAT_CPC = "CPC"

COLONNES = ["Code", "Poste", "Exercice N", "Exercice N-1"]


# ---------------------------------------------------------------------------
# Normalisation et rapprochement des libellés
# ---------------------------------------------------------------------------

def _normaliser(texte: object) -> str:
    """Minuscules, sans accents, sans ponctuation ni espaces superflus."""
    if texte is None:
        return ""
    t = str(texte)
    t = unicodedata.normalize("NFKD", t)
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = t.lower()
    for c in "()[]{}'’\".,;:/-_+*":
        t = t.replace(c, " ")
    return " ".join(t.split())


def _table_libelles(postes) -> Dict[str, str]:
    return {_normaliser(p.libelle): p.code for p in postes}


def _deviner_code(texte: object, postes) -> Optional[str]:
    """Retrouve le code d'un poste à partir de son libellé (exact puis approché)."""
    cle = _normaliser(texte)
    if not cle:
        return None
    table = _table_libelles(postes)
    if cle in table:
        return table[cle]
    # correspondance approchée
    proches = difflib.get_close_matches(cle, list(table), n=1, cutoff=0.72)
    if proches:
        return table[proches[0]]
    # recherche par mots-clés significatifs
    for libelle, code in table.items():
        mots = [m for m in libelle.split() if len(m) > 4]
        if mots and sum(1 for m in mots if m in cle) >= max(1, len(mots) // 2):
            return code
    return None


# ---------------------------------------------------------------------------
# Modèles vierges
# ---------------------------------------------------------------------------

def modele_dataframe(postes, avec_n1: bool = True) -> pd.DataFrame:
    """DataFrame utilisé par l'éditeur Streamlit et par le modèle téléchargeable."""
    lignes = [
        {"Code": p.code, "Poste": p.libelle, "Exercice N": 0.0, "Exercice N-1": 0.0 if avec_n1 else None}
        for p in postes
    ]
    return pd.DataFrame(lignes, columns=COLONNES if avec_n1 else COLONNES[:3])


def modele_editeur(postes) -> pd.DataFrame:
    """Tableau de saisie : une ligne par poste, colonne « Rubrique » pour la lisibilité."""
    return pd.DataFrame(
        [
            {
                "Code": p.code,
                "Rubrique": ref.GROUPES.get(p.groupe, p.groupe),
                "Poste": p.libelle,
                "Exercice N": None,
                "Exercice N-1": None,
            }
            for p in postes
        ]
    )


def appliquer_import(
    df: pd.DataFrame,
    postes: Dict[str, float],
    colonne: str,
) -> pd.DataFrame:
    """Reporte des montants importés dans le tableau de saisie, en conservant l'ordre officiel."""
    if not postes or colonne not in df.columns:
        return df
    correspondance = {str(c).strip().upper(): i for i, c in enumerate(df["Code"])}
    df = df.copy()
    for code, valeur in postes.items():
        position = correspondance.get(str(code).strip().upper())
        if position is not None:
            df.at[position, colonne] = float(valeur)
    return df


NOTICE = [
    ["Comment utiliser ce modèle"],
    [""],
    ["1. Ne modifiez pas la colonne « Code » : elle sert à reconnaître les postes à l'import."],
    ["2. Saisissez les montants de l'exercice N (et, si vous les avez, ceux de l'exercice N-1)."],
    ["3. Tous les montants doivent être exprimés dans la même unité (ex. en euros ou en milliers d'euros)."],
    ["4. Un poste sans montant peut être laissé vide ou à 0."],
    ["5. Les amortissements ne se déduisent pas des immobilisations : saisissez-les en net et indiquez aussi"],
    ["   les dotations aux amortissements dans le CPC (nécessaire pour la capacité d'autofinancement)."],
    ["6. Le total de l'actif doit être égal au total du passif (sinon un contrôle de cohérence vous alertera)."],
    [""],
    ["Feuilles du classeur :"],
    ["  • Bilan : postes d'actif et de passif"],
    ["  • CPC   : chiffre d'affaires, charges, produits financiers, impôt"],
    ["  • Aide  : liste des codes reconnus par l'application"],
]


def _feuille_aide() -> pd.DataFrame:
    lignes = []
    for p in ref.POSTES_BILAN:
        lignes.append(
            [ETAT_BILAN, p.code, p.libelle, ref.GROUPES.get(p.groupe, p.groupe), p.aide]
        )
    for p in ref.POSTES_CPC:
        lignes.append(
            [ETAT_CPC, p.code, p.libelle, ref.GROUPES.get(p.groupe, p.groupe), p.aide]
        )
    return pd.DataFrame(lignes, columns=["État", "Code", "Libellé officiel", "Rubrique", "Explication"])


def exporter_modele_excel() -> bytes:
    """Classeur Excel vierge à remplir par l'utilisateur."""
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        modele_dataframe(ref.POSTES_BILAN).to_excel(writer, sheet_name="Bilan", index=False)
        modele_dataframe(ref.POSTES_CPC).to_excel(writer, sheet_name="CPC", index=False)
        _feuille_aide().to_excel(writer, sheet_name="Aide", index=False)
        pd.DataFrame(NOTICE).to_excel(writer, sheet_name="Notice", index=False, header=False)

        # Mise en forme : largeurs de colonnes et en-têtes
        for feuille, largeurs in (("Bilan", [22, 58, 16, 16]), ("CPC", [22, 58, 16, 16]), ("Aide", [10, 22, 58, 34, 60])):
            ws = writer.sheets[feuille]
            for i, largeur in enumerate(largeurs, start=1):
                ws.column_dimensions[chr(64 + i)].width = largeur
            for cellule in ws[1]:
                cellule.font = Font(bold=True)
    return buffer.getvalue()


def exporter_modele_csv() -> Dict[str, bytes]:
    """Modèles CSV (un fichier par état) pour les utilisateurs sans Excel."""
    return {
        f"modele_{ETAT_BILAN.lower()}.csv": modele_dataframe(ref.POSTES_BILAN, avec_n1=False)
        .to_csv(index=False)
        .encode("utf-8-sig"),
        f"modele_{ETAT_CPC.lower()}.csv": modele_dataframe(ref.POSTES_CPC, avec_n1=False)
        .to_csv(index=False)
        .encode("utf-8-sig"),
    }


def exporter_donnees_excel(
    bilan_n: Dict[str, float],
    bilan_n1: Dict[str, float],
    cpc_n: Dict[str, float],
    cpc_n1: Dict[str, float],
) -> bytes:
    """Exporte les données saisies dans un classeur au format du modèle (réimportable)."""
    df_bilan = appliquer_import(modele_dataframe(ref.POSTES_BILAN), bilan_n, "Exercice N")
    if bilan_n1:
        df_bilan = appliquer_import(df_bilan, bilan_n1, "Exercice N-1")
    df_cpc = appliquer_import(modele_dataframe(ref.POSTES_CPC), cpc_n, "Exercice N")
    if cpc_n1:
        df_cpc = appliquer_import(df_cpc, cpc_n1, "Exercice N-1")

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df_bilan.to_excel(writer, sheet_name="Bilan", index=False)
        df_cpc.to_excel(writer, sheet_name="CPC", index=False)
        _feuille_aide().to_excel(writer, sheet_name="Aide", index=False)
        for feuille, largeurs in (("Bilan", [22, 58, 16, 16]), ("CPC", [22, 58, 16, 16]), ("Aide", [10, 22, 58, 34, 60])):
            ws = writer.sheets[feuille]
            for i, largeur in enumerate(largeurs, start=1):
                ws.column_dimensions[chr(64 + i)].width = largeur
    return buffer.getvalue()


def exemple_dataframe():
    """Jeu de données d'exemple (PME industrielle en difficulté modérée)."""
    bilan = modele_dataframe(ref.POSTES_BILAN).set_index("Code")
    cpc = modele_dataframe(ref.POSTES_CPC).set_index("Code")

    valeurs_bilan_n = {
        "IMMO_INCORP_CORP": 780_000,
        "IMMO_FINANCIERES": 20_000,
        "STOCKS": 520_000,
        "CLIENTS": 690_000,
        "AUTRES_CREANCES": 60_000,
        "VMP": 0,
        "DISPONIBILITES": 45_000,
        "CAPITAL": 200_000,
        "RESERVES": 180_000,
        "RESULTAT": 62_000,
        "EMPRUNTS": 640_000,
        "FOURNISSEURS": 540_000,
        "DETTES_SOCIALES": 150_000,
        "DETTES_FISCALES": 85_000,
        "AUTRES_DETTES_CT": 30_000,
        "CONCOURS_BANCAIRES": 228_000,
    }
    valeurs_bilan_n1 = {
        "IMMO_INCORP_CORP": 850_000,
        "IMMO_FINANCIERES": 20_000,
        "STOCKS": 470_000,
        "CLIENTS": 640_000,
        "AUTRES_CREANCES": 55_000,
        "VMP": 0,
        "DISPONIBILITES": 70_000,
        "CAPITAL": 200_000,
        "RESERVES": 148_000,
        "RESULTAT": 116_000,
        "EMPRUNTS": 710_000,
        "FOURNISSEURS": 500_000,
        "DETTES_SOCIALES": 140_000,
        "DETTES_FISCALES": 80_000,
        "AUTRES_DETTES_CT": 25_000,
        "CONCOURS_BANCAIRES": 186_000,
    }
    valeurs_cpc_n = {
        "CA": 3_150_000,
        "AUTRES_PRODUITS": 30_000,
        "ACHATS": 1_980_000,
        "CHARGES_EXTERNES": 430_000,
        "PERSONNEL": 520_000,
        "IMPOTS_TAXES": 45_000,
        "DOTATIONS": 95_000,
        "PRODUITS_FIN": 5_000,
        "CHARGES_FIN": 45_000,
        "IMPOT_RESULTAT": 8_000,
    }
    valeurs_cpc_n1 = {
        "CA": 3_300_000,
        "AUTRES_PRODUITS": 25_000,
        "ACHATS": 2_050_000,
        "CHARGES_EXTERNES": 430_000,
        "PERSONNEL": 530_000,
        "IMPOTS_TAXES": 45_000,
        "DOTATIONS": 88_000,
        "PRODUITS_FIN": 4_000,
        "CHARGES_FIN": 50_000,
        "IMPOT_RESULTAT": 20_000,
    }

    for table, valeurs, colonne in (
        (bilan, valeurs_bilan_n, "Exercice N"),
        (bilan, valeurs_bilan_n1, "Exercice N-1"),
        (cpc, valeurs_cpc_n, "Exercice N"),
        (cpc, valeurs_cpc_n1, "Exercice N-1"),
    ):
        for code, valeur in valeurs.items():
            table.loc[code, colonne] = float(valeur)

    return bilan.reset_index(), cpc.reset_index()


# ---------------------------------------------------------------------------
# Lecture des fichiers déposés par l'utilisateur
# ---------------------------------------------------------------------------

def _lire_brut(nom_fichier: str, contenu: bytes) -> List[Tuple[str, pd.DataFrame]]:
    """Renvoie la liste (nom_de_feuille, DataFrame) d'un fichier Excel ou CSV."""
    nom = nom_fichier.lower()
    if nom.endswith((".xlsx", ".xlsm", ".xls")):
        classeur = pd.read_excel(io.BytesIO(contenu), sheet_name=None, dtype=object)
        return [(feuille, df) for feuille, df in classeur.items()]

    # CSV : on tente plusieurs encodages et séparateurs
    for encodage in ("utf-8-sig", "utf-8", "latin-1"):
        for separateur in (None, ";", ",", "\t"):
            try:
                df = pd.read_csv(
                    io.BytesIO(contenu), encoding=encodage, sep=separateur, dtype=object, engine="python"
                )
            except Exception:
                continue
            if df.shape[1] >= 2:
                return [(nom_fichier, df)]
    raise ValueError(
        f"Impossible de lire « {nom_fichier} ». Utilisez un fichier Excel (.xlsx) ou CSV exporté du modèle."
    )


def _deviner_colonnes_valeurs(df: pd.DataFrame) -> Tuple[Optional[str], Optional[str]]:
    """Repère les colonnes « exercice N » et « exercice N-1 »."""
    colonnes = list(df.columns)
    numeriques = [
        c
        for c in colonnes
        if df[c].apply(lambda v: isinstance(v, (int, float)) or _est_nombre(v)).sum() >= 2
    ]
    if not numeriques:
        return None, None
    # Colonnes nommées : on privilégie les libellés explicites
    col_n = col_n1 = None
    for c in colonnes:
        cle = _normaliser(c)
        if col_n is None and ("n 1" in cle or "n-1" in cle or "precedent" in cle or "anterieur" in cle):
            col_n1 = c
        elif col_n is None and (cle in ("n", "exercice n", "annee n", "montant n") or "exercice n" == cle):
            col_n = c
    if col_n is None:
        col_n = numeriques[0]
    if col_n1 is None:
        restantes = [c for c in numeriques if c != col_n]
        col_n1 = restantes[0] if restantes else None
    return col_n, col_n1


def _est_nombre(valeur) -> bool:
    if valeur is None or isinstance(valeur, bool):
        return False
    if isinstance(valeur, (int, float)):
        return True
    texte = str(valeur).replace(" ", "").replace("\u00a0", "").replace(",", ".").strip()
    if not texte:
        return False
    try:
        float(texte)
        return True
    except ValueError:
        return False


def df_vers_postes(df: pd.DataFrame) -> Tuple[Dict[str, float], Dict[str, float], List[str]]:
    """Convertit un tableau importé en deux dictionnaires {code: montant}.

    Renvoie (postes_N, postes_N1, avertissements).
    """
    colonnes = list(df.columns)
    colonne_code = next((c for c in colonnes if _normaliser(c) in ("code", "code poste", "ref", "reference")), None)
    colonne_libelle = next(
        (c for c in colonnes if _normaliser(c) in ("poste", "libelle", "designation", "intitule")),
        None,
    )
    if colonne_libelle is None:
        # à défaut, la première colonne textuelle
        for c in colonnes:
            if not df[c].apply(_est_nombre).all():
                colonne_libelle = c
                break

    col_n, col_n1 = _deviner_colonnes_valeurs(df)
    if col_n is None:
        raise ValueError("Aucune colonne de montants n'a été trouvée dans le fichier importé.")

    # Décide s'il s'agit du bilan ou du CPC
    codes_bilan = set(ref.POSTES_BILAN_PAR_CODE)
    codes_cpc = set(ref.POSTES_CPC_PAR_CODE)
    tous = list(ref.POSTES_BILAN) + list(ref.POSTES_CPC)
    postes_retenus: List = []
    scores = {"bilan": 0, "cpc": 0}

    lignes_codees: List[Tuple[Optional[str], Optional[str], Optional[float], Optional[float]]] = []
    for _, ligne in df.iterrows():
        brut_code = str(ligne.get(colonne_code)).strip().upper().replace(" ", "_") if colonne_code else None
        brut_libelle = ligne.get(colonne_libelle) if colonne_libelle else None
        code = None
        if brut_code and brut_code in codes_bilan:
            code = brut_code
            scores["bilan"] += 1
        elif brut_code and brut_code in codes_cpc:
            code = brut_code
            scores["cpc"] += 1
        else:
            devine = _deviner_code(brut_libelle, tous)
            if devine and devine in codes_bilan:
                code = devine
                scores["bilan"] += 1
            elif devine and devine in codes_cpc:
                code = devine
                scores["cpc"] += 1
        lignes_codees.append(
            (
                code,
                str(brut_libelle) if brut_libelle is not None else "",
                nombre(ligne.get(col_n)) if col_n else 0.0,
                nombre(ligne.get(col_n1)) if col_n1 and col_n1 in df.columns else None,
            )
        )

    if scores["bilan"] >= scores["cpc"]:
        postes_retenus = ref.POSTES_BILAN
        vocabulaire = "bilan"
    else:
        postes_retenus = ref.POSTES_CPC
        vocabulaire = "compte de produits et charges"

    valides = {p.code for p in postes_retenus}
    postes_n: Dict[str, float] = {}
    postes_n1: Dict[str, float] = {}
    avertissements: List[str] = []

    for code, libelle, v_n, v_n1 in lignes_codees:
        if code is None:
            if (v_n not in (None, 0.0)) or (v_n1 not in (None, 0.0)):
                avertissements.append(
                    f"Ligne ignorée (poste non reconnu dans le {vocabulaire}) : « {libelle} » — vérifiez la colonne « Code »."
                )
            continue
        if code not in valides:
            continue
        postes_n[code] = nombre(v_n)
        if v_n1 is not None:
            postes_n1[code] = nombre(v_n1)

    if not postes_n:
        raise ValueError(
            f"Aucun poste reconnu dans ce fichier (interprété comme un {vocabulaire}). "
            "Utilisez le modèle fourni ou vérifiez la colonne « Code »."
        )
    return postes_n, postes_n1, avertissements


def importer_fichiers(fichiers: List[Tuple[str, bytes]]) -> Dict[str, object]:
    """Importe un ou plusieurs fichiers et renvoie les postes du bilan et du CPC.

    ``fichiers`` : liste de couples (nom, contenu binaire).
    Renvoie un dictionnaire avec les clés bilan / bilan_n1 / cpc / cpc_n1 / messages.
    """
    resultat: Dict[str, object] = {
        "bilan": {},
        "bilan_n1": {},
        "cpc": {},
        "cpc_n1": {},
        "messages": [],
    }
    for nom_fichier, contenu in fichiers:
        for nom_feuille, df in _lire_brut(nom_fichier, contenu):
            if df is None or df.empty:
                continue
            cle_feuille = _normaliser(nom_feuille)
            if any(mot in cle_feuille for mot in ("aide", "notice", "parametre")):
                continue
            try:
                postes_n, postes_n1, avertissements = df_vers_postes(df)
            except ValueError as exc:
                resultat["messages"].append(f"⚠️ {nom_fichier} / {nom_feuille} : {exc}")  # type: ignore[union-attr]
                continue

            est_bilan = len(set(postes_n) & set(ref.POSTES_BILAN_PAR_CODE)) >= len(
                set(postes_n) & set(ref.POSTES_CPC_PAR_CODE)
            )
            etiquette = "bilan" if est_bilan else "cpc"
            resultat[etiquette].update(postes_n)  # type: ignore[union-attr]
            if postes_n1:
                resultat[f"{etiquette}_n1"].update(postes_n1)  # type: ignore[union-attr]
            resultat["messages"].append(  # type: ignore[union-attr]
                f"✅ {nom_fichier} / {nom_feuille} : {len(postes_n)} postes du {etiquette.upper()} importés"
                + (f" (dont {len(postes_n1)} avec l'exercice précédent)" if postes_n1 else "")
            )
            for message in avertissements:
                resultat["messages"].append(f"⚠️ {message}")  # type: ignore[union-attr]
    return resultat


def postes_depuis_editeur(df: pd.DataFrame, postes) -> Tuple[Dict[str, float], Dict[str, float]]:
    """Extrait les montants d'un tableau édité dans Streamlit (colonnes Code / Exercice N / N-1)."""
    valides = {p.code for p in postes}
    colonne_n = next((c for c in df.columns if _normaliser(c) in ("exercice n", "n", "montant n")), None)
    colonne_n1 = next((c for c in df.columns if _normaliser(c) in ("exercice n 1", "n 1", "montant n 1")), None)
    postes_n: Dict[str, float] = {}
    postes_n1: Dict[str, float] = {}
    if colonne_n is None:
        return postes_n, postes_n1
    for _, ligne in df.iterrows():
        code = str(ligne.get("Code", "")).strip().upper()
        if code not in valides:
            continue
        postes_n[code] = nombre(ligne.get(colonne_n))
        if colonne_n1 and colonne_n1 in df.columns and not pd.isna(ligne.get(colonne_n1)):
            postes_n1[code] = nombre(ligne.get(colonne_n1))
    return postes_n, postes_n1
