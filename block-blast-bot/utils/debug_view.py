"""
Block Blast Bot - Debug View
==============================
عرض مرئي مباشر لما يراه البوت
- الصورة الأصلية
- اللوحة المكتشفة (شبكة 8×8 مع الحالة)
- القطع المكتشفة (bbox + شكل)
- أفضل حركة مقترحة
- إحصائيات مباشرة (FPS, filled cells, ...)
"""

import sys
import time
from pathlib import Path
from typing import Optional, List

import cv2
import numpy as np

from loguru import logger

try:
    from config import (
        DEBUG_CONFIG, BOARD_CONFIG, TRAY_CONFIG, DEBUG_DIR,
    )
except ImportError:
    DEBUG_DIR = Path(__file__).parent.parent / "debug"
    DEBUG_CONFIG = {
        "draw_board_grid": True,
        "draw_blocks": True,
        "draw_best_move": True,
        "show_coordinates": False,
        "window_width": 540,
        "window_height": 960,
    }
    BOARD_CONFIG = {
        "rows": 8, "cols": 8,
        "x_start": 100, "y_start": 1100, "cell_size": 100,
    }
    TRAY_CONFIG = {"slot_positions": [(250, 1900), (540, 1900), (830, 1900)]}


# ============================================================
# كلاس العرض المرئي
# ============================================================

class DebugView:
    """عرض مرئي مباشر لما يراه البوت"""

    def __init__(self, window_name: str = "Block Blast Bot - Debug"):
        self.window_name = window_name
        self.window_created = False
        self._quit_requested = False

        # حجم النافذة
        self.max_w = DEBUG_CONFIG.get("window_width", 540)
        self.max_h = DEBUG_CONFIG.get("window_height", 960)

        # آخر إطار معروض
        self._last_frame: Optional[np.ndarray] = None

        # إحصائيات
        self._frame_count = 0
        self._fps_start = time.time()
        self._fps_history: List[float] = []

        # آخر صورة محفوظة
        self._last_display: Optional[np.ndarray] = None

        logger.debug("👁️  DebugView جاهز")

    # ========================================================
    # الواجهة الرئيسية
    # ========================================================

    def show(
        self,
        frame: np.ndarray,
        board: Optional[np.ndarray] = None,
        blocks: Optional[List] = None,
        best_move=None,
        extra_info: Optional[dict] = None,
    ):
        """
        عرض إطار مع كل المعلومات المرئية

        Args:
            frame: الصورة الأصلية
            board: مصفوفة اللوحة (اختياري)
            blocks: قائمة القطع (اختياري)
            best_move: أفضل حركة (اختياري)
            extra_info: معلومات إضافية للعرض (اختياري)
        """
        if frame is None:
            return

        if not self._ensure_window():
            return

        canvas = frame.copy()

        # ============================================================
        # 1) رسم شبكة اللوحة
        # ============================================================
        if board is not None and DEBUG_CONFIG.get("draw_board_grid", True):
            canvas = self._draw_board(canvas, board)

        # ============================================================
        # 2) رسم القطع
        # ============================================================
        if blocks and DEBUG_CONFIG.get("draw_blocks", True):
            canvas = self._draw_blocks(canvas, blocks)

        # ============================================================
        # 3) رسم أفضل حركة
        # ============================================================
        if best_move is not None and DEBUG_CONFIG.get("draw_best_move", True):
            canvas = self._draw_best_move(canvas, best_move)

        # ============================================================
        # 4) رسم الإحصائيات
        # ============================================================
        canvas = self._draw_stats(canvas, board, blocks, extra_info)

        # ============================================================
        # 5) تصغير للعرض
        # ============================================================
        display = self._resize_for_display(canvas)

        self._last_display = display.copy()
        self._last_frame = frame.copy()
        self._frame_count += 1

        # حساب FPS
        self._update_fps()

        # عرض
        cv2.imshow(self.window_name, display)

        # معالجة المفاتيح
        key = cv2.waitKey(1) & 0xFF
        self._handle_key(key)

    def should_quit(self) -> bool:
        """هل طُلب الخروج؟"""
        return self._quit_requested

    def close(self):
        """إغلاق النافذة"""
        try:
            cv2.destroyAllWindows()
            # عدة مرات للتأكد (OpenCV مشكلة معروفة على بعض الأنظمة)
            for _ in range(3):
                cv2.waitKey(1)
        except Exception:
            pass
        self.window_created = False
        logger.debug("👁️  تم إغلاق DebugView")

    def reset(self):
        """إعادة تعيين الحالة"""
        self._quit_requested = False
        self._frame_count = 0
        self._fps_start = time.time()
        self._fps_history.clear()

    # ========================================================
    # إدارة النافذة
    # ========================================================

    def _ensure_window(self) -> bool:
        """إنشاء النافذة إن لم تكن موجودة"""
        if self.window_created:
            return True

        try:
            cv2.namedWindow(self.window_name, cv2.WINDOW_AUTOSIZE)
            self.window_created = True
            return True
        except Exception as e:
            logger.error(f"❌ فشل إنشاء نافذة العرض: {e}")
            logger.info("   تأكد من وجود واجهة رسومية (DISPLAY)")
            return False

    def _resize_for_display(self, frame: np.ndarray) -> np.ndarray:
        """تصغير الصورة لتناسب الشاشة"""
        h, w = frame.shape[:2]
        scale = min(self.max_h / h, self.max_w / w, 1.0)

        if scale >= 1.0:
            return frame

        new_w = int(w * scale)
        new_h = int(h * scale)
        return cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)

    def _handle_key(self, key: int):
        """معالجة مفاتيح التحكم"""
        # ESC أو Q = خروج
        if key in (27, ord("q"), ord("Q")):
            self._quit_requested = True

        # S = حفظ صورة
        elif key in (ord("s"), ord("S")):
            self.save_screenshot()

        # R = إعادة تعيين
        elif key in (ord("r"), ord("R")):
            self.reset()
            logger.info("🔄 إعادة تعيين")

    # ========================================================
    # رسم اللوحة
    # ========================================================

    def _draw_board(self, canvas: np.ndarray, board: np.ndarray) -> np.ndarray:
        """رسم شبكة اللوحة والحالة"""
        rows = BOARD_CONFIG.get("rows", 8)
        cols = BOARD_CONFIG.get("cols", 8)
        x_start = BOARD_CONFIG.get("x_start", 100)
        y_start = BOARD_CONFIG.get("y_start", 1100)
        cell = BOARD_CONFIG.get("cell_size", 100)

        # التحقق من الأبعاد
        if board.shape != (rows, cols):
            logger.debug(f"⚠️  بُعد اللوحة مختلف: {board.shape}")
            rows, cols = board.shape

        for r in range(rows):
            for c in range(cols):
                cx = x_start + c * cell
                cy = y_start + r * cell
                half = cell // 2

                x1 = cx - half
                y1 = cy - half
                x2 = cx + half
                y2 = cy + half

                is_filled = board[r, c] == 1

                # اللون حسب الحالة
                if is_filled:
                    color = (0, 0, 255)      # أحمر
                    thickness = 2
                else:
                    color = (0, 200, 0)      # أخضر
                    thickness = 1

                cv2.rectangle(canvas, (x1, y1), (x2, y2), color, thickness)

                # نقطة في مركز الخلية الممتلئة
                if is_filled:
                    cv2.circle(canvas, (cx, cy), max(2, cell // 8), (0, 0, 255), -1)

                # إحداثيات (اختياري)
                if DEBUG_CONFIG.get("show_coordinates", False):
                    cv2.putText(
                        canvas, f"{r},{c}",
                        (x1 + 3, y1 + 15),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.3,
                        (255, 255, 255), 1,
                    )

        return canvas

    # ========================================================
    # رسم القطع
    # ========================================================

    def _draw_blocks(self, canvas: np.ndarray, blocks: List) -> np.ndarray:
        """رسم القطع المكتشفة"""
        for block in blocks:
            # bbox
            bbox = getattr(block, "bbox", None)
            if bbox is None or len(bbox) < 4:
                continue

            bx, by, bw, bh = bbox
            if bw <= 0 or bh <= 0:
                continue

            # إطار خارجي
            cv2.rectangle(canvas, (bx, by), (bx + bw, by + bh), (0, 255, 0), 2)

            # نص فوق الصندوق
            slot = getattr(block, "slot_index", -1) + 1
            h_dim = getattr(block, "height", 0)
            w_dim = getattr(block, "width", 0)
            color_name = getattr(block, "color_name", "?")

            info = f"S{slot}: {h_dim}x{w_dim} [{color_name}]"

            # خلفية سوداء للنص
            text_size = cv2.getTextSize(
                info, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1
            )[0]
            cv2.rectangle(
                canvas,
                (bx, by - text_size[1] - 8),
                (bx + text_size[0] + 6, by),
                (0, 0, 0), -1,
            )

            cv2.putText(
                canvas, info,
                (bx + 3, by - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                (0, 255, 255), 1,
            )

            # رسم شبكة القطعة داخلها
            self._draw_block_shape(canvas, block, bx, by, bw, bh)

        # رسم مراكز slots
        for i, (cx, cy) in enumerate(TRAY_CONFIG.get("slot_positions", [])):
            cv2.circle(canvas, (int(cx), int(cy)), 5, (255, 255, 255), -1)
            cv2.putText(
                canvas, f"S{i+1}",
                (int(cx) - 12, int(cy) - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                (255, 255, 255), 1,
            )

        return canvas

    def _draw_block_shape(
        self,
        canvas: np.ndarray,
        block,
        bx: int, by: int, bw: int, bh: int,
    ):
        """رسم شبكة الشكل داخل bbox القطعة"""
        shape = getattr(block, "shape", None)
        if shape is None:
            return

        h, w = shape.shape
        if h == 0 or w == 0:
            return

        cell_w = bw / w
        cell_h = bh / h

        for r in range(h):
            for c in range(w):
                x1 = int(bx + c * cell_w)
                y1 = int(by + r * cell_h)
                x2 = int(bx + (c + 1) * cell_w)
                y2 = int(by + (r + 1) * cell_h)

                if shape[r, c] == 1:
                    # خلية ممتلئة
                    cx = (x1 + x2) // 2
                    cy = (y1 + y2) // 2
                    cv2.circle(canvas, (cx, cy), 4, (0, 0, 255), -1)
                    cv2.rectangle(canvas, (x1, y1), (x2, y2), (0, 0, 255), 1)
                else:
                    # خلية فارغة
                    cv2.rectangle(canvas, (x1, y1), (x2, y2), (80, 80, 80), 1)

    # ========================================================
    # رسم أفضل حركة
    # ========================================================

    def _draw_best_move(self, canvas: np.ndarray, move) -> np.ndarray:
        """رسم أفضل حركة مقترحة (تظليل أصفر شفاف)"""
        try:
            # احصل على الخلايا
            if hasattr(move, "get_cells"):
                cells = move.get_cells()
            else:
                return canvas

            if not cells:
                return canvas

            x_start = BOARD_CONFIG.get("x_start", 100)
            y_start = BOARD_CONFIG.get("y_start", 1100)
            cell = BOARD_CONFIG.get("cell_size", 100)

            # تظليل شفاف
            overlay = canvas.copy()

            for r, c in cells:
                # تجاهل الخلايا خارج الحدود
                if not (0 <= r < 8 and 0 <= c < 8):
                    continue

                cx = x_start + c * cell
                cy = y_start + r * cell
                half = cell // 2

                cv2.rectangle(
                    overlay,
                    (cx - half, cy - half),
                    (cx + half, cy + half),
                    (0, 255, 255),  # أصفر
                    -1,
                )

            # دمج شفاف
            canvas = cv2.addWeighted(overlay, 0.35, canvas, 0.65, 0)

            # إطارات صفراء
            for r, c in cells:
                if not (0 <= r < 8 and 0 <= c < 8):
                    continue

                cx = x_start + c * cell
                cy = y_start + r * cell
                half = cell // 2

                cv2.rectangle(
                    canvas,
                    (cx - half, cy - half),
                    (cx + half, cy + half),
                    (0, 255, 255), 2,
                )

            # نص "BEST MOVE"
            r0, c0 = cells[0]
            cx0 = x_start + c0 * cell
            cy0 = y_start + r0 * cell - cell // 2 - 15

            # نص مع خلفية
            score = getattr(move, "score", 0)
            text = f"BEST: {score:.0f}"

            cv2.putText(
                canvas, text,
                (cx0 - 50, cy0),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                (0, 0, 0), 4,
            )
            cv2.putText(
                canvas, text,
                (cx0 - 50, cy0),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                (0, 255, 255), 2,
            )

        except Exception as e:
            logger.debug(f"خطأ في رسم الحركة: {e}")

        return canvas

    # ========================================================
    # رسم الإحصائيات
    # ========================================================

    def _draw_stats(
        self,
        canvas: np.ndarray,
        board: Optional[np.ndarray],
        blocks: Optional[List],
        extra_info: Optional[dict] = None,
    ) -> np.ndarray:
        """رسم شريط الإحصائيات في الأعلى والأسفل"""
        h, w = canvas.shape[:2]

        # ============================================================
        # شريط علوي
        # ============================================================
        cv2.rectangle(canvas, (0, 0), (w, 60), (0, 0, 0), -1)

        # FPS
        fps = self._get_current_fps()
        fps_text = f"FPS: {fps:.1f}"

        # إحصائيات اللوحة
        if board is not None:
            filled = int(np.sum(board))
            board_text = f"Filled: {filled}/64"
        else:
            board_text = "Board: N/A"

        # القطع
        if blocks is not None:
            blocks_text = f"Blocks: {len(blocks)}"
        else:
            blocks_text = "Blocks: N/A"

        # السطر الأول
        line1 = f"{fps_text}  |  {board_text}  |  {blocks_text}"
        cv2.putText(
            canvas, line1,
            (10, 25),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6,
            (0, 255, 0), 2,
        )

        # السطر الثاني (معلومات إضافية)
        line2_parts = [f"Frame: {self._frame_count}"]

        if extra_info:
            for k, v in extra_info.items():
                line2_parts.append(f"{k}: {v}")

        line2 = "  |  ".join(line2_parts)
        cv2.putText(
            canvas, line2,
            (10, 50),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5,
            (200, 200, 200), 1,
        )

        # ============================================================
        # شريط سفلي (تعليمات)
        # ============================================================
        cv2.rectangle(canvas, (0, h - 35), (w, h), (0, 0, 0), -1)

        help_text = "[Q/ESC] Quit  |  [S] Save  |  [R] Reset"
        cv2.putText(
            canvas, help_text,
            (10, h - 12),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5,
            (180, 180, 180), 1,
        )

        return canvas

    # ========================================================
    # FPS
    # ========================================================

    def _update_fps(self):
        """تحديث حساب FPS"""
        now = time.time()
        elapsed = now - self._fps_start

        if elapsed > 0:
            fps = self._frame_count / elapsed
            self._fps_history.append(fps)

            # احتفظ بآخر 30 قيمة فقط
            if len(self._fps_history) > 30:
                self._fps_history.pop(0)

    def _get_current_fps(self) -> float:
        """متوسط FPS لآخر فترة"""
        if not self._fps_history:
            elapsed = time.time() - self._fps_start
            return self._frame_count / elapsed if elapsed > 0 else 0.0

        return sum(self._fps_history) / len(self._fps_history)

    # ========================================================
    # حفظ الصور
    # ========================================================

    def save_screenshot(self, filename: str = None) -> bool:
        """حفظ آخر إطار معروض"""
        if self._last_display is None:
            logger.warning("⚠️  لا يوجد إطار للحفظ")
            return False

        try:
            DEBUG_DIR.mkdir(parents=True, exist_ok=True)

            if filename is None:
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"debug_view_{timestamp}.png"

            path = DEBUG_DIR / filename
            cv2.imwrite(str(path), self._last_display)
            logger.info(f"💾 حفظ: {path}")
            return True

        except Exception as e:
            logger.warning(f"⚠️  فشل الحفظ: {e}")
            return False

    def save_raw_frame(self, filename: str = None) -> bool:
        """حفظ الإطار الأصلي (بدون رسومات)"""
        if self._last_frame is None:
            return False

        try:
            DEBUG_DIR.mkdir(parents=True, exist_ok=True)

            if filename is None:
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"raw_{timestamp}.png"

            path = DEBUG_DIR / filename
            cv2.imwrite(str(path), self._last_frame)
            logger.info(f"💾 حفظ (خام): {path}")
            return True

        except Exception as e:
            logger.warning(f"⚠️  {e}")
            return False

    # ========================================================
    # إحصائيات
    # ========================================================

    def stats(self) -> dict:
        """إحصائيات العرض"""
        elapsed = time.time() - self._fps_start
        return {
            "frames": self._frame_count,
            "elapsed_sec": round(elapsed, 1),
            "avg_fps": round(self._get_current_fps(), 1),
        }


# ============================================================
# اختبار سريع
# ============================================================

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from utils.logger import setup_logger, log_section

    setup_logger(level="DEBUG")
    log_section("اختبار Debug View")

    try:
        # محاولة الاتصال بالهاتف
        try:
            from core.adb_controller import ADBController
            from core.screen_capture import ScreenCapture
            from core.board_detector import BoardDetector
            from core.block_detector import BlockDetector

            adb = ADBController()
            if not adb.is_connected():
                logger.error("❌ لا يوجد هاتف متصل!")
                raise SystemExit(1)

            logger.success("✅ الهاتف متصل")

            capture = ScreenCapture(adb)
            board_detector = BoardDetector()
            block_detector = BlockDetector()

        except ImportError as e:
            logger.error(f"❌ مكتبة ناقصة: {e}")
            raise SystemExit(1)

        # إنشاء العرض
        view = DebugView()

        logger.info("👁️  بدء العرض المباشر — اضغط Q للخروج")

        try:
            while not view.should_quit():
                frame = capture.grab()
                if frame is None:
                    time.sleep(0.05)
                    continue

                board = board_detector.detect(frame)
                blocks = block_detector.detect(frame)

                view.show(frame, board=board, blocks=blocks)

        except KeyboardInterrupt:
            logger.info("\n⏹️  تم الإيقاف")

        finally:
            view.close()

        print("\n📊 إحصائيات العرض:")
        for k, v in view.stats().items():
            print(f"  {k}: {v}")

        log_section("انتهى الاختبار", char="-")

    except SystemExit:
        pass
    except Exception as e:
        logger.exception(f"❌ خطأ: {e}")