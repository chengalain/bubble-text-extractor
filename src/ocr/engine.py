# engine.py — EasyOCR + upscaling 2x + masque bulles blanches
import cv2
import numpy as np
from pathlib import Path

try:
    import easyocr
    _EASYOCR_AVAILABLE = True
except ImportError:
    _EASYOCR_AVAILABLE = False


class OCREngine:
    CONFIDENCE_THRESHOLD = 0.40
    WHITE_THRESHOLD      = 220
    UPSCALE_FACTOR       = 2.0   # upscale avant OCR → meilleure lecture

    def __init__(self, lang: str = "en"):
        self.lang    = lang
        self._reader = None

    def _get_reader(self):
        if self._reader is None:
            if not _EASYOCR_AVAILABLE:
                raise RuntimeError("EasyOCR non installé. Lance : pip install easyocr")
            self._reader = easyocr.Reader([self.lang], gpu=False, verbose=False)
        return self._reader

    # ── Chargement + upscaling ─────────────────────────────────────────────────
    def _load_and_upscale(self, image_path: Path) -> tuple[np.ndarray, np.ndarray]:
        """
        Retourne (img_original, img_upscaled).
        Le masque est calculé sur l'original, l'OCR tourne sur l'upscaled.
        """
        img = cv2.imread(str(image_path))
        if img is None:
            raise ValueError(f"Impossible de charger : {image_path}")

        h, w = img.shape[:2]
        upscaled = cv2.resize(
            img,
            (int(w * self.UPSCALE_FACTOR), int(h * self.UPSCALE_FACTOR)),
            interpolation=cv2.INTER_CUBIC,
        )
        # Légère netteté après upscale pour les contours de lettres
        kernel   = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
        upscaled = cv2.filter2D(upscaled, -1, kernel)

        return img, upscaled

    # ── Masque bulles blanches ─────────────────────────────────────────────────
    def _bubble_mask(self, img: np.ndarray) -> np.ndarray:
        """
        Masque ne conservant que les régions blanches fermées de taille
        cohérente avec une bulle (ni pixel isolé, ni ciel entier).
        """
        h_img, w_img = img.shape[:2]
        page_area    = h_img * w_img

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, self.WHITE_THRESHOLD, 255, cv2.THRESH_BINARY)

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=4)
        opened = cv2.morphologyEx(closed, cv2.MORPH_OPEN,  kernel, iterations=2)

        # Garder uniquement les contours de taille bulle (0.5 % – 40 % de la page)
        contours, _ = cv2.findContours(opened, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        mask = np.zeros_like(opened)
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if page_area * 0.005 < area < page_area * 0.40:
                cv2.drawContours(mask, [cnt], -1, 255, thickness=cv2.FILLED)

        return mask

    # ── Filtre spatial ─────────────────────────────────────────────────────────
    @staticmethod
    def _in_bubble(bbox: list, mask: np.ndarray, scale: float) -> bool:
        """Centre de la bbox ramenée à l'échelle du masque (original)."""
        cx = int(sum(p[0] for p in bbox) / 4 / scale)
        cy = int(sum(p[1] for p in bbox) / 4 / scale)
        h, w = mask.shape
        cx = max(0, min(cx, w - 1))
        cy = max(0, min(cy, h - 1))
        return mask[cy, cx] == 255

    # ── Regroupement lignes → bulles ───────────────────────────────────────────
    @staticmethod
    def _group_into_bubbles(results: list, line_gap: int = 40) -> list[str]:
        if not results:
            return []

        bubbles: list[list[str]] = []
        current: list[str]       = [results[0][1]]
        prev_bottom: float       = results[0][0][2][1]

        for bbox, text, _ in results[1:]:
            y_top = bbox[0][1]
            if y_top - prev_bottom <= line_gap:
                current.append(text)
            else:
                bubbles.append(current)
                current = [text]
            prev_bottom = bbox[2][1]

        bubbles.append(current)
        return [" ".join(g) for g in bubbles]

    # ── Point d'entrée public ──────────────────────────────────────────────────
    def extract_from_images(self, image_paths: list[Path]) -> list[str]:
        reader     = self._get_reader()
        all_texts: list[str] = []

        for image_path in image_paths:
            try:
                img_orig, img_up = self._load_and_upscale(image_path)
            except ValueError:
                continue

            mask    = self._bubble_mask(img_orig)
            results = reader.readtext(img_up, paragraph=False)

            filtered = [
                r for r in results
                if r[2] >= self.CONFIDENCE_THRESHOLD
                and r[1].strip()
                and self._in_bubble(r[0], mask, self.UPSCALE_FACTOR)
            ]

            filtered.sort(key=lambda r: (r[0][0][1], r[0][0][0]))
            # line_gap en pixels upscalés — large pour ne pas couper une bulle en deux
            bubbles = self._group_into_bubbles(filtered, line_gap=80)
            all_texts.extend(bubbles)

        return all_texts
