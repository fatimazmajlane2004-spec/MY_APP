"""Mise en forme du diagnostic : tableaux, rapport Markdown et rapport HTML imprimable."""

from __future__ import annotations

import datetime as _dt
import html
from typing import Dict, List, Optional

import pandas as pd

from . import referentiel as ref
from .diagnostic import Diagnostic, _fmt, couleur_score, note_affichee
from .ratios import ResultatRatios


# ---------------------------------------------------------------------------
# Tableaux
# ---------------------------------------------------------------------------

def tableau_ratios(diag: Diagnostic) -> pd.DataFrame:
    """Tableau synthétique des ratios, prêt pour l'affichage ou l'export CSV."""
    lignes: List[Dict[str, object]] = []
    for l in diag.lignes:
        ligne = {
            "Axe": f"{ref.AXES_ICONES.get(l.axe, '')} {ref.AXES.get(l.axe, l.axe)}".strip(),
            "Ratio": f"{l.icone} {l.libelle}",
            "Valeur": _valeur_texte(l.valeur, l.unite, diag.unite_courte),
            "Statut": f"{l.pastille} {l.statut}",
            "Score /100": note_affichee(l.score),
            "Formule": l.formule,
        }
        if l.valeur_n1 is not None:
            ligne["Exercice N-1"] = _valeur_texte(l.valeur_n1, l.unite, diag.unite_courte)
            ligne["Évolution"] = l.evolution
        lignes.append(ligne)
    return pd.DataFrame(lignes)


def _valeur_texte(valeur: Optional[float], unite: str, symbole: str = "") -> str:
    if valeur is None:
        return "n.d."
    if unite == "montant":
        return f"{valeur:,.0f}".replace(",", " ") + (f" {symbole}" if symbole else "")
    return _fmt(valeur, unite)


def tableau_scores(diag: Diagnostic) -> pd.DataFrame:
    lignes = []
    for axe, libelle in ref.AXES.items():
        score = diag.scores_axes.get(axe)
        lignes.append(
            {
                "Axe": f"{ref.AXES_ICONES.get(axe, '')} {libelle}".strip(),
                "Score /100": note_affichee(score),
                "Poids": f"{ref.POIDS_AXES.get(axe, 0):.0%}",
            }
        )
    return pd.DataFrame(lignes)


# ---------------------------------------------------------------------------
# Rapport Markdown
# ---------------------------------------------------------------------------

def rapport_markdown(diag: Diagnostic, resultat: ResultatRatios, meta: Dict[str, str]) -> str:
    date = _dt.date.today().strftime("%d/%m/%Y")
    lignes: List[str] = []
    a = lignes.append

    a(f"# 📊 Diagnostic financier — {meta.get('entreprise', 'Entreprise')}")
    a("")
    a(f"*Exercice : {meta.get('exercice', 'N')} — Secteur : {meta.get('secteur', 'Général')} — "
      f"Unité : {meta.get('unite', 'unités')} — Rapport généré le {date}*")
    a("")
    a("## 📌 1. Synthèse")
    a("")
    note = f"{note_affichee(diag.score_global)}/100" if diag.score_global is not None else "non calculable"
    icone_appreciation = ref.ICONES_APPRECIATION.get(diag.appreciation, "")
    a(f"**Note globale : {note} — situation {diag.appreciation} {icone_appreciation}**")
    a("")
    a(diag.synthese)
    a("")
    a("| Axe | Score /100 | Poids |")
    a("|---|---|---|")
    for axe, libelle in ref.AXES.items():
        score = diag.scores_axes.get(axe)
        a(f"| {libelle} | {note_affichee(score)} | {ref.POIDS_AXES.get(axe, 0):.0%} |" if score is not None
          else f"| {libelle} | n.d. | {ref.POIDS_AXES.get(axe, 0):.0%} |")
    a("")

    a("## ✅ 2. Points forts")
    a("")
    if diag.points_forts:
        for p in diag.points_forts:
            a(f"- {p}")
    else:
        a("- Aucun ratio n'atteint le niveau « bon » avec les données fournies.")
    a("")

    a("## ⚠️ 3. Points de vigilance")
    a("")
    if diag.points_vigilance:
        for p in diag.points_vigilance:
            a(f"- {p}")
    else:
        a("- Aucun point de vigilance majeur détecté.")
    a("")

    a("## 🎯 4. Priorités d'action")
    a("")
    for i, r in enumerate(diag.recommandations, start=1):
        a(f"{i}. {r}")
    a("")

    a("## 📊 5. Détail des ratios")
    a("")
    for axe, libelle_axe in ref.AXES.items():
        lignes_axe = [l for l in diag.lignes if l.axe == axe]
        if not lignes_axe:
            continue
        a(f"### {ref.AXES_ICONES.get(axe, '')} {libelle_axe}")
        a("")
        a(f"*{ref.AXES_DESCRIPTIONS.get(axe, '')}*")
        a("")
        for l in lignes_axe:
            a(f"**{l.icone} {l.libelle} — {_valeur_texte(l.valeur, l.unite, diag.unite_courte)} ({l.pastille} {l.statut})**")
            a("")
            a(f"- Formule : {l.formule}")
            if l.valeur_n1 is not None:
                a(f"- Exercice précédent : {_valeur_texte(l.valeur_n1, l.unite, diag.unite_courte)} (évolution : {l.evolution})")
            a(f"- {l.texte}")
            if l.conseil and l.statut == ref.STATUT_VIGILANCE:
                a(f"- *Piste d'amélioration :* {l.conseil}")
            a("")

    if diag.alertes:
        a("## 🔍 6. Contrôles de cohérence")
        a("")
        for alerte in diag.alertes:
            a(f"- **{alerte.get('titre')}** — {alerte.get('message')}")
        a("")

    a("---")
    a("")
    a("*Document généré automatiquement à partir des états financiers saisis. "
      "Il ne constitue pas un avis d'expert-comptable ni une opinion d'audit.*")
    return "\n".join(lignes)


# ---------------------------------------------------------------------------
# Rapport HTML imprimable
# ---------------------------------------------------------------------------

CSS = """
:root { color-scheme: light; }
* { box-sizing: border-box; }
body { font-family: "Segoe UI", Roboto, Helvetica, Arial, sans-serif; margin: 0; padding: 32px;
       color: #1f2933; background: #f7f9fc; line-height: 1.55; }
.page { max-width: 940px; margin: 0 auto; background: #fff; padding: 40px 48px;
        border-radius: 10px; box-shadow: 0 2px 14px rgba(15,23,42,.08); }
h1 { font-size: 27px; margin: 0 0 4px; }
h2 { font-size: 19px; margin-top: 34px; padding-bottom: 6px; border-bottom: 2px solid #e4e9f2;
     border-left: 6px solid #2563eb; padding-left: 12px; }
h3 { font-size: 16px; margin-top: 24px; color: #334155; }
.meta { color: #64748b; font-size: 13px; margin-bottom: 24px; }
.score-carte { display: flex; gap: 26px; align-items: center; background: #f1f5fb; border-radius: 12px;
               padding: 20px 24px; margin: 18px 0; }
.score-anneau { width: 118px; height: 118px; border-radius: 50%; padding: 11px; flex: 0 0 auto; }
.score-anneau-centre { width: 100%; height: 100%; border-radius: 50%; background: #fff;
                       display: flex; flex-direction: column; align-items: center; justify-content: center; }
.score-anneau-centre span { font-size: 30px; font-weight: 800; line-height: 1; }
.score-anneau-centre small { font-size: 11px; color: #94a3b8; }
.score-legende { font-size: 14px; color: #475569; }
table { width: 100%; border-collapse: collapse; margin: 14px 0; font-size: 14px; }
th, td { text-align: left; padding: 8px 10px; border-bottom: 1px solid #e6eaf1; vertical-align: top; }
th { background: #f8fafc; font-weight: 600; color: #334155; }
.num { text-align: right; white-space: nowrap; }
.badge { display: inline-block; padding: 2px 9px; border-radius: 999px; color: #fff; font-size: 12px;
         font-weight: 600; white-space: nowrap; }
.ratio { border-left: 4px solid #cbd5e1; padding: 12px 16px; margin: 14px 0; background: #fbfcfe; border-radius: 0 8px 8px 0; }
.ratio h4 { margin: 0 0 4px; font-size: 15px; }
.formule { font-family: Consolas, "Courier New", monospace; font-size: 12px; color: #64748b; }
ul { padding-left: 20px; }
li { margin-bottom: 6px; }
footer { margin-top: 36px; font-size: 12px; color: #94a3b8; border-top: 1px solid #e6eaf1; padding-top: 12px; }
.barre { height: 8px; background: #e6eaf1; border-radius: 99px; overflow: hidden; min-width: 120px; }
.barre span { display: block; height: 100%; }
@media print { body { background: #fff; padding: 0; } .page { box-shadow: none; padding: 0; } }
"""


def _badge(statut: str) -> str:
    couleur = ref.COULEURS_STATUT.get(statut, "#9e9e9e")
    return f'<span class="badge" style="background:{couleur}">{html.escape(statut)}</span>'


def _barre(score: Optional[float]) -> str:
    if score is None:
        return ""
    return f'<div class="barre"><span style="width:{max(2, min(100, score)):.0f}%;background:{couleur_score(score)}"></span></div>'


def rapport_html(diag: Diagnostic, resultat: ResultatRatios, meta: Dict[str, str]) -> str:
    date = _dt.date.today().strftime("%d/%m/%Y")
    e = html.escape
    p: List[str] = []
    a = p.append

    note_texte = str(note_affichee(diag.score_global)) if diag.score_global is not None else "n.d."
    couleur_note = couleur_score(diag.score_global)

    a("<!DOCTYPE html><html lang='fr'><head><meta charset='utf-8'>")
    a(f"<title>Diagnostic financier — {e(meta.get('entreprise', 'Entreprise'))}</title>")
    a(f"<style>{CSS}</style></head><body><div class='page'>")

    a(f"<h1>📊 Diagnostic financier — {e(meta.get('entreprise', 'Entreprise'))}</h1>")
    a(
        f"<div class='meta'>📅 Exercice {e(meta.get('exercice', 'N'))} · 🏭 Secteur : {e(meta.get('secteur', 'Général'))} · "
        f"💱 Montants exprimés {e(meta.get('unite', 'en unités'))} · 🕒 Rapport généré le {date}</div>"
    )

    a("<div class='score-carte'>")
    a(
        f"<div class='score-anneau' style='background:conic-gradient({couleur_note} 0% "
        f"{max(0.0, min(100.0, diag.score_global or 0.0)):.0f}%, #e6eaf1 0%)'>"
        f"<div class='score-anneau-centre'><span style='color:{couleur_note}'>{note_texte}</span>"
        "<small>/100</small></div></div>"
    )
    icone_appreciation = ref.ICONES_APPRECIATION.get(diag.appreciation, "")
    ponderation = ", ".join(
        f"{ref.AXES[axe].lower()} {ref.POIDS_AXES[axe]:.0%}" for axe in ref.AXES
    )
    a(
        "<div class='score-legende'><strong>Situation "
        f"{e(diag.appreciation)} {icone_appreciation}</strong><br>Note globale pondérée : {e(ponderation)}.<br>"
        "Repères adaptés au secteur sélectionné.</div>"
    )
    a("</div>")

    a("<h2>📌 1. Synthèse</h2>")
    for paragraphe in diag.synthese.split("\n\n"):
        a(f"<p>{_markdown_inline(paragraphe)}</p>")

    a("<table><tr><th>Axe</th><th class='num'>Score /100</th><th>Poids</th><th>Niveau</th></tr>")
    for axe, libelle in ref.AXES.items():
        score = diag.scores_axes.get(axe)
        a(
            f"<tr><td>{ref.AXES_ICONES.get(axe, '')} {e(libelle)}</td>"
            f"<td class='num'>{note_affichee(score)}</td>" if score is not None else
            f"<tr><td>{ref.AXES_ICONES.get(axe, '')} {e(libelle)}</td><td class='num'>n.d.</td>",
        )
        a(f"<td>{ref.POIDS_AXES.get(axe, 0):.0%}</td><td style='width:34%'>{_barre(score)}</td></tr>")
    a("</table>")

    a("<h2>✅ 2. Points forts</h2>")
    if diag.points_forts:
        a("<ul>" + "".join(f"<li>{_markdown_inline(x)}</li>" for x in diag.points_forts) + "</ul>")
    else:
        a("<p>Aucun ratio n'atteint le niveau « bon » avec les données fournies.</p>")

    a("<h2>⚠️ 3. Points de vigilance</h2>")
    if diag.points_vigilance:
        a("<ul>" + "".join(f"<li>{_markdown_inline(x)}</li>" for x in diag.points_vigilance) + "</ul>")
    else:
        a("<p>Aucun point de vigilance majeur détecté.</p>")

    a("<h2>🎯 4. Priorités d'action</h2><ol>")
    for r in diag.recommandations:
        a(f"<li>{_markdown_inline(r)}</li>")
    a("</ol>")

    a("<h2>📊 5. Détail des ratios</h2>")
    for axe, libelle_axe in ref.AXES.items():
        lignes_axe = [l for l in diag.lignes if l.axe == axe]
        if not lignes_axe:
            continue
        a(f"<h3>{ref.AXES_ICONES.get(axe, '')} {e(libelle_axe)}</h3>")
        a(f"<p style='color:#64748b;font-size:13px'>{e(ref.AXES_DESCRIPTIONS.get(axe, ''))}</p>")
        for l in lignes_axe:
            bordure = l.couleur
            a(f"<div class='ratio' style='border-left-color:{bordure}'>")
            a(
                f"<h4>{l.icone} {e(l.libelle)} — <strong>{e(_valeur_texte(l.valeur, l.unite, diag.unite_courte))}</strong> {_badge(l.statut)}"
                + (
                    f" <span style='font-size:12px;color:#64748b'>Évolution : {e(l.evolution)} "
                    f"(N-1 : {e(_valeur_texte(l.valeur_n1, l.unite, diag.unite_courte))})</span>"
                    if l.evolution
                    else ""
                )
                + "</h4>"
            )
            a(f"<div class='formule'>{e(l.formule)}</div>")
            a(f"<p style='margin:8px 0 4px'>{e(l.texte)}</p>")
            a(f"<p style='margin:0;color:#64748b;font-size:13px'><em>À quoi ça sert :</em> {e(l.definition)}</p>")
            if l.conseil and l.statut == ref.STATUT_VIGILANCE:
                a(f"<p style='margin:6px 0 0;font-size:13px'><strong>Piste d'amélioration :</strong> {e(l.conseil)}</p>")
            a("</div>")

    if diag.alertes:
        a("<h2>🔍 6. Contrôles de cohérence</h2><ul>")
        for alerte in diag.alertes:
            a(f"<li><strong>{e(str(alerte.get('titre')))}</strong> — {e(str(alerte.get('message')))}</li>")
        a("</ul>")

    a(
        "<footer>Document généré automatiquement à partir des états financiers saisis. "
        "Il ne constitue ni un avis d'expert-comptable ni une opinion d'audit. "
        "Les repères utilisés sont des moyennes de marché et doivent être adaptés à l'activité réelle.</footer>"
    )
    a("</div></body></html>")
    return "".join(p)


def _markdown_inline(texte: str) -> str:
    """Convertit le **gras** Markdown en HTML."""
    morceaux = texte.split("**")
    sortie = []
    for i, morceau in enumerate(morceaux):
        sortie.append(f"<strong>{html.escape(morceau)}</strong>" if i % 2 else html.escape(morceau))
    return "".join(sortie)
