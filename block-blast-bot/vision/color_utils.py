"""
Block Blast Bot - Color Utils
==============================
أدوات مساعدة للتعامل مع الألوان:
- تحويل BGR ↔ HSV
- تصنيف الألوان
- مقارنة الألوان
- استخراج الألوان السائدة
"""

import sys
from pathlib import Path
from typing import Optional, Tuple, List, Dict
from collections import Counter

import cv2
import numpy as np
from loguru import logger

try:
    from config import COLOR_CONFIG
except ImportError:
    COLOR_CONFIG = {"colors": {}, "hue_tolerance": 10}


# ============================================================
# ثوابت الألوان الشائعة (BGR)
# ============================================================

NAMED_COLORS_BGR: Dict[str, Tuple[int, int, int]] = {
    "red":     (0, 0, 255),
    "green":   (0, 255, 0),
    "blue":    (255, 0, 0),
    "yellow":  (0, 255, 255),
    "orange":  (0, 165, 255),
    "purple":  (128, 0, 128),
    "pink":    (203, 192, 255),
    "cyan":    (255, 255, 0),
    "white":   (255, 255, 255),
    "black":   (0, 0, 0),
    "gray":    (128, 128, 128),
}


# ============================================================
# كلاس أدوات الألوان
# ============================================================

class ColorUtils:
    """أدوات مساعدة للتعامل مع الألوان"""

    def __init__(self):
        self.color_ranges = COLOR_CONFIG.get("colors", {})
        self.hue_tolerance = COLOR_CONFIG.get("hue_tolerance", 10)

        # إذا لم تكن هناك نطاقات، استخدم الافتراضية
        if not self.color_ranges:
            self.color_ranges = {
                "red":    {"h_min": 0,   "h_max": 10,  "s_min": 100, "v_min": 100},
                "orange": {"h_min": 11,  "h_max": 22,  "s_min": 100, "v_min": 100},
                "yellow": {"h_min": 23,  "h_max": 35,  "s_min": 100, "v_min": 100},
                "green":  {"h_min": 36,  "h_max": 85,  "s_min": 80,  "v_min": 80},
                "cyan":   {"h_min": 86,  "h_max": 100, "s_min": 80,  "v_min": 80},
                "blue":   {"h_min": 101, "h_max": 130, "s_min": 80,  "v_min": 80},
                "purple": {"h_min": 131, "h_max": 160, "s_min": 80,  "v_min": 80},
                "pink":   {"h_min": 161, "h_max": 179, "s_min": 80,  "v_min": 80},
            }

        logger.debug(f"🎨 ColorUtils جاهز — {len(self.color_ranges)} ألوان")

    # ========================================================
    # التحويلات
    # ========================================================

    @staticmethod
    def bgr_to_hsv(bgr: Tuple[int, int, int]) -> Tuple[int, int, int]:
        """تحويل BGR → HSV (لون واحد)"""
        b, g, r = int(bgr[0]), int(bgr[1]), int(bgr[2])
        pixel = np.uint8([[[b, g, r]]])
        hsv = cv2.cvtColor(pixel, cv2.COLOR_BGR2HSV)
        h, s, v = hsv[0, 0]
        return int(h), int(s), int(v)

    @staticmethod
    def hsv_to_bgr(hsv: Tuple[int, int, int]) -> Tuple[int, int, int]:
        """تحويل HSV → BGR (لون واحد)"""
        h, s, v = int(hsv[0]), int(hsv[1]), int(hsv[2])
        pixel = np.uint8([[[h, s, v]]])
        bgr = cv2.cvtColor(pixel, cv2.COLOR_HSV2BGR)
        b, g, r = bgr[0, 0]
        return int(b), int(g), int(r)

    @staticmethod
    def rgb_to_bgr(rgb: Tuple[int, int, int]) -> Tuple[int, int, int]:
        """تحويل RGB → BGR"""
        r, g, b = rgb
        return int(b), int(g), int(r)

    @staticmethod
    def bgr_to_rgb(bgr: Tuple[int, int, int]) -> Tuple[int, int, int]:
        """تحويل BGR → RGB"""
        b, g, r = bgr
        return int(r), int(g), int(b)

    # ========================================================
    # تصنيف الألوان
    # ========================================================

    def classify(
        self,
        bgr: Tuple[int, int, int],
        use_hsv: bool = True,
    ) -> Optional[str]:
        """
        تصنيف لون BGR إلى اسم

        Args:
            bgr: (B, G, R)
            use_hsv: استخدام HSV (أدق)

        Returns:
            اسم اللون أو None
        """
        if use_hsv:
            h, s, v = self.bgr_to_hsv(bgr)

            # فحص الأبيض/الأسود/الرمادي أولاً
            if s < 40:
                if v > 200:
                    return "white"
                elif v < 50:
                    return "black"
                else:
                    return "gray"

            # تصنيف حسب Hue
            for name, rng in self.color_ranges.items():
                h_min = rng.get("h_min", 0)
                h_max = rng.get("h_max", 179)
                s_min = rng.get("s_min", 0)
                v_min = rng.get("v_min", 0)

                if h_min <= h <= h_max and s >= s_min and v >= v_min:
                    return name

            return None

        else:
            # تصنيف بسيط بالمسافة من الألوان المعروفة
            return self._classify_by_distance(bgr)

    def _classify_by_distance(
        self,
        bgr: Tuple[int, int, int],
    ) -> Optional[str]:
        """تصنيف بمسافة BGR من الألوان المعروفة"""
        best_name = None
        best_distance = float("inf")

        for name, ref_bgr in NAMED_COLORS_BGR.items():
            distance = self.color_distance(bgr, ref_bgr)
            if distance < best_distance:
                best_distance = distance
                best_name = name

        # إذا كانت المسافة كبيرة جداً، لا نعرف
        if best_distance > 150:
            return None

        return best_name

    # ========================================================
    # مقارنة الألوان
    # ========================================================

    @staticmethod
    def color_distance(
        c1: Tuple[int, int, int],
        c2: Tuple[int, int, int],
    ) -> float:
        """
        المسافة الإقليدية بين لونين في BGR
        """
        b1, g1, r1 = int(c1[0]), int(c1[1]), int(c1[2])
        b2, g2, r2 = int(c2[0]), int(c2[1]), int(c2[2])

        return float(np.sqrt(
            (b1 - b2) ** 2 +
            (g1 - g2) ** 2 +
            (r1 - r2) ** 2
        ))

    @staticmethod
    def color_distance_hue(
        c1: Tuple[int, int, int],
        c2: Tuple[int, int, int],
    ) -> float:
        """
        المسافة في Hue فقط (H من HSV)
        (0-90، حيث 0 = نفس اللون)
        """
        h1, _, _ = ColorUtils.bgr_to_hsv(c1)
        h2, _, _ = ColorUtils.bgr_to_hsv(c2)

        # الفرق مع مراعاة الدورية (0-179)
        diff = abs(h1 - h2)
        if diff > 90:
            diff = 180 - diff

        return float(diff)

    def is_similar(
        self,
        c1: Tuple[int, int, int],
        c2: Tuple[int, int, int],
        threshold: float = 50,
    ) -> bool:
        """هل اللونان متشابهان؟"""
        return self.color_distance(c1, c2) < threshold

    # ========================================================
    # استخراج الألوان السائدة
    # ========================================================

    def dominant_color(
        self,
        region: np.ndarray,
        mask: Optional[np.ndarray] = None,
        use_median: bool = True,
    ) -> Optional[Tuple[int, int, int]]:
        """
        استخراج اللون السائد من منطقة

        Args:
            region: صورة (H, W, 3) BGR
            mask: قناع (اختياري) لتحديد البكسلات
            use_median: استخدام الوسيط (أفضل ضد الضوضاء)

        Returns:
            (B, G, R) أو None
        """
        if region.size == 0:
            return None

        # استخرج البكسلات
        if mask is not None:
            pixels = region[mask > 0]
        else:
            pixels = region.reshape(-1, 3)

        if len(pixels) == 0:
            return None

        # احسب السائد
        if use_median:
            color = np.median(pixels, axis=0)
        else:
            color = np.mean(pixels, axis=0)

        return tuple(int(c) for c in color)

    def dominant_colors(
        self,
        region: np.ndarray,
        n: int = 3,
    ) -> List[Tuple[Tuple[int, int, int], float]]:
        """
        أكثر n ألوان شيوعاً في منطقة

        Returns:
            [(color, ratio), ...]
        """
        if region.size == 0:
            return []

        # استخدم K-means لتجميع الألوان
        pixels = region.reshape(-1, 3).astype(np.float32)

        if len(pixels) < n:
            # ألوان قليلة، نأخذ كل واحد
            unique = np.unique(pixels, axis=0)
            return [(tuple(int(c) for c in col), 1.0 / len(unique)) for col in unique]

        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
        _, labels, centers = cv2.kmeans(
            pixels, n, None, criteria, 3, cv2.KMEANS_PP_CENTERS
        )

        # احسب النسب
        counts = Counter(labels.flatten())
        total = len(labels)

        results = []
        for i in range(n):
            color = tuple(int(c) for c in centers[i])
            ratio = counts.get(i, 0) / total
            results.append((color, ratio))

        # رتب حسب النسبة
        results.sort(key=lambda x: x[1], reverse=True)
        return results

    # ========================================================
    # أدوات إضافية
    # ========================================================

    def get_color_name_bgr(self, bgr: Tuple[int, int, int]) -> str:
        """اسم اللون التقريبي بالعربية"""
        name_en = self.classify(bgr) or "unknown"

        translations = {
            "red": "أحمر",
            "orange": "برتقالي",
            "yellow": "أصفر",
            "green": "أخضر",
            "cyan": "سماوي",
            "blue": "أزرق",
            "purple": "بنفسجي",
            "pink": "وردي",
            "white": "أبيض",
            "black": "أسود",
            "gray": "رمادي",
            "unknown": "غير معروف",
        }

        return translations.get(name_en, name_en)

    def show_color(self, name: str, height: int = 100, width: int = 200) -> Optional[np.ndarray]:
        """
        إنشاء صورة تعرض اللون (للتشخيص)

        Args:
            name: اسم اللون
            height, width: أبعاد الصورة

        Returns:
            صورة BGR أو None
        """
        if name not in NAMED_COLORS_BGR:
            return None

        color = NAMED_COLORS_BGR[name]
        img = np.full((height, width, 3), color, dtype=np.uint8)

        # أضف نصاً
        cv2.putText(
            img, name.upper(),
            (20, height // 2 + 10),
            cv2.FONT_HERSHEY_SIMPLEX, 1.0,
            (255, 255, 255) if sum(color) < 400 else (0, 0, 0),
            2,
        )

        return img

    def create_color_palette(self, colors: List[Tuple[int, int, int]]) -> np.ndarray:
        """
        إنشاء شريط من الألوان (للتشخيص)

        Args:
            colors: قائمة (B, G, R)

        Returns:
            صورة تحتوي على شريط الألوان
        """
        n = len(colors)
        if n == 0:
            return np.zeros((100, 1, 3), dtype=np.uint8)

        cell_w = 100
        height = 100
        palette = np.zeros((height, n * cell_w, 3), dtype=np.uint8)

        for i, color in enumerate(colors):
            palette[:, i * cell_w:(i + 1) * cell_w] = color

        return palette

    # ========================================================
    # تحليل منطقة
    # ========================================================

    def analyze_region(self, region: np.ndarray) -> Dict:
        """
        تحليل مفصل لمنطقة ألوان

        Returns:
            dict مع:
              - mean: متوسط اللون
              - median: وسيط اللون
              - dominant: اللون السائد
              - name: اسم اللون
              - brightness: الإضاءة
              - saturation: التشبع
        """
        if region.size == 0:
            return {}

        mean_color = np.mean(region.reshape(-1, 3), axis=0).astype(int)
        median_color = np.median(region.reshape(-1, 3), axis=0).astype(int)

        b, g, r = int(median_color[0]), int(median_color[1]), int(median_color[2])
        h, s, v = self.bgr_to_hsv((b, g, r))

        return {
            "mean": tuple(int(c) for c in mean_color),
            "median": tuple(int(c) for c in median_color),
            "hsv": (h, s, v),
            "name": self.classify((b, g, r)),
            "name_ar": self.get_color_name_bgr((b, g, r)),
            "brightness": v,
            "saturation": s,
            "hue": h,
        }


# ============================================================
# دوال مستقلة (بدون كلاس)
# ============================================================

def bgr_to_hsv(bgr):
    """تحويل BGR → HSV (دالة سريعة)"""
    return ColorUtils.bgr_to_hsv(bgr)


def classify_color(bgr):
    """تصنيف لون (دالة سريعة)"""
    return ColorUtils().classify(bgr)


def color_distance(c1, c2):
    """مسافة بين لونين"""
    return ColorUtils.color_distance(c1, c2)


# ============================================================
# اختبار سريع
# ============================================================

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from utils.logger import setup_logger, log_section

    setup_logger(level="INFO")
    log_section("اختبار Color Utils")

    cu = ColorUtils()

    # ============================================================
    # 1) التحويلات
    # ============================================================
    print("\n🔄 اختبار التحويلات:")
    bgr = (0, 0, 255)  # أحمر
    hsv = cu.bgr_to_hsv(bgr)
    print(f"   BGR {bgr} → HSV {hsv}")
    print(f"   HSV {hsv} → BGR {cu.hsv_to_bgr(hsv)}")

    rgb = cu.bgr_to_rgb(bgr)
    print(f"   BGR {bgr} → RGB {rgb}")
    print(f"   RGB {rgb} → BGR {cu.rgb_to_bgr(rgb)}")

    # ============================================================
    # 2) تصنيف الألوان
    # ============================================================
    print("\n🎨 تصنيف الألوان:")
    test_colors = [
        ((0, 0, 255), "أحمر صريح"),
        ((0, 255, 0), "أخضر صريح"),
        ((255, 0, 0), "أزرق صريح"),
        ((0, 255, 255), "أصفر"),
        ((255, 255, 255), "أبيض"),
        ((128, 128, 128), "رمادي"),
    ]

    for bgr, label in test_colors:
        name = cu.classify(bgr)
        name_ar = cu.get_color_name_bgr(bgr)
        print(f"   {label:15} → {name} ({name_ar})")

    # ============================================================
    # 3) مقارنة الألوان
    # ============================================================
    print("\n📏 مقارنة الألوان:")
    c1 = (0, 0, 255)   # أحمر
    c2 = (0, 0, 200)   # أحمر داكن
    c3 = (255, 0, 0)   # أزرق

    print(f"   {c1} vs {c2}: مسافة = {cu.color_distance(c1, c2):.1f}")
    print(f"   {c1} vs {c3}: مسافة = {cu.color_distance(c1, c3):.1f}")
    print(f"   متشابهان (c1, c2)? {cu.is_similar(c1, c2, threshold=100)}")
    print(f"   متشابهان (c1, c3)? {cu.is_similar(c1, c3, threshold=100)}")

    # ============================================================
    # 4) تحليل منطقة
    # ============================================================
    print("\n🔍 تحليل منطقة:")
    region = np.zeros((50, 50, 3), dtype=np.uint8)
    region[:] = (0, 0, 255)  # أحمر
    region[20:30, 20:30] = (0, 255, 0)  # مربع أخضر

    analysis = cu.analyze_region(region)
    for k, v in analysis.items():
        print(f"   {k}: {v}")

    # ============================================================
    # 5) الألوان السائدة
    # ============================================================
    print("\n🌈 الألوان السائدة في المنطقة:")
    dominant = cu.dominant_colors(region, n=3)
    for color, ratio in dominant:
        name = cu.classify(color)
        print(f"   {color} - {name} ({ratio * 100:.1f}%)")

    # ============================================================
    # 6) رسم ألوان (اختياري)
    # ============================================================
    print("\n🎨 اختبار عرض الألوان:")
    palette_colors = [
        (0, 0, 255),      # أحمر
        (0, 165, 255),    # برتقالي
        (0, 255, 255),    # أصفر
        (0, 255, 0),      # أخضر
        (255, 255, 0),    # سماوي
        (255, 0, 0),      # أزرق
    ]

    palette = cu.create_color_palette(palette_colors)
    print(f"   ✅ شريط الألوان: {palette.shape}")

    log_section("انتهى الاختبار بنجاح", char="-")