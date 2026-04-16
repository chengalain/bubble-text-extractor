# mangadex.py — MangaDex official API (no scraping needed)
import requests
import time
from .base_scraper import BaseScraper, MangaResult, ChapterInfo

class MangaDexScraper(BaseScraper):
    SOURCE_NAME = "MangaDex"
    BASE_URL    = "https://api.mangadex.org"
    DELAY       = 0.5  # secondes entre requêtes (respecter rate limit)

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "BubbleTextExtractor/1.0 (educational project)"
        })

    def _get(self, endpoint: str, params: dict = None) -> dict:
        """Requête GET avec gestion erreurs + rate limiting."""
        url = f"{self.BASE_URL}{endpoint}"
        time.sleep(self.DELAY)
        try:
            r = self.session.get(url, params=params, timeout=15)
            r.raise_for_status()
            return r.json()
        except requests.exceptions.Timeout:
            raise ConnectionError("MangaDex ne répond pas (timeout).")
        except requests.exceptions.HTTPError as e:
            raise ConnectionError(f"Erreur API MangaDex : {e.response.status_code}")
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Problème réseau : {e}")

    # ── Recherche ──────────────────────────────────────────────────────────────
    def search(self, title: str) -> list[MangaResult]:
        """Recherche un manga par titre sur MangaDex."""
        data = self._get("/manga", params={
            "title": title,
            "limit": 10,
            "availableTranslatedLanguage[]": "en",
            "order[relevance]": "desc",
            "includes[]": "cover_art",
        })

        results = []
        for item in data.get("data", []):
            attrs = item["attributes"]

            # Titre : préférer EN, sinon premier dispo
            titles = attrs.get("title", {})
            name = (
                titles.get("en")
                or titles.get("ja-ro")
                or next(iter(titles.values()), "Unknown")
            )

            # Description courte
            descs = attrs.get("description", {})
            desc = descs.get("en", "")
            if len(desc) > 120:
                desc = desc[:117] + "..."

            results.append(MangaResult(
                id=item["id"],
                title=name,
                description=desc,
                source=self.SOURCE_NAME,
            ))

        return results

    # ── Chapitres ──────────────────────────────────────────────────────────────
    def get_chapters(self, manga_id: str, lang: str = "en") -> list[ChapterInfo]:
        """Récupère tous les chapitres EN d'un manga, triés par numéro."""
        chapters = []
        offset   = 0
        limit    = 100

        while True:
            data = self._get("/chapter", params={
                "manga": manga_id,
                "translatedLanguage[]": lang,
                "limit": limit,
                "offset": offset,
                "order[chapter]": "asc",
                "includes[]": "scanlation_group",
            })

            items = data.get("data", [])
            if not items:
                break

            for item in items:
                attrs = item["attributes"]
                chapters.append(ChapterInfo(
                    id=item["id"],
                    number=attrs.get("chapter") or "?",
                    title=attrs.get("title") or "",
                    lang=attrs.get("translatedLanguage", lang),
                    pages=attrs.get("pages", 0),
                ))

            # Pagination : on arrête si on a tout
            total = data.get("total", 0)
            offset += limit
            if offset >= total:
                break

        return chapters

    # ── URLs des pages ─────────────────────────────────────────────────────────
    def get_page_urls(self, chapter_id: str) -> list[str]:
        """Retourne les URLs CDN des images d'un chapitre."""
        data = self._get(f"/at-home/server/{chapter_id}")

        base_url = data["baseUrl"]
        chapter  = data["chapter"]
        hash_val = chapter["hash"]
        files    = chapter["data"]  # qualité normale

        return [
            f"{base_url}/data/{hash_val}/{filename}"
            for filename in files
        ]