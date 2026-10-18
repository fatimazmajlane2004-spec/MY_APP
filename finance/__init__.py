"""Package de calcul et d'analyse financière.

Modules :
    referentiel  — postes comptables, définition des ratios, seuils et repères
    ratios       — agrégation des postes et calcul des ratios
    diagnostic   — notation, interprétation en langage simple, recommandations
    reporting    — tableaux et rapports exportables (Markdown, HTML)
    io_utils     — modèles de fichiers, import des bilans et CPC
"""

from . import diagnostic, io_utils, ratios, referentiel, reporting  # noqa: F401

__version__ = "1.0.0"
__all__ = ["referentiel", "ratios", "diagnostic", "reporting", "io_utils"]
