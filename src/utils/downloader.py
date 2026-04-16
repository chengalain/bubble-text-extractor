# downloader.py — téléchargement des pages d'un chapitre
import os
import uuid
import time
import requests
from pathlib import Path


class ChapterDownloader:
    HEADERS = {
        "User-Agent": "BubbleTextExtractor/1.0 (educational project)",
        "Referer":    "https://mangadex.org/",
    }
    DELAY        = 0.3   # secondes entre chaque image
    MAX_RETRIES  = 3
    TIMEOUT      = 20

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    # ── Dossier temporaire ─────────────────────────────────────────────────────
    def _make_tmp_dir(self) -> Path:
        session_id = uuid.uuid4().hex[:8]
        tmp = Path(f"/tmp/bubble_ocr_{session_id}")
        tmp.mkdir(parents=True, exist_ok=True)
        return tmp

    # ── Barre de progression ───────────────────────────────────────────────────
    @staticmethod
    def _progress(current: int, total: int, width: int = 30):
        filled = int(width * current / total)
        bar    = "█" * filled + "░" * (width - filled)
        pct    = int(100 * current / total)
        print(f"\r  📥 [{bar}] {pct:>3}%  ({current}/{total})", end="", flush=True)

    # ── Téléchargement d'une image ─────────────────────────────────────────────
    def _download_one(self, url: str, dest: Path) -> bool:
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                r = self.session.get(url, timeout=self.TIMEOUT, stream=True)
                r.raise_for_status()
                with open(dest, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                return True
            except requests.exceptions.RequestException:
                if attempt < self.MAX_RETRIES:
                    time.sleep(1.5 * attempt)
        return False

    # ── Téléchargement complet d'un chapitre ───────────────────────────────────
    def download_chapter(self, page_urls: list[str]) -> tuple[Path, list[Path]]:
        """
        Télécharge toutes les pages dans un dossier /tmp/.
        Retourne (tmp_dir, [chemins images triés]).
        """
        tmp_dir    = self._make_tmp_dir()
        downloaded = []
        failed     = []

        total = len(page_urls)
        print()

        for i, url in enumerate(page_urls, 1):
            self._progress(i, total)

            # Extension depuis l'URL
            ext  = Path(url.split("?")[0]).suffix or ".jpg"
            dest = tmp_dir / f"page_{i:03d}{ext}"

            ok = self._download_one(url, dest)

            if ok:
                downloaded.append(dest)
            else:
                failed.append(i)
            time.sleep(self.DELAY)

        print()  # newline après la barre

        if failed:
            print(f"\n  ⚠  Pages échouées : {failed}")

        # Trier par nom de fichier (ordre de lecture)
        downloaded.sort()
        return tmp_dir, downloaded

    # ── Nettoyage ──────────────────────────────────────────────────────────────
    @staticmethod
    def cleanup(tmp_dir: Path):
        """Supprime le dossier temporaire et son contenu."""
        if not tmp_dir.exists():
            return
        for f in tmp_dir.iterdir():
            f.unlink()
        tmp_dir.rmdir()