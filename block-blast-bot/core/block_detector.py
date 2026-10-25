"""
Block Blast Bot - Block Detector
==================================
كشف القطع الثلاث المتاحة في الأسفل (Tray)
يحدد: شكل كل قطعة، لونها، وأبعادها
"""

import sys
from pathlib import Path
from typing import Optional, List, Tuple
from dataclasses import dataclass, field

import cv2
import numpy as np

from loguru import logger

try:
    from config import (
        TRAY_CONFIG, BOARD_CONFIG, COLOR_CONFIG, DEBUG_DIR,
        get_slot_center,
    )
except ImportError:
    TRAY_CONFIG = {
        "slots": 3,
        "slot_positions": [(250, 1900), (540, 1900), (830, 1900)],
        "mini_cell_size": 60,
    }
    BOARD_CONFIG = {"cell_size": 100}
    COLOR_CONFIG = {"colors": {}}
    DEBUG_DIR = Path(__file__).parent.parent / "debug"
    def get_slot_center(i):
        return TRAY_CONFIG["slot_positions"][i]


# ============================================================
# تمثيل القطعة
# ============================================================

@dataclass
class Block:
    """
    تمثيل قطعة واحدة

    Attributes:
        shape: مصفوفة ثنائية الأبعاد (n×m) — 1 = خلية، 0 = فراغ
               مثال L-shape:
                   [[1, 0],
                    [1, 0],
                    [1, 1]]
        color: BGR color (متوسط لون القطعة)
        color_name: اسم اللون (red, blue, ...)
        slot_index: 0/1/2 (مكانها في الأسفل)
        bbox: (x, y, w, h) موقعها في الصورة
    """
    shape: np.ndarray
    color: Optional[np.ndarray] = None
    color_name: Optional[str] = None
    slot_index: int = -1
    bbox: Tuple[int, int, int, int] = (0, 0, 0, 0)

    @property
    def height(self) -> int:
        return self.shape.shape[0]

    @property
    def width(self) -> int:
        return self.shape.shape[1]

    @property
    def num_cells(self) -> int:
        return int(np.sum(self.shape))

    def get_cells(self) -> List[Tuple[int, int]]:
        """قائمة الخلايا النسبية [(r, c), ...]"""
        return [tuple(p) for p in np.argwhere(self.shape == 1)]

    def rotate(self, times: int = 1) -> "Block":
        """إرجاع نسخة مُدوّرة (90° × times)"""
        new_shape = np.rot90(self.shape, k=times)
        return Block(
            shape=new_shape,
            color=self.color,
            color_name=self.color_name,
            slot_index=self.slot_index,
            bbox=self.bbox,
        )

    def get_all_rotations(self) -> List["Block"]:
        """كل الدورانات الفريدة (بدون تكرار)"""
        rotations = []
        seen = set()
        for k in range(4):
            rot = self.rotate(k)
            key = (rot.height, rot.width, tuple(rot.shape.flatten()))
            if key not in seen:
                seen.add(key)
                rotations.append(rot)
        return rotations

    def __repr__(self) -> str:
        return (
            f"Block(slot={self.slot_index}, "
            f"shape={self.height}x{self.width}, "
            f"cells={self.num_cells}, "
            f"color={self.color_name})"
        )

    def visualize(self) -> str:
        """تمثيل نصي للقطعة"""
        lines = []
        for row in self.shape:
            lines.append("".join("█ " if v else "· " for v in row))
        return "\n".join(lines)


# ============================================================
# كلاس كشف القطع
# ============================================================

class BlockDetector:
    """كشف القطع الثلاث من منطقة Tray في الأسفل"""

    def __init__(self):
        self.slots = TRAY_CONFIG["slots"]
        self.slot_positions = TRAY_CONFIG["slot_positions"]
        self.mini_cell = TRAY_CONFIG.get("mini_cell_size", 60)
        self.board_cell = BOARD_CONFIG["cell_size"]

        # آخر كشف
        self._last_blocks: List[Block] = []

        logger.debug(
            f"🔍 BlockDetector جاهز — {self.slots} slots, "
            f"mini_cell={self.mini_cell}px"
        )

    # ========================================================
    # الواجهة الرئيسية
    # ========================================================

    def detect(self, frame: np.ndarray) -> List[Block]:
        """
        كشف القطع الثلاث

        Args:
            frame: صورة الشاشة

        Returns:
            قائمة بـ 3 Block objects (أو أقل إن فشل الكشف)
        """
        blocks = []

        for slot_idx in range(self.slots):
            try:
                block = self._detect_single_slot(frame, slot_idx)
                if block is not None:
                    blocks.append(block)
                else:
                    logger.warning(f"⚠️  فشل كشف القطعة في slot {slot_idx}")
            except Exception as e:
                logger.exception(f"❌ خطأ في slot {slot_idx}: {e}")

        self._last_blocks = blocks

        logger.debug(
            f"🔍 تم كشف {len(blocks)}/{self.slots} قطعة: "
            f"{[(b.height, b.width) for b in blocks]}"
        )

        return blocks

    # ========================================================
    # كشف قطعة واحدة
    # ========================================================

    def _detect_single_slot(
        self,
        frame: np.ndarray,
        slot_idx: int,
    ) -> Optional[Block]:
        """
        كشف القطعة في slot محدد

        الخطوات:
        1. أخذ منطقة حول مركز القطعة
        2. عزل الألوان الزاهية (القطعة)
        3. إيجاد أكبر مكون متصل
        4. حساب الـ bounding box
        5. تحويله إلى شبكة shape
        """
        cx, cy = self.slot_positions[slot_idx]

        # ============================================================
        # 1) أخذ منطقة حول القطعة
        # ============================================================
        region_size = int(self.board_cell * 5)  # منطقة كبيرة (5 خلايا)
        half = region_size // 2
        h, w = frame.shape[:2]

        x1 = max(0, cx - half)
        y1 = max(0, cy - half)
        x2 = min(w, cx + half)
        y2 = min(h, cy + half)

        region = frame[y1:y2, x1:x2]
        if region.size == 0:
            return None

        # ============================================================
        # 2) عزل القطعة (mask)
        # ============================================================
        mask = self._extract_colored_mask(region)
        if mask is None or np.sum(mask) < 100:
            logger.trace(f"Slot {slot_idx}: لا يوجد محتوى كافٍ")
            return None

        # ============================================================
        # 3) إيجاد أكبر مكون متصل
        # ============================================================
        contours, _ = cv2.findContours(
            mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        if not contours:
            return None

        # أكبر مكون حسب المساحة
        largest = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(largest)

        # تصفية: يجب أن تكون قطعة حقيقية (ليست ضوضاء)
        min_area = (self.mini_cell ** 2) * 0.5
        if area < min_area:
            logger.trace(
                f"Slot {slot_idx}: المساحة صغيرة ({area:.0f} < {min_area:.0f})"
            )
            return None

        # ============================================================
        # 4) الـ bounding box
        # ============================================================
        bx, by, bw, bh = cv2.boundingRect(largest)

        # ============================================================
        # 5) تحويل إلى shape (شبكة)
        # ============================================================
        shape = self._bbox_to_shape(mask, bx, by, bw, bh)

        if shape is None or np.sum(shape) == 0:
            logger.trace(f"Slot {slot_idx}: shape فارغ")
            return None

        # ============================================================
        # 6) لون القطعة
        # ============================================================
        color = self._average_color(region, mask, largest)
        color_name = self._classify_color(color) if color is not None else None

        # ============================================================
        # 7) بناء Block
        # ============================================================
        block = Block(
            shape=shape,
            color=color,
            color_name=color_name,
            slot_index=slot_idx,
            bbox=(x1 + bx, y1 + by, bw, bh),
        )

        logger.trace(
            f"Slot {slot_idx}: {block.height}x{block.width}, "
            f"cells={block.num_cells}, color={color_name}"
        )

        return block

    # ========================================================
    # عزل القطعة (mask)
    # ========================================================

    def _extract_colored_mask(self, region: np.ndarray) -> Optional[np.ndarray]:
        """
        إنشاء mask للقطعة (الألوان الزاهية فقط)

        المنطق:
        - الخلفية داكنة/رمادية
        - القطعة ملونة (تشبع عالٍ)
        """
        # تحويل HSV
        hsv = cv2.cvtColor(region, cv2.COLOR_BGR2HSV)

        # عتبة: تشبع عالٍ OR إضاءة عالية
        mask1 = cv2.inRange(hsv, (0, 60, 60), (179, 255, 255))
        mask2 = cv2.inRange(hsv, (0, 0, 200), (179, 60, 255))
        mask = cv2.bitwise_or(mask1, mask2)

        # تنظيف الضوضاء
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)

        return mask

    # ========================================================
    # تحويل bounding box → shape
    # ========================================================

    def _bbox_to_shape(
        self,
        mask: np.ndarray,
        bx: int, by: int, bw: int, bh: int,
    ) -> Optional[np.ndarray]:
        """
        تحويل منطقة من mask إلى مصفوفة shape
        """
        # قطع ROI من mask
        roi = mask[by:by + bh, bx:bx + bw]
        if roi.size == 0:
            return None

        # ============================================================
        # تحديد حجم القطعة بالخلايا (Grid size)
        # ============================================================
        grid_h = max(1, round(bh / self.mini_cell))
        grid_w = max(1, round(bw / self.mini_cell))

        # حدود معقولة: 1-5 خلايا
        grid_h = min(grid_h, 5)
        grid_w = min(grid_w, 5)

        # ============================================================
        # تقسيم ROI إلى شبكة grid_h × grid_w
        # ============================================================
        shape = np.zeros((grid_h, grid_w), dtype=np.uint8)

        cell_h = bh / grid_h
        cell_w = bw / grid_w

        for r in range(grid_h):
            for c in range(grid_w):
                # منطقة الخلية
                y_start = int(r * cell_h)
                y_end = int((r + 1) * cell_h)
                x_start = int(c * cell_w)
                x_end = int((c + 1) * cell_w)

                cell_region = roi[y_start:y_end, x_start:x_end]
                if cell_region.size == 0:
                    continue

                # نسبة البكسلات البيضاء
                fill_ratio = np.mean(cell_region > 0)

                # العتبة: 50%
                if fill_ratio > 0.5:
                    shape[r, c] = 1

        # التحقق: يجب أن يكون للقطعة خلايا
        if np.sum(shape) == 0:
            return None

        return shape

    # ========================================================
    # حساب لون القطعة
    # ========================================================

    def _average_color(
        self,
        region: np.ndarray,
        mask: np.ndarray,
        contour: np.ndarray,
    ) -> Optional[np.ndarray]:
        """متوسط لون القطعة (فقط داخل القناع)"""
        try:
            # قناع خاص للـ contour فقط
            contour_mask = np.zeros(mask.shape, dtype=np.uint8)
            cv2.drawContours(contour_mask, [contour], -1, 255, -1)

            # فقط البكسلات داخل القناع
            pixels = region[contour_mask > 0]
            if pixels.size == 0:
                return None

            median_color = np.median(pixels, axis=0).astype(np.int16)
            return median_color

        except Exception as e:
            logger.debug(f"خطأ في حساب اللون: {e}")
            return None

    def _classify_color(self, color: np.ndarray) -> Optional[str]:
        """تصنيف BGR → اسم اللون"""
        if color is None:
            return None

        b, g, r = int(color[0]), int(color[1]), int(color[2])
        pixel = np.uint8([[[b, g, r]]])
        hsv = cv2.cvtColor(pixel, cv2.COLOR_BGR2HSV)
        h = int(hsv[0, 0, 0])

        colors = COLOR_CONFIG.get("colors", {})
        if not colors:
            colors = {
                "red":    (0, 10),
                "orange": (11, 22),
                "yellow": (23, 35),
                "green":  (36, 85),
                "cyan":   (86, 100),
                "blue":   (101, 130),
                "purple": (131, 160),
                "pink":   (161, 179),
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

    # ========================================================
    # أدوات مساعدة
    # ========================================================

    def get_blocks(self) -> List[Block]:
        """آخر القطع المكتشفة"""
        return self._last_blocks

    def count(self) -> int:
        """عدد القطع في آخر كشف"""
        return len(self._last_blocks)

    def get_block_by_slot(self, slot_idx: int) -> Optional[Block]:
        """إرجاع القطعة في slot محدد"""
        for block in self._last_blocks:
            if block.slot_index == slot_idx:
                return block
        return None

    # ========================================================
    # الرسم للتشخيص
    # ========================================================

    def draw(
        self,
        frame: np.ndarray,
        blocks: Optional[List[Block]] = None,
    ) -> np.ndarray:
        """رسم القطع المكتشفة على الصورة"""
        canvas = frame.copy()
        if blocks is None:
            blocks = self._last_blocks

        # رسم مراكز slots
        for i, (cx, cy) in enumerate(self.slot_positions):
            cv2.circle(canvas, (cx, cy), 5, (255, 255, 255), -1)
            cv2.putText(
                canvas, f"S{i+1}",
                (cx - 15, cy - 40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                (255, 255, 255), 2,
            )

        # رسم كل قطعة
        for block in blocks:
            bx, by, bw, bh = block.bbox

            # إطار
            cv2.rectangle(
                canvas, (bx, by), (bx + bw, by + bh),
                (0, 255, 0), 2,
            )

            # معلومات
            info = f"{block.height}x{block.width} [{block.color_name or '?'}]"
            cv2.putText(
                canvas, info,
                (bx, by - 8),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                (0, 255, 255), 2,
            )

            # رسم شبكة القطعة
            self._draw_shape_grid(canvas, block, bx, by, bw, bh)

        return canvas

    def _draw_shape_grid(
        self,
        canvas: np.ndarray,
        block: Block,
        bx: int, by: int, bw: int, bh: int,
    ):
        """رسم شبكة القطعة داخلها"""
        cell_w = bw / block.width
        cell_h = bh / block.height

        for r in range(block.height):
            for c in range(block.width):
                x1 = int(bx + c * cell_w)
                y1 = int(by + r * cell_h)
                x2 = int(bx + (c + 1) * cell_w)
                y2 = int(by + (r + 1) * cell_h)

                if block.shape[r, c] == 1:
                    # خلية ممتلئة
                    cx = (x1 + x2) // 2
                    cy = (y1 + y2) // 2
                    cv2.circle(canvas, (cx, cy), 5, (0, 0, 255), -1)
                    cv2.rectangle(canvas, (x1, y1), (x2, y2), (0, 0, 255), 1)
                else:
                    # خلية فارغة
                    cv2.rectangle(canvas, (x1, y1), (x2, y2), (100, 100, 100), 1)

    # ========================================================
    # ملخص
    # ========================================================

    def summary(self) -> str:
        """ملخص نصي للقطع"""
        if not self._last_blocks:
            return "لم يتم كشف أي قطعة"

        lines = [f"Blocks: {len(self._last_blocks)}"]
        for block in self._last_blocks:
            lines.append(f"\n  Slot {block.slot_index + 1}: "
                         f"{block.height}x{block.width}, "
                         f"cells={block.num_cells}, "
                         f"color={block.color_name}")
            for row in block.shape:
                lines.append("    " + "".join("█ " if v else "· " for v in row))

        return "\n".join(lines)


# ============================================================
# اختبار سريع
# ============================================================

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from utils.logger import setup_logger, log_section

    setup_logger(level="DEBUG")
    log_section("اختبار Block Detector")

    try:
        from core.adb_controller import ADBController
        from core.screen_capture import ScreenCapture

        # الاتصال
        adb = ADBController()
        if not adb.is_connected():
            logger.error("❌ لا يوجد هاتف متصل!")
            raise SystemExit(1)

        logger.success("✅ الهاتف متصل")

        # التقاط
        capture = ScreenCapture(adb)
        frame = capture.grab()
        if frame is None:
            logger.error("❌ فشل التقاط الشاشة")
            raise SystemExit(1)

        logger.success(f"✅ الصورة: {frame.shape}")

        # الكشف
        detector = BlockDetector()
        blocks = detector.detect(frame)

        # الملخص
        print("\n" + "=" * 60)
        print(detector.summary())
        print("=" * 60)

        if not blocks:
            logger.warning("⚠️  لم يتم كشف أي قطعة!")
            logger.info("   تحقق من:")
            logger.info("   1. هل القطع ظاهرة في اللعبة؟")
            logger.info("   2. هل الإحداثيات في config صحيحة؟")
            logger.info("   3. جرّب رفع self.mini_cell قليلاً")

        # حفظ صورة التشخيص
        drawn = detector.draw(frame, blocks)
        out_path = DEBUG_DIR / "block_detection.png"
        cv2.imwrite(str(out_path), drawn)
        logger.success(f"💾 صورة التشخيص: {out_path}")

        # عرض النافذة
        try:
            h, w = drawn.shape[:2]
            scale = min(600 / h, 400 / w)
            small = cv2.resize(drawn, (int(w * scale), int(h * scale)))
            cv2.imshow("Block Detection", small)
            logger.info("👁️  اضغط أي مفتاح للإغلاق")
            cv2.waitKey(0)
            cv2.destroyAllWindows()
        except Exception as e:
            logger.debug(f"لا يمكن عرض النافذة: {e}")

        log_section("انتهى الاختبار بنجاح", char="-")

    except KeyboardInterrupt:
        logger.info("\n⏹️  تم الإلغاء")
    except Exception as e:
        logger.exception(f"❌ خطأ: {e}")