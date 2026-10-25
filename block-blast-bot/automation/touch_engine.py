"""
Block Blast Bot - Touch Engine
================================
تحويل حركة (Move) إلى سحب فعلي على شاشة الهاتف

المشكلة:
- Move يعطينا موضع القطعة في اللوحة (row, col)
- لكن في اللعبة، نسحب من التقطعة في Tray إلى الموقع على اللوحة

الحل:
1. احسب مركز البداية (Tray)
2. احسب مركز النهاية (اللوحة)
3. نفّذ swipe بينهما
"""

import sys
import time
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
from loguru import logger

try:
    from config import (
        BOARD_CONFIG, TRAY_CONFIG, ADB_CONFIG,
        get_board_cell_center, get_slot_center,
    )
    from core.game_state import Move
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from config import (
        BOARD_CONFIG, TRAY_CONFIG, ADB_CONFIG,
        get_board_cell_center, get_slot_center,
    )
    from core.game_state import Move


# ============================================================
# كلاس محرك اللمس
# ============================================================

class TouchEngine:
    """تنفيذ الحركات على شاشة الهاتف"""

    def __init__(self, adb_controller):
        """
        Args:
            adb_controller: نسخة ADBController
        """
        self.adb = adb_controller

        # إعدادات
        self.cell_size = BOARD_CONFIG["cell_size"]
        self.mini_cell = TRAY_CONFIG.get("mini_cell_size", 60)
        self.swipe_duration = ADB_CONFIG.get("swipe_duration", 350)

        # إحصائيات
        self._last_move: Optional[Move] = None
        self._last_swipe_ms = 0.0

        logger.debug(
            f"👆 TouchEngine جاهز — "
            f"cell={self.cell_size}, mini={self.mini_cell}, "
            f"swipe={self.swipe_duration}ms"
        )

    # ========================================================
    # الواجهة الرئيسية
    # ========================================================

    def execute(self, move: Move, verify: bool = False) -> bool:
        """
        تنفيذ حركة على الهاتف

        Args:
            move: الحركة
            verify: التحقق بعد التنفيذ (يحتاج screen_capture)

        Returns:
            True إن نجح التنفيذ
        """
        start = time.perf_counter()

        # 1) حساب نقطة البداية (Tray)
        start_point = self._get_start_point(move)
        if start_point is None:
            logger.error(f"❌ لا يمكن حساب نقطة البداية: {move}")
            return False

        # 2) حساب نقطة النهاية (اللوحة)
        end_point = self._get_end_point(move)
        if end_point is None:
            logger.error(f"❌ لا يمكن حساب نقطة النهاية: {move}")
            return False

        # 3) تنفيذ السحب
        logger.info(
            f"👆 تنفيذ حركة: slot={move.slot_index} "
            f"rot={move.rotation} pos=({move.row},{move.col})"
        )
        logger.debug(
            f"   من {start_point} → إلى {end_point} "
            f"({self.swipe_duration}ms)"
        )

        success = self._perform_swipe(start_point, end_point)

        elapsed_ms = (time.perf_counter() - start) * 1000
        self._last_swipe_ms = elapsed_ms
        self._last_move = move

        if success:
            logger.success(f"✅ تم التنفيذ في {elapsed_ms:.0f}ms")
        else:
            logger.error(f"❌ فشل التنفيذ")

        # 4) تحقق (اختياري)
        if verify and success:
            time.sleep(0.2)
            # يمكن إضافة تحقق لاحقاً

        return success

    # ========================================================
    # حساب الإحداثيات
    # ========================================================

    def _get_start_point(self, move: Move) -> Optional[Tuple[int, int]]:
        """
        نقطة البداية = مركز القطعة في Tray

        ملاحظة: نحتاج للنقطة المناسبة للقبض على القطعة
        عادةً = مركز القطعة في Tray
        """
        try:
            x, y = get_slot_center(move.slot_index)
            return int(x), int(y)
        except (IndexError, KeyError) as e:
            logger.error(f"خطأ في إحداثيات Slot: {e}")
            return None

    def _get_end_point(self, move: Move) -> Optional[Tuple[int, int]]:
        """
        نقطة النهاية = مركز "قلب" القطعة على اللوحة

        الحساب:
        1. shape بعد الدوران
        2. مركز الشكل (متوسط الخلايا الممتلئة)
        3. تحويل إلى إحداثيات بكسل
        """
        shape = move.get_rotated_shape()
        h, w = shape.shape

        # متوسط مواضع الخلايا الممتلئة داخل الـ shape
        # (مركز "ثقالة" القطعة)
        filled = np.argwhere(shape == 1)
        if filled.size == 0:
            return None

        # متوسط (r, c) للخلايا الممتلئة
        mean_r = float(np.mean(filled[:, 0]))
        mean_c = float(np.mean(filled[:, 1]))

        # الموضع المطلق على اللوحة
        abs_row = move.row + mean_r
        abs_col = move.col + mean_c

        # تحويل إلى بكسل
        x = BOARD_CONFIG["x_start"] + abs_col * self.cell_size
        y = BOARD_CONFIG["y_start"] + abs_row * self.cell_size

        return int(round(x)), int(round(y))

    def _get_bbox_center(self, move: Move) -> Optional[Tuple[int, int]]:
        """
        (بديل) مركز bounding box للقطعة على اللوحة
        """
        shape = move.get_rotated_shape()
        h, w = shape.shape

        # مركز bbox
        center_r = move.row + (h - 1) / 2
        center_c = move.col + (w - 1) / 2

        x = BOARD_CONFIG["x_start"] + center_c * self.cell_size
        y = BOARD_CONFIG["y_start"] + center_r * self.cell_size

        return int(round(x)), int(round(y))

    # ========================================================
    # تنفيذ السحب
    # ========================================================

    def _perform_swipe(
        self,
        start: Tuple[int, int],
        end: Tuple[int, int],
    ) -> bool:
        """
        تنفيذ السحب الفعلي

        في Block Blast، تحتاج:
        1. لمس القطعة في Tray (بدون رفع الإصبع)
        2. سحبها إلى موقعها
        3. رفع الإصبع
        """
        x1, y1 = start
        x2, y2 = end

        try:
            # ADB swipe يقوم بكل شيء: لمس + سحب + رفع
            self.adb.swipe(
                x1, y1,
                x2, y2,
                duration=self.swipe_duration,
            )
            return True
        except Exception as e:
            logger.exception(f"❌ فشل السحب: {e}")
            return False

    # ========================================================
    # تحقق (بعد التنفيذ)
    # ========================================================

    def verify_move(
        self,
        move: Move,
        screen_capture,
        board_detector,
        tolerance: int = 2,
    ) -> bool:
        """
        التحقق من أن الحركة نُفّذت فعلاً

        المنطق:
        - اقرأ اللوحة بعد الحركة
        - تحقق من أن الخلايا المتوقعة أصبحت ممتلئة (أو ممسوحة)

        Args:
            tolerance: عدد الخلايا المسموح اختلافها
        """
        frame = screen_capture.grab()
        if frame is None:
            return False

        new_board = board_detector.detect(frame)

        # الخلايا المتوقعة أن تكون ممتلئة (قبل المسح)
        expected_filled = set(move.get_cells())

        # الخلايا الممتلئة الجديدة
        actual_filled = set()
        for r, c in expected_filled:
            if 0 <= r < 8 and 0 <= c < 8:
                if new_board[r, c] == 1:
                    actual_filled.add((r, c))

        # نسبة النجاح
        if not expected_filled:
            return False

        match_ratio = len(actual_filled) / len(expected_filled)

        # لكن قد تكون بعض الخلايا ممسوحة فوراً (لو أكملت خطاً)
        if match_ratio < 0.3:
            logger.warning(
                f"⚠️  التحقق: فقط {match_ratio * 100:.0f}% من الخلايا مطابقة"
            )
            return False

        logger.debug(f"✓ تحقق: {match_ratio * 100:.0f}% مطابقة")
        return True

    # ========================================================
    # عمليات لمس إضافية
    # ========================================================

    def tap_board(self, row: int, col: int):
        """نقرة على خلية في اللوحة"""
        x, y = get_board_cell_center(row, col)
        self.adb.tap(x, y)

    def tap_slot(self, slot_index: int):
        """نقرة على قطعة في Tray"""
        x, y = get_slot_center(slot_index)
        self.adb.tap(x, y)

    def drag_block(
        self,
        slot_index: int,
        row: int,
        col: int,
        rotation: int = 0,
    ):
        """
        سحب قطعة من Tray إلى اللوحة (بدون Move object)
        """
        # حساب نقطة البداية
        sx, sy = get_slot_center(slot_index)

        # حساب نقطة النهاية
        ex = BOARD_CONFIG["x_start"] + col * self.cell_size
        ey = BOARD_CONFIG["y_start"] + row * self.cell_size

        self.adb.swipe(sx, sy, ex, ey, duration=self.swipe_duration)

    # ========================================================
    # ضبط ديناميكي
    # ========================================================

    def set_swipe_duration(self, ms: int):
        """ضبط مدة السحب (أطول = أدق لكن أبطأ)"""
        self.swipe_duration = ms
        logger.info(f"⚙️  مدة السحب: {ms}ms")

    def calibrate_offset(
        self,
        offset_x: int = 0,
        offset_y: int = 0,
    ):
        """
        ضبط offset إن كانت القطع تُوضع في مكان خاطئ باستمرار

        Args:
            offset_x: إزاحة أفقية (+ لليمين)
            offset_y: إزاحة رأسية (+ للأسفل)
        """
        self.offset_x = offset_x
        self.offset_y = offset_y
        logger.info(f"⚙️  Offset: ({offset_x}, {offset_y})")

    # ========================================================
    # إحصائيات
    # ========================================================

    def stats(self) -> dict:
        """إحصائيات آخر تنفيذ"""
        return {
            "last_move": str(self._last_move) if self._last_move else None,
            "swipe_ms": round(self._last_swipe_ms, 1),
            "duration_setting": self.swipe_duration,
        }


# ============================================================
# اختبار سريع
# ============================================================

if __name__ == "__main__":
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).parent.parent))
    from utils.logger import setup_logger, log_section
    from core.adb_controller import ADBController
    setup_logger(level="DEBUG")
    log_section("اختبار Touch Engine")
    try:
        adb = ADBController()
        if not adb.is_connected():
            logger.error("لا يوجد هاتف متصل")
            raise SystemExit(1)
        logger.success("تم الاتصال")
        engine = TouchEngine(adb)
        print("TouchEngine جاهز")
        print(engine.stats())
    except Exception as e:
        logger.exception(f"خطأ: {e}")
