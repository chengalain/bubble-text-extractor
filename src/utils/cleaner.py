# cleaner.py — Export du texte extrait vers un fichier .txt
import re
from pathlib import Path


def _safe_filename(title: str) -> str:
    """Convertit un titre en nom de fichier sûr (lowercase, underscores)."""
    slug = title.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)   # retire les caractères spéciaux
    slug = re.sub(r"[\s-]+", "_", slug)     # espaces/tirets → underscore
    return slug[:40]                         # tronque à 40 chars


def export_txt(
    texts: list[str],
    manga_title: str,
    chapter_number: str,
    output_dir: str | Path = "output",
) -> Path:
    """
    Génère un fichier .txt formaté à partir des textes extraits.

    Format :
        [Bulle 1]
        texte

        [Bulle 2]
        texte

    Retourne le Path du fichier créé.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    slug     = _safe_filename(manga_title)
    filename = f"{slug}_ch{chapter_number}_en.txt"
    out_path = output_dir / filename

    lines: list[str] = []

    if not texts:
        lines.append("(Aucun texte extrait)\n")
    else:
        for i, text in enumerate(texts, 1):
            lines.append(f"[Bulle {i}]")
            lines.append(text.strip())
            lines.append("")   # ligne vide entre les bulles

    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path
