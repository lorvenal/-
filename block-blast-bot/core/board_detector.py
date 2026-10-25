"""
Block Blast Bot - Board Detector
==================================
كشف شبكة اللوحة 8×8 وتحديد حالة كل خلية (فارغة/ملونة)
"""

import sys
from pathlib import Path
from typing import Optional, List, Tuple

import cv2
import numpy as np

from loguru import logger

try:
    from config import (
        BOARD_CONFIG, COLOR_CONFIG, DEBUG_CONFIG, DEBUG_DIR,
        get_board_cell_center,
    )
except ImportError:
    BOARD_CONFIG = {
        "rows": 8, "cols": 8,
        "x_start": 100, "y_start": 1100, "cell_size": 100,
    }
    COLOR_CONFIG = {"colors": {}, "empty_cell_brightness_threshold": 60}
    DEBUG_CONFIG = {"draw_board_grid": True}
    DEBUG_DIR = Path(__file__).parent.parent / "debug"
    def get_board_cell_center(r, c):
        return (100 + c * 100 + 50, 1100 + r * 100 + 50)


# ============================================================
# ثوابت
# ============================================================

EMPTY = 0
FILLED = 1


# ============================================================
# كلاس كشف اللوحة
# ============================================================

class BoardDetector:
    """كشف حالة اللوحة 8×8 من صورة الشاشة"""

    def __init__(self):
        self.rows = BOARD_CONFIG["rows"]
        self.cols = BOARD_CONFIG["cols"]
        self.cell_size = BOARD_CONFIG["cell_size"]
        self.x_start = BOARD_CONFIG["x_start"]
        self.y_start = BOARD_CONFIG["y_start"]

        # حدود فارغة
        self.empty_threshold = COLOR_CONFIG.get(
            "empty_cell_brightness_threshold", 60
        )

        # تخزين مؤقت
        self._last_board: Optional[np.ndarray] = None
        self._last_colors: Optional[np.ndarray] = None

        logger.debug(
            f"🔍 BoardDetector جاهز — {self.rows}×{self.cols}, "
            f"cell={self.cell_size}px, "
            f"start=({self.x_start},{self.y_start})"
        )

    # ========================================================
    # الواجهة الرئيسية
    # ========================================================

    def detect(self, frame: np.ndarray) -> np.ndarray:
        """
        كشف حالة اللوحة من صورة الشاشة

        Args:
            frame: صورة OpenCV من الشاشة

        Returns:
            numpy array بحجم (8, 8):
              - 0 = خلية فارغة
              - 1 = خلية ملونة
        """
        board = np.zeros((self.rows, self.cols), dtype=np.uint8)
        colors = np.full((self.rows, self.cols, 3), -1, dtype=np.int16)

        for r in range(self.rows):
            for c in range(self.cols):
                cx, cy = self._cell_center(r, c)
                color = self._sample_cell_color(frame, cx, cy)

                if color is None:
                    continue

                # هل الخلية ملونة؟
                is_filled = self._is_filled(color)

                board[r, c] = FILLED if is_filled else EMPTY
                if is_filled:
                    colors[r, c] = color

        self._last_board = board
        self._last_colors = colors

        filled_count = int(np.sum(board))
        logger.debug(
            f"🔍 اللوحة: {filled_count}/{self.rows * self.cols} خلية ملونة"
        )

        return board

    def detect_with_colors(self, frame: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        كشف حالة اللوحة + ألوان الخلايا

        Returns:
            (board, colors):
              board: (8, 8) — 0/1
              colors: (8, 8, 3) — BGR color أو -1 للفارغة
        """
        board = self.detect(frame)
        return board, self._last_colors

    # ========================================================
    # حساب إحداثيات الخلية
    # ========================================================

    def _cell_center(self, row: int, col: int) -> Tuple[int, int]:
        """مركز الخلية (row, col) بالبكسل"""
        x = self.x_start + col * self.cell_size
        y = self.y_start + row * self.cell_size
        return x, y

    def _cell_bbox(self, row: int, col: int) -> Tuple[int, int, int, int]:
        """حدود الخلية (x1, y1, x2, y2) بالبكسل"""
        cx, cy = self._cell_center(row, col)
        half = self.cell_size // 2
        return (cx - half, cy - half, cx + half, cy + half)

    # ========================================================
    # أخذ عيّنة لون
    # ========================================================

    def _sample_cell_color(
        self,
        frame: np.ndarray,
        cx: int, cy: int,
    ) -> Optional[np.ndarray]:
        """
        أخذ عينة لون من مركز الخلية
        يستخدم منطقة صغيرة (patch) لتقليل الضوضاء
        """
        h, w = frame.shape[:2]

        # patch بحجم 40% من الخلية
        patch_size = max(6, int(self.cell_size * 0.4))
        half = patch_size // 2

        x1, y1 = cx - half, cy - half
        x2, y2 = cx + half, cy + half

        # التحقق من الحدود
        if x1 < 0 or y1 < 0 or x2 >= w or y2 >= h:
            logger.trace(f"⚠️  خلية خارج الحدود: ({cx},{cy})")
            return None

        patch = frame[y1:y2, x1:x2]
        if patch.size == 0:
            return None

        # متوسط اللون (median أفضل من mean لمقاومة الضوضاء)
        median_color = np.median(patch.reshape(-1, 3), axis=0)
        return median_color.astype(np.int16)

    # ========================================================
    # فحص هل الخلية ملونة
    # ========================================================

    def _is_filled(self, color: np.ndarray) -> bool:
        """
        هل الخلية ملونة (= قطعة موجودة)؟

        المنطق:
        - الخلية الفارغة: رمادية داكنة (تشبع منخفض + إضاءة منخفضة)
        - الخلية الملونة: ألوان زاهية (تشبع عالٍ)
        """
        b, g, r = int(color[0]), int(color[1]), int(color[2])

        # تحويل BGR → HSV
        pixel = np.uint8([[[b, g, r]]])
        hsv = cv2.cvtColor(pixel, cv2.COLOR_BGR2HSV)
        h, s, v = int(hsv[0, 0, 0]), int(hsv[0, 0, 1]), int(hsv[0, 0, 2])

        # الحكم:
        # 1) تشبع عالٍ (> 80) → ملونة
        # 2) إضاءة عالية (> 180) → قد تكون بيضاء/فاتحة
        # 3) كلاهما منخفض → فارغة (رمادية داكنة)

        if s > 80 and v > 60:
            return True

        if v > 180:
            return True

        return False

    # ========================================================
    # تصنيف اللون
    # ========================================================

    def classify_color(self, color: np.ndarray) -> Optional[str]:
        """تصنيف اللون إلى اسم (red, blue, green, ...)"""
        if color is None:
            return None

        b, g, r = int(color[0]), int(color[1]), int(color[2])
        pixel = np.uint8([[[b, g, r]]])
        hsv = cv2.cvtColor(pixel, cv2.COLOR_BGR2HSV)
        h = int(hsv[0, 0, 0])

        colors = COLOR_CONFIG.get("colors", {})
        if not colors:
            colors = {
                "red":    {"h_min": 0,   "h_max": 10},
                "orange": {"h_min": 11,  "h_max": 22},
                "yellow": {"h_min": 23,  "h_max": 35},
                "green":  {"h_min": 36,  "h_max": 85},
                "cyan":   {"h_min": 86,  "h_max": 100},
                "blue":   {"h_min": 101, "h_max": 130},
                "purple": {"h_min": 131, "h_max": 160},
                "pink":   {"h_min": 161, "h_max": 179},
            }

        for name, rng in colors.items():
            if isinstance(rng, dict):
                h_min = rng.get("h_min", 0)
                h_max = rng.get("h_max", 179)
            else:
                h_min, h_max = rng

            if h_min <= h <= h_max:
                return name

        return None

    def get_color_name(self, row: int, col: int) -> Optional[str]:
        """اسم لون الخلية (row, col)"""
        if self._last_colors is None:
            return None
        color = self._last_colors[row, col]
        if color[0] < 0:  # فارغة
            return None
        return self.classify_color(color)

    # ========================================================
    # أدوات مساعدة
    # ========================================================

    def count_filled(self) -> int:
        """عدد الخلايا الممتلئة في آخر كشف"""
        if self._last_board is None:
            return 0
        return int(np.sum(self._last_board))

    def is_empty(self) -> bool:
        """هل اللوحة فارغة تماماً؟"""
        return self.count_filled() == 0

    def get_empty_cells(self) -> List[Tuple[int, int]]:
        """قائمة الخلايا الفارغة (row, col)"""
        if self._last_board is None:
            return []
        positions = np.argwhere(self._last_board == EMPTY)
        return [tuple(p) for p in positions]

    def get_filled_cells(self) -> List[Tuple[int, int]]:
        """قائمة الخلايا الممتلئة (row, col)"""
        if self._last_board is None:
            return []
        positions = np.argwhere(self._last_board == FILLED)
        return [tuple(p) for p in positions]

    # ========================================================
    # الرسم للتشخيص
    # ========================================================

    def draw(
        self,
        frame: np.ndarray,
        board: Optional[np.ndarray] = None,
        show_colors: bool = True,
        show_indices: bool = False,
    ) -> np.ndarray:
        """
        رسم شبكة اللوحة + حالة كل خلية على الصورة

        Args:
            frame: الصورة الأصلية
            board: مصفوفة الحالة
            show_colors: عرض ألوان الخلايا الممتلئة
            show_indices: عرض أرقام الصفوف والأعمدة

        Returns:
            صورة مرسومة
        """
        canvas = frame.copy()
        if board is None:
            board = self._last_board
        if board is None:
            return canvas

        for r in range(self.rows):
            for c in range(self.cols):
                x1, y1, x2, y2 = self._cell_bbox(r, c)
                is_filled = board[r, c] == FILLED

                # لون الإطار
                if is_filled:
                    color = (0, 0, 255)  # أحمر
                    thickness = 2
                else:
                    color = (0, 255, 0)  # أخضر
                    thickness = 1

                cv2.rectangle(canvas, (x1, y1), (x2, y2), color, thickness)

                # علامة · للفارغة
                if not is_filled:
                    cx, cy = self._cell_center(r, c)
                    cv2.putText(
                        canvas, "·",
                        (cx - 5, cy + 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                        (100, 100, 100), 1,
                    )

                # أرقام الصفوف والأعمدة
                if show_indices:
                    cx, cy = self._cell_center(r, c)
                    cv2.putText(
                        canvas, f"{r},{c}",
                        (cx - 15, cy - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.3,
                        (255, 255, 255), 1,
                    )

        # معلومات إحصائية
        filled = int(np.sum(board))
        info = f"Filled: {filled}/{self.rows * self.cols}"
        cv2.putText(
            canvas, info,
            (self.x_start, self.y_start - 20),
            cv2.FONT_HERSHEY_SIMPLEX, 0.7,
            (0, 255, 255), 2,
        )

        return canvas

    # ========================================================
    # ملخص
    # ========================================================

    def summary(self) -> str:
        """ملخص نصي للوحة"""
        if self._last_board is None:
            return "لم يتم الكشف بعد"

        filled = self.count_filled()
        empty = self.rows * self.cols - filled

        lines = [
            f"Board {self.rows}x{self.cols} | filled={filled} empty={empty}",
        ]

        # تمثيل نصي للوحة
        for r in range(self.rows):
            row = ""
            for c in range(self.cols):
                row += "█ " if self._last_board[r, c] else "· "
            lines.append(f"  {row}")

        return "\n".join(lines)


# ============================================================
# اختبار سريع
# ============================================================

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from utils.logger import setup_logger, log_section

    setup_logger(level="DEBUG")
    log_section("اختبار Board Detector")

    try:
        from core.adb_controller import ADBController
        from core.screen_capture import ScreenCapture

        # الاتصال
        adb = ADBController()
        if not adb.is_connected():
            logger.error("❌ لا يوجد هاتف متصل!")
            raise SystemExit(1)

        logger.success("✅ الهاتف متصل")

        # التقاط صورة
        capture = ScreenCapture(adb)
        frame = capture.grab()
        if frame is None:
            logger.error("❌ فشل التقاط الشاشة")
            raise SystemExit(1)

        logger.success(f"✅ تم التقاط الصورة: {frame.shape}")

        # الكشف
        detector = BoardDetector()
        logger.info(
            f"📐 إعدادات اللوحة: "
            f"start=({detector.x_start},{detector.y_start}), "
            f"cell={detector.cell_size}"
        )

        board = detector.detect(frame)

        # الملخص
        print("\n" + detector.summary())
        print(f"\nالخلايا الممتلئة: {detector.count_filled()}")
        print(f"الخلايا الفارغة: {len(detector.get_empty_cells())}")

        # حفظ صورة مرسومة
        drawn = detector.draw(frame, board, show_indices=False)
        out_path = DEBUG_DIR / "board_detection.png"
        cv2.imwrite(str(out_path), drawn)
        logger.success(f"💾 تم حفظ صورة التشخيص: {out_path}")

        # عرض الصورة
        try:
            h, w = drawn.shape[:2]
            scale = min(600 / h, 400 / w)
            small = cv2.resize(drawn, (int(w * scale), int(h * scale)))

            cv2.imshow("Board Detection", small)
            logger.info("👁️  اضغط أي مفتاح في نافذة العرض للإغلاق")
            cv2.waitKey(0)
            cv2.destroyAllWindows()
        except Exception as e:
            logger.debug(f"لا يمكن عرض النافذة: {e}")

        log_section("انتهى الاختبار بنجاح", char="-")

    except KeyboardInterrupt:
        logger.info("\n⏹️  تم الإلغاء")
    except Exception as e:
        logger.exception(f"❌ خطأ: {e}")