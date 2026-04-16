#!/usr/bin/env python3
"""
Bubble Text Extractor — Interactive CLI
"""

import os
import sys

# Ajouter src/ au path pour les imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from scrapers.mangadex import MangaDexScraper
from scrapers.base_scraper import MangaResult, ChapterInfo
from utils.downloader import ChapterDownloader
from ocr.engine import OCREngine
from utils.cleaner import export_txt

# ── Couleurs terminal ──────────────────────────────────────────────────────────
class Colors:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    RED     = "\033[91m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    BLUE    = "\033[94m"
    CYAN    = "\033[96m"
    WHITE   = "\033[97m"
    DIM     = "\033[2m"

def c(text, color):
    return f"{color}{text}{Colors.RESET}"

# ── Helpers affichage ──────────────────────────────────────────────────────────
def clear():
    os.system("cls" if os.name == "nt" else "clear")

def header():
    print()
    print(c("  ╔════════════════════════════════════════╗", Colors.CYAN))
    print(c("  ║  ", Colors.CYAN) + c("🫧  Bubble Text Extractor", Colors.BOLD + Colors.WHITE) + c("           ║", Colors.CYAN))
    print(c("  ║  ", Colors.CYAN) + c("Extract text from manga chapters", Colors.DIM) + c("    ║", Colors.CYAN))
    print(c("  ╚════════════════════════════════════════╝", Colors.CYAN))
    print()

def separator():
    print(c("  ─────────────────────────────────────────", Colors.DIM))

def success(msg): print(c(f"  ✅ {msg}", Colors.GREEN))
def error(msg):   print(c(f"  ❌ {msg}", Colors.RED))
def info(msg):    print(c(f"  ℹ  {msg}", Colors.CYAN))
def warn(msg):    print(c(f"  ⚠  {msg}", Colors.YELLOW))
def loading(msg): print(c(f"  ⏳ {msg}", Colors.YELLOW), end="\r")

def prompt(msg):
    return input(c(f"\n  ▶ {msg}: ", Colors.YELLOW)).strip()

def print_menu(options: list[tuple[str, str]]):
    print()
    for i, (label, desc) in enumerate(options, 1):
        num = c(f"  [{i}]", Colors.CYAN + Colors.BOLD)
        lbl = c(f" {label}", Colors.WHITE + Colors.BOLD)
        dsc = c(f"  —  {desc}", Colors.DIM) if desc else ""
        print(f"{num}{lbl}{dsc}")
    print()

def ask_choice(count: int, allow_back=True) -> int | None:
    """Retourne index 0-based ou None pour retour."""
    if allow_back:
        print(c("  [0] ← Retour", Colors.DIM))
    print()
    while True:
        raw = prompt("Ton choix")
        if raw in ("0", "q", "") and allow_back:
            return None
        if raw.isdigit() and 1 <= int(raw) <= count:
            return int(raw) - 1
        error(f"Choix invalide. Entre un nombre entre 1 et {count}.")

# ── Écran : Résultats de recherche ─────────────────────────────────────────────
def display_search_results(results: list[MangaResult]) -> MangaResult | None:
    print(c(f"\n  {len(results)} résultat(s) trouvé(s) :\n", Colors.GREEN + Colors.BOLD))
    separator()

    for i, r in enumerate(results, 1):
        num   = c(f"  [{i}]", Colors.CYAN + Colors.BOLD)
        title = c(f" {r.title}", Colors.WHITE + Colors.BOLD)
        src   = c(f"  ({r.source})", Colors.DIM)
        print(f"{num}{title}{src}")
        if r.description:
            # Tronquer à 80 chars pour l'affichage
            desc = r.description[:80] + "..." if len(r.description) > 80 else r.description
            print(c(f"       {desc}", Colors.DIM))
        print()

    choice = ask_choice(len(results))
    return results[choice] if choice is not None else None

# ── Écran : Sélection chapitre ─────────────────────────────────────────────────
def display_chapters(chapters: list[ChapterInfo], manga_title: str) -> ChapterInfo | None:
    clear()
    header()
    print(c(f"  📚 Chapitres disponibles — {manga_title}", Colors.BOLD + Colors.WHITE))
    separator()
    print(c(f"\n  {len(chapters)} chapitre(s) en EN trouvé(s)\n", Colors.GREEN))

    # Afficher par groupes de 20 pour ne pas flood le terminal
    PAGE_SIZE = 20
    page = 0

    while True:
        start = page * PAGE_SIZE
        end   = min(start + PAGE_SIZE, len(chapters))
        batch = chapters[start:end]

        for i, ch in enumerate(batch, start + 1):
            num   = c(f"  [{i:>3}]", Colors.CYAN + Colors.BOLD)
            ch_n  = c(f" Ch. {ch.number:<8}", Colors.WHITE + Colors.BOLD)
            pages = c(f"  {ch.pages} pages", Colors.DIM)
            title = c(f"  {ch.title}", Colors.DIM) if ch.title else ""
            print(f"{num}{ch_n}{pages}{title}")

        print()

        # Options navigation
        nav_options = []
        if end < len(chapters):
            nav_options.append(c("  [n] → Page suivante", Colors.CYAN))
        if page > 0:
            nav_options.append(c("  [p] ← Page précédente", Colors.CYAN))
        nav_options.append(c("  [0] ← Retour", Colors.DIM))

        for opt in nav_options:
            print(opt)
        print()

        raw = prompt("Numéro du chapitre à extraire (ou n/p pour naviguer)")

        if raw.lower() == "n" and end < len(chapters):
            page += 1
            clear()
            header()
            print(c(f"  📚 Chapitres disponibles — {manga_title}", Colors.BOLD + Colors.WHITE))
            separator()
            continue
        elif raw.lower() == "p" and page > 0:
            page -= 1
            clear()
            header()
            print(c(f"  📚 Chapitres disponibles — {manga_title}", Colors.BOLD + Colors.WHITE))
            separator()
            continue
        elif raw in ("0", "q", ""):
            return None
        elif raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(chapters):
                return chapters[idx]
            # Chercher par numéro de chapitre aussi
            match = next((ch for ch in chapters if ch.number == raw), None)
            if match:
                return match
            error(f"Numéro invalide.")
        else:
            # Chercher par numéro de chapitre (ex: "56.5")
            match = next((ch for ch in chapters if ch.number == raw), None)
            if match:
                return match
            error("Entrée invalide.")

# ── Écran : Confirmation avant extraction ─────────────────────────────────────
def screen_confirm_extract(manga: MangaResult, chapter: ChapterInfo, page_urls: list[str]) -> bool:
    clear()
    header()
    print(c("  📋 Récapitulatif", Colors.BOLD + Colors.WHITE))
    separator()
    print()
    print(c("  Manga   : ", Colors.DIM) + c(manga.title, Colors.WHITE + Colors.BOLD))
    print(c("  Chapitre: ", Colors.DIM) + c(f"Ch. {chapter.number}" + (f" — {chapter.title}" if chapter.title else ""), Colors.WHITE))
    print(c("  Langue  : ", Colors.DIM) + c("EN", Colors.WHITE))
    print(c("  Pages   : ", Colors.DIM) + c(str(len(page_urls)), Colors.WHITE))
    print(c("  Source  : ", Colors.DIM) + c(manga.source, Colors.WHITE))
    print()

    # Nom du fichier de sortie
    safe_title = manga.title.lower().replace(" ", "_")[:30]
    output_file = f"{safe_title}_ch{chapter.number}_en.txt"
    print(c("  Output  : ", Colors.DIM) + c(f"output/{output_file}", Colors.GREEN))
    print()
    separator()

    print_menu([
        ("Lancer l'extraction", "téléchargement + OCR"),
        ("Annuler",             "retour au menu"),
    ])

    choice = ask_choice(2, allow_back=False)
    return choice == 0

# ── Écran : Pipeline extraction ────────────────────────────────────────────────
def screen_extract_pipeline(manga: MangaResult, chapter: ChapterInfo, page_urls: list[str]):
    clear()
    header()
    print(c("  ⚙  Extraction en cours...", Colors.BOLD + Colors.WHITE))
    separator()
    print()
    info(f"{manga.title} — Ch. {chapter.number} ({len(page_urls)} pages)")
    print()
    separator()

    # ── Step 3 : Téléchargement ────────────────────────────────────────────────
    print()
    print(c("  📥 Téléchargement des pages...", Colors.WHITE + Colors.BOLD))

    downloader = ChapterDownloader()
    try:
        tmp_dir, image_paths = downloader.download_chapter(page_urls)
    except Exception as e:
        error(f"Téléchargement échoué : {e}")
        input(c("\n  Appuie sur Entrée...", Colors.DIM))
        return

    success(f"{len(image_paths)} pages téléchargées dans {tmp_dir}")
    print()

    # ── Step 4 : OCR ──────────────────────────────────────────────────────────
    print()
    print(c("  🔬 Détection des bulles + OCR...", Colors.WHITE + Colors.BOLD))
    info("Initialisation EasyOCR (peut prendre quelques secondes)...")

    engine = OCREngine(lang="en")
    try:
        texts = engine.extract_from_images(image_paths)
    except RuntimeError as e:
        error(str(e))
        input(c("\n  Appuie sur Entrée...", Colors.DIM))
        return

    if texts:
        success(f"{len(texts)} bulle(s) extraite(s).")
    else:
        warn("Aucun texte détecté dans ce chapitre.")

    print()

    # ── Step 5 : Export TXT ────────────────────────────────────────────────────
    print(c("  💾 Export du fichier TXT...", Colors.WHITE + Colors.BOLD))

    try:
        out_path = export_txt(texts, manga.title, chapter.number, output_dir="output")
        success(f"Fichier généré : {out_path}")
    except Exception as e:
        error(f"Export échoué : {e}")
        input(c("\n  Appuie sur Entrée...", Colors.DIM))
        return

    print()
    separator()
    print()

    # ── Nettoyage ──────────────────────────────────────────────────────────────
    raw = prompt("Supprimer les images temporaires ? (o/n) [o]")
    if raw.lower() != "n":
        downloader.cleanup(tmp_dir)
        success("Images temporaires supprimées.")
    else:
        info(f"Images conservées dans : {tmp_dir}")

    print()
    input(c("  Appuie sur Entrée pour revenir au menu...", Colors.DIM))

# ── Écran : Recherche ──────────────────────────────────────────────────────────
def screen_search():
    clear()
    header()
    print(c("  🔍 Rechercher un manga", Colors.BOLD + Colors.WHITE))
    separator()

    title = prompt("Titre du manga")
    if not title:
        return

    print()
    loading(f"Recherche de '{title}' sur MangaDex...")

    scraper = MangaDexScraper()

    try:
        results = scraper.search(title)
    except ConnectionError as e:
        print()
        error(str(e))
        input(c("\n  Appuie sur Entrée...", Colors.DIM))
        return

    print()  # clear le \r du loading

    if not results:
        warn(f"Aucun résultat pour '{title}'.")
        info("Essaie un titre différent ou en anglais.")
        input(c("\n  Appuie sur Entrée...", Colors.DIM))
        return

    # Sélection manga
    manga = display_search_results(results)
    if manga is None:
        return

    # Récupération des chapitres
    clear()
    header()
    print(c(f"  📚 Chargement des chapitres — {manga.title}", Colors.BOLD + Colors.WHITE))
    separator()
    print()
    loading("Récupération des chapitres EN...")

    try:
        chapters = scraper.get_chapters(manga.id, lang="en")
    except ConnectionError as e:
        print()
        error(str(e))
        input(c("\n  Appuie sur Entrée...", Colors.DIM))
        return

    print()

    if not chapters:
        warn("Aucun chapitre EN disponible pour ce manga.")
        input(c("\n  Appuie sur Entrée...", Colors.DIM))
        return

    # Sélection chapitre
    chapter = display_chapters(chapters, manga.title)
    if chapter is None:
        return

    # Récupération URLs des pages
    loading(f"Récupération des URLs — Ch. {chapter.number}...")

    try:
        page_urls = scraper.get_page_urls(chapter.id)
    except ConnectionError as e:
        print()
        error(str(e))
        input(c("\n  Appuie sur Entrée...", Colors.DIM))
        return

    print()

    # Confirmation + lancement
    confirmed = screen_confirm_extract(manga, chapter, page_urls)
    if confirmed:
        screen_extract_pipeline(manga, chapter, page_urls)

# ── Écran : URL directe ────────────────────────────────────────────────────────
def screen_extract_url():
    clear()
    header()
    print(c("  🔗 Extraction par URL directe", Colors.BOLD + Colors.WHITE))
    separator()
    print()
    warn("Fonctionnalité URL directe — disponible à V1 (multi-sites).")
    info("Pour l'instant, utilise la recherche par titre (MangaDex).")
    print()
    input(c("  Appuie sur Entrée...", Colors.DIM))

# ── Écran : À propos ───────────────────────────────────────────────────────────
def screen_about():
    clear()
    header()
    print(c("  ℹ  À propos", Colors.BOLD + Colors.WHITE))
    separator()
    print()
    print(c("  Bubble Text Extractor v0.2", Colors.CYAN))
    print(c("  Auteur  : Alain", Colors.DIM))
    print(c("  Licence : MIT (educational purposes)", Colors.DIM))
    print()
    print(c("  Roadmap :", Colors.WHITE + Colors.BOLD))
    print(c("  Step 1 ✅  Structure + CLI interactif", Colors.GREEN))
    print(c("  Step 2 ✅  MangaDex API — recherche + chapitres", Colors.GREEN))
    print(c("  Step 3 ✅  Téléchargement des images", Colors.GREEN))
    print(c("  Step 4 ✅  OCR + Export TXT", Colors.GREEN))
    print(c("  Step 5 ⏳  Polish + gestion erreurs", Colors.DIM))
    print()
    input(c("  Appuie sur Entrée pour revenir au menu...", Colors.DIM))

# ── Menu principal ─────────────────────────────────────────────────────────────
def main_menu():
    menu = [
        ("Rechercher un manga",      "Titre → chapitres → extraction"),
        ("Extraire via URL directe", "Colle l'URL d'un chapitre (V1)"),
        ("À propos",                 "Roadmap du projet"),
        ("Quitter",                  ""),
    ]
    actions = [screen_search, screen_extract_url, screen_about, None]

    while True:
        clear()
        header()
        print(c("  Menu principal", Colors.BOLD + Colors.WHITE))
        separator()
        print_menu(menu)

        choice = ask_choice(len(menu), allow_back=False)
        if choice is None:
            continue
        if actions[choice] is None:
            clear()
            print()
            print(c("  👋 À bientôt !\n", Colors.CYAN + Colors.BOLD))
            sys.exit(0)
        actions[choice]()

# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print()
        print(c("\n  👋 Interruption. À bientôt !\n", Colors.CYAN))
        sys.exit(0)