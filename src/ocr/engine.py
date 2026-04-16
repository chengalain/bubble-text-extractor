# engine.py — Hybrid : masque bulles blanches + EasyOCR full-page
import cv2
import numpy as np
from pathlib import Path

try:
    import easyocr
    _EASYOCR_AVAILABLE = True
except ImportError:
    _EASYOCR_AVAILABLE = False


class OCREngine:
    """
    Pipeline hybride :
    1. Masque des régions blanches (bulles manga ≈ blanc pur)
    2. EasyOCR sur la page entière (CRAFT détecte les zones de texte)
    3. On ne garde que les détections dont le centre tombe dans une bulle blanche
    4. Regroupement des lignes proches en une seule bulle
    """

    CONFIDENCE_THRESHOLD = 0.45
    WHITE_THRESHOLD      = 210   # pixel >= cette valeur → considéré "blanc"

    def __init__(self, lang: str = "en"):
        self.lang    = lang
        self._reader = None

    # ── Init lazy EasyOCR ──────────────────────────────────────────────────────
    def _get_reader(self):
        if self._reader is None:
            if not _EASYOCR_AVAILABLE:
                raise RuntimeError("EasyOCR non installé. Lance : pip install easyocr")
            self._reader = easyocr.Reader([self.lang], gpu=False, verbose=False)
        return self._reader

    # ── Chargement ────────────────────────────────────────────────────────────
    @staticmethod
    def _load(image_path: Path) -> np.ndarray:
        img = cv2.imread(str(image_path))
        if img is None:
            raise ValueError(f"Impossible de charger : {image_path}")
        return img

    # ── Masque des bulles blanches ─────────────────────────────────────────────
    def _bubble_mask(self, img: np.ndarray) -> np.ndarray:
        """
        Retourne un masque binaire où les pixels blancs (bulles) valent 255.
        Stratégie :
          - Seuillage sur les pixels très clairs (>= WHITE_THRESHOLD)
          - Fermeture morphologique pour boucher les trous dans les bulles
          - Ouverture pour éliminer le bruit (petites zones blanches isolées)
        """
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, mask = cv2.threshold(gray, self.WHITE_THRESHOLD, 255, cv2.THRESH_BINARY)

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        mask   = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=4)
        mask   = cv2.morphologyEx(mask, cv2.MORPH_OPEN,  kernel, iterations=2)

        return mask

    # ── Filtre spatial : ne garder que le texte dans les bulles ───────────────
    @staticmethod
    def _in_bubble(bbox: list, mask: np.ndarray) -> bool:
        """
        Retourne True si le centre de la bbox tombe dans une zone blanche du masque.
        bbox = [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
        """
        cx = int(sum(p[0] for p in bbox) / 4)
        cy = int(sum(p[1] for p in bbox) / 4)
        h, w = mask.shape
        cx = max(0, min(cx, w - 1))
        cy = max(0, min(cy, h - 1))
        return mask[cy, cx] == 255

    # ── Regroupement des lignes en bulles ──────────────────────────────────────
    @staticmethod
    def _group_into_bubbles(results: list, line_gap: int = 30) -> list[str]:
        """
        Regroupe les détections proches verticalement (même bulle).
        line_gap : écart max en pixels entre deux lignes d'une même bulle.
        """
        if not results:
            return []

        bubbles: list[list[str]]  = []
        current: list[str]        = [results[0][1]]
        prev_bottom: float        = results[0][0][2][1]

        for bbox, text, _ in results[1:]:
            y_top = bbox[0][1]
            if y_top - prev_bottom <= line_gap:
                current.append(text)
            else:
                bubbles.append(current)
                current = [text]
            prev_bottom = bbox[2][1]

        bubbles.append(current)
        return [" ".join(group) for group in bubbles]

    # ── Point d'entrée public ──────────────────────────────────────────────────
    def extract_from_images(self, image_paths: list[Path]) -> list[str]:
        """
        Traite une liste d'images de manga.
        Retourne une liste de strings, une par bulle détectée.
        """
        reader     = self._get_reader()
        all_texts: list[str] = []

        for image_path in image_paths:
            try:
                img = self._load(image_path)
            except ValueError:
                continue

            # 1. Masque des zones blanches (bulles)
            mask = self._bubble_mask(img)

            # 2. EasyOCR sur la page entière
            results = reader.readtext(img, paragraph=False)

            # 3. Filtrer : confiance + centre dans une bulle blanche
            filtered = [
                r for r in results
                if r[2] >= self.CONFIDENCE_THRESHOLD
                and r[1].strip()
                and self._in_bubble(r[0], mask)
            ]

            # 4. Trier top→bottom, left→right
            filtered.sort(key=lambda r: (r[0][0][1], r[0][0][0]))

            # 5. Regrouper les lignes proches
            bubbles = self._group_into_bubbles(filtered)
            all_texts.extend(bubbles)

        return all_texts
