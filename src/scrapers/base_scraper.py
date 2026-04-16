# base_scraper.py
from dataclasses import dataclass

@dataclass
class MangaResult:
    """Un manga trouvé lors d'une recherche."""
    id: str
    title: str
    description: str
    source: str  # nom du site

@dataclass
class ChapterInfo:
    """Un chapitre disponible."""
    id: str
    number: str   # "56" ou "56.5"
    title: str    # titre du chapitre (souvent vide)
    lang: str     # "en", "fr", etc.
    pages: int    # nb de pages

class BaseScraper:
    """
    Moule commun pour tous les scrapers.
    Chaque nouveau site hérite de cette classe et implémente les 3 méthodes.
    """
    SOURCE_NAME = "Unknown"

    def search(self, title: str) -> list[MangaResult]:
        """Recherche un manga par titre. Retourne une liste de résultats."""
        raise NotImplementedError

    def get_chapters(self, manga_id: str, lang: str = "en") -> list[ChapterInfo]:
        """Retourne la liste des chapitres disponibles pour un manga."""
        raise NotImplementedError

    def get_page_urls(self, chapter_id: str) -> list[str]:
        """Retourne les URLs des images d'un chapitre."""
        raise NotImplementedError