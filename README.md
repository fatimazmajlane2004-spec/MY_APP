# 📊 Diagnostic financier automatique

Application **Streamlit** qui importe un **bilan** et un **compte de produits et charges (CPC)**,
calcule automatiquement les ratios de **liquidité**, **solvabilité**, **rentabilité** et **rotation**,
puis rédige un **diagnostic en langage simple** : points forts, points de vigilance et priorités d'action.

---

## 1. Installation

```powershell
cd C:\Users\User\Desktop\MY_APP
python -m pip install -r requirements.txt
```

## 2. Lancement

**Méthode la plus simple** : double-cliquez sur **`lancer_app.bat`**.
Le serveur démarre et le navigateur s'ouvre sur `http://localhost:8501`.

**En ligne de commande :**

```powershell
cd C:\Users\User\Desktop\MY_APP
streamlit run app.py
```

> ⚠️ **L'adresse est `http://localhost:8501`** — ce n'est pas `https://`.
> Streamlit sert une page en HTTP simple : taper `https://` provoque une erreur de
> connexion dans le navigateur.
>
> Si le message **« Port 8501 is not available »** apparaît, un autre programme occupe
> déjà le port. Utilisez un autre port : `streamlit run app.py --server.port 8502`
> (puis ouvrez `http://localhost:8502`).

Pour découvrir l'outil immédiatement, cliquez sur **🎲 Charger un exemple** dans la barre latérale.

## 3. Mode d'emploi

### a) Importer les états financiers

| Méthode | Comment faire |
|---|---|
| **Excel** (recommandé) | Barre latérale → *Modèles de fichiers* → téléchargez le modèle, remplissez les feuilles `Bilan` et `CPC`, puis déposez le fichier dans l'onglet **1️⃣ Données**. |
| **CSV** | Un fichier par état, avec une colonne `Code` (ou `Poste`) et une colonne de montants. |
| **Saisie manuelle** | Remplissez directement les deux tableaux de l'onglet **1️⃣ Données**. |

Les deux exercices (**N** et **N-1**) peuvent être saisis : l'application calcule alors des moyennes
(plus justes pour les ratios de rotation) et affiche les évolutions.

### b) Lire les résultats

| Onglet | Contenu |
|---|---|
| **1️⃣ Données** | Saisie, import, contrôles de cohérence (bilan équilibré, résultat CPC = résultat du bilan). |
| **2️⃣ Ratios** | Note globale, score par axe, graphiques, tableau complet des ratios, évolution N/N-1. |
| **3️⃣ Diagnostic** | Synthèse rédigée, points forts, points de vigilance, priorités d'action, détail expliqué ratio par ratio. |
| **4️⃣ Rapport** | Export **HTML** (imprimable en PDF), **Markdown**, **CSV** des ratios et **Excel** des données. |

Les notes suivent un code couleur constant : 🟢 **Bon** (score ≥ 85), 🟠 **Acceptable** (de 55 à 85),
🔴 **À surveiller** (moins de 55) et ⚪ **non calculable** (donnée manquante). Ce code est repris dans
l'anneau de score, les cartes par axe, les tableaux et le rapport exporté.

### c) Adapter l'analyse

Dans la barre latérale : nom de l'entreprise, exercice, **secteur d'activité** (les seuils des ratios
s'ajustent), **unité des montants** et **taux de TVA** (pour le délai fournisseurs).

---

## 4. Les ratios calculés

### 💧 Liquidité — *payer les dettes à court terme*
| Ratio | Formule | Repère |
|---|---|---|
| Liquidité générale | Actif circulant / Passif circulant | > 1,5 |
| Liquidité réduite | (Créances + Trésorerie) / Passif circulant | > 1,0 |
| Liquidité immédiate | Trésorerie / Passif circulant | > 0,3 |
| Trésorerie nette | (FR − BFR) / CA | > 3 % |
| Fonds de roulement, BFR | *indicateurs* | FR ≥ 0, BFR financé |

### 🏦 Solvabilité — *solidité de la structure*
| Ratio | Formule | Repère |
|---|---|---|
| Autonomie financière | Capitaux propres / Total du passif | > 30 % |
| Solvabilité générale | Capitaux propres / Total des dettes | > 1 |
| Levier d'endettement | Dettes financières / Capitaux propres | < 0,5 |
| Capacité de remboursement | Dettes financières / CAF | < 3 ans |

### 📈 Rentabilité — *gagner de l'argent*
| Ratio | Formule | Repère |
|---|---|---|
| Marge nette | Résultat net / CA | > 5 % |
| Marge d'exploitation | Résultat d'exploitation / CA | > 6 % |
| ROE | Résultat net / Capitaux propres | > 12 % |
| ROA | Résultat d'exploitation / Total actif | > 7 % |
| Rentabilité économique | Rés. exploitation / (Immobilisations + BFR) | > 10 % |
| Taux de valeur ajoutée | (CA + autres produits − achats − charges externes) / CA | > 25 % |

### 🔄 Rotation — *vitesse de circulation*
| Ratio | Formule | Repère |
|---|---|---|
| Durée de stockage | 360 × Stock moyen / Achats | < 30 j |
| Délai clients | 360 × Créances clients TTC / CA TTC | < 30 j |
| Délai fournisseurs | 360 × Dettes fourn. TTC / (Achats + charges externes) TTC | 30 à 90 j |
| Poids du BFR | 360 × BFR / CA | < 45 j |
| Rotation de l'actif | CA / Total actif | > 1,5 |
| Rotation des immobilisations | CA / Immobilisations nettes | > 3 |

> Les repères sont ceux d'une entreprise « moyenne ». Ils sont **ajustés automatiquement** au secteur
> choisi (commerce, industrie, services) et restent à interpréter selon l'activité réelle.

**Note globale** : moyenne pondérée des ratios notés (liquidité 30 %, solvabilité 25 %,
rentabilité 30 %, rotation 15 %). Chaque ratio est noté de 0 à 100 ; un ratio est « Bon » à partir de
85/100 et « À surveiller » en dessous de 55/100 — les seuils affichés et les notes sont donc toujours
cohérents.

---

## 5. Structure du projet

```
MY_APP/
├── app.py                       # application Streamlit (interface)
├── lancer_app.bat               # démarrage en double-clic (Windows)
├── .streamlit/
│   └── config.toml              # thème (couleurs, police) utilisé par Streamlit
├── finance/                     # moteur d'analyse, indépendant de Streamlit
│   ├── referentiel.py           # postes comptables, définition des ratios, seuils par secteur
│   ├── ratios.py                # agrégation des postes et calcul des ratios
│   ├── diagnostic.py            # notation, textes d'interprétation, recommandations
│   ├── reporting.py             # tableaux, rapport Markdown, rapport HTML
│   └── io_utils.py              # modèles de fichiers, import Excel/CSV
├── data/                        # exemples générés
│   ├── modele_bilan_cpc.xlsx    # modèle vierge à remplir
│   ├── exemple_bilan_cpc.xlsx   # exemple rempli (2 exercices)
│   ├── exemple_rapport.html     # exemple de rapport de diagnostic
│   └── exemple_ratios.csv
├── scripts/
│   ├── creer_fichiers.py        # régénère les fichiers du dossier data/
│   └── verifier_rendu.py        # affiche le contenu réellement rendu (contrôle qualité)
├── tests/                       # tests unitaires + tests d'interface
└── requirements.txt
```

## 6. Tests

```powershell
python -m pip install pytest
python -m pytest -q
```

30 tests couvrent les agrégats comptables, chaque famille de ratios, les cas limites
(divisions par zéro, CAF négative, bilan déséquilibré), la cohérence des notes et des seuils,
l'import/export de fichiers, la génération des rapports et le fonctionnement réel de
l'interface Streamlit (via `streamlit.testing`, le framework officiel de test).

## 7. Compatibilité

Développé et testé avec **Streamlit 1.65 / Python 3.10**. L'application détecte automatiquement
la version de Streamlit installée (`width="stretch"` sur les versions récentes,
`use_container_width=True` sur les anciennes) et reste donc utilisable avec `streamlit>=1.32`.

## 8. Ajouter ou modifier un ratio

Tout se passe dans `finance/referentiel.py` : ajoutez une entrée à la liste `RATIOS`
(libellé, formule, unité, sens, seuils, phrases d'explication), puis calculez sa valeur dans
`finance/ratios.py`. L'interface, le diagnostic et les rapports le prennent en compte automatiquement.

---

## 9. Déploiement sur Streamlit Community Cloud

L'application est prête pour un hébergement gratuit (aucune donnée secrète n'est nécessaire) :

1. Poussez le projet sur GitHub (dépôt `MY_APP`, branche `main`).
2. Ouvrez <https://share.streamlit.io> → **Create app** → **Deploy a public app from GitHub**.
3. Renseignez :

   | Champ | Valeur |
   |---|---|
   | Repository | `votre-compte/MY_APP` |
   | Branch | `main` |
   | Main file path | `app.py` |
   | App URL | au choix, par exemple `diagnostic-financier` |

4. Cliquez sur **Deploy!**. Le premier démarrage prend 2 à 3 minutes : Streamlit installe
   `requirements.txt` (Streamlit, pandas, openpyxl, altair, numpy).

Bon à savoir :

- Le thème (`.streamlit/config.toml`) est repris automatiquement au déploiement.
- L'application ne conserve aucune donnée : chaque visiteur repart d'une page vide, ses chiffres
  restent dans sa session. Elle peut donc être partagée librement.
- Le dossier `data/` n'est pas utile au fonctionnement : il ne contient que des exemples.
- Après un `git push` sur la branche `main`, Streamlit redéploie automatiquement la nouvelle version.

---

## ⚠️ Avertissement

Cet outil fournit une **analyse automatique d'aide à la décision**, à partir des données saisies par
l'utilisateur. Il ne constitue ni un avis d'expert-comptable, ni un audit, ni un conseil en
investissement. Les repères sectoriels sont des moyennes de marché.
