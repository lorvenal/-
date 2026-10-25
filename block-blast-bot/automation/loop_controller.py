"""
Block Blast Bot - Loop Controller
===================================
حلقة اللعب الرئيسية — تربط كل المكونات:
1. التقاط الشاشة
2. كشف اللوحة والقطع
3. بناء GameState
4. إيجاد أفضل حركة (Solver)
5. تنفيذ الحركة (TouchEngine)
6. تكرار حتى Game Over
"""

import sys
import time
from pathlib import Path
from typing import Optional

import numpy as np
from loguru import logger

try:
    from config import (
        LOOP_CONFIG, BOARD_CONFIG, DEBUG_DIR, SCREEN_CONFIG,
    )
    from core.adb_controller import ADBController
    from core.screen_capture import ScreenCapture
    from core.board_detector import BoardDetector
    from core.block_detector import BlockDetector
    from core.game_state import GameState
    from ai.solver import Solver
    from automation.touch_engine import TouchEngine
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from config import (
        LOOP_CONFIG, BOARD_CONFIG, DEBUG_DIR, SCREEN_CONFIG,
    )
    from core.adb_controller import ADBController
    from core.screen_capture import ScreenCapture
    from core.board_detector import BoardDetector
    from core.block_detector import BlockDetector
    from core.game_state import GameState
    from ai.solver import Solver
    from automation.touch_engine import TouchEngine


# ============================================================
# كلاس حلقة اللعب
# ============================================================

class LoopController:
    """حلقة اللعب الرئيسية"""

    def __init__(
        self,
        max_moves: Optional[int] = None,
        delay: Optional[float] = None,
        verify_moves: bool = False,
    ):
        """
        Args:
            max_moves: أقصى عدد حركات (None = بلا حد)
            delay: التأخير بين الحركات (ثواني)
            verify_moves: التحقق من كل حركة بعد تنفيذها
        """
        # الإعدادات
        self.max_moves = max_moves or LOOP_CONFIG.get("max_moves")
        self.delay = delay or LOOP_CONFIG.get("loop_delay", 0.7)
        self.verify_moves = verify_moves

        # المكونات
        logger.info("🔧 تهيئة المكونات...")
        self.adb = ADBController()

        if not self.adb.is_connected():
            raise RuntimeError("❌ لا يوجد هاتف متصل!")

        self.capture = ScreenCapture(self.adb)
        self.board_detector = BoardDetector()
        self.block_detector = BlockDetector()
        self.solver = Solver()
        self.touch = TouchEngine(self.adb)

        # الإحصائيات
        self.stats_data = {
            "moves_played": 0,
            "total_lines_cleared": 0,
            "best_single_move_lines": 0,
            "game_overs": 0,
            "errors": 0,
            "start_time": None,
            "end_time": None,
        }

        # حالة التوقف
        self._should_stop = False
        self._last_state: Optional[GameState] = None

        logger.success(f"✅ جاهز — delay={self.delay}s, max_moves={self.max_moves}")

    # ========================================================
    # الواجهة الرئيسية
    # ========================================================

    def run(self):
        """تشغيل الحلقة الكاملة"""
        logger.info("=" * 60)
        logger.info("🚀 بدء اللعب التلقائي")
        logger.info("=" * 60)

        # تحقق أولي
        if not self._preflight_check():
            return

        self.stats_data["start_time"] = time.time()

        move_count = 0

        try:
            while not self._should_stop:
                # 1) فحص الحد الأقصى
                if self.max_moves and move_count >= self.max_moves:
                    logger.info(f"🏁 وصلنا للحد الأقصى ({self.max_moves} حركة)")
                    break

                # 2) دورة لعب واحدة
                result = self._play_one_turn()

                if result == "game_over":
                    logger.warning("💀 Game Over!")
                    self.stats_data["game_overs"] += 1
                    break

                elif result == "no_moves":
                    logger.warning("⚠️  لا توجد حركات صالحة")
                    break

                elif result == "error":
                    self.stats_data["errors"] += 1
                    if self.stats_data["errors"] > 5:
                        logger.error("❌ أخطاء كثيرة — إيقاف")
                        break

                elif result == "success":
                    move_count += 1
                    self.stats_data["moves_played"] += 1

                    # 3) تأخير
                    time.sleep(self.delay)

        except KeyboardInterrupt:
            logger.info("\n⏹️  تم الإيقاف يدوياً")

        finally:
            self.stats_data["end_time"] = time.time()
            self._print_final_stats()

    def stop(self):
        """إيقاف الحلقة (يمكن استدعاؤها من خيط آخر)"""
        logger.info("🛑 طلب إيقاف")
        self._should_stop = True

    # ========================================================
    # دورة واحدة
    # ========================================================

    def _play_one_turn(self) -> str:
        """
        دورة لعب واحدة

        Returns:
            "success" / "game_over" / "no_moves" / "error"
        """
        try:
            # ============================================================
            # 1) التقاط الشاشة
            # ============================================================
            frame = self.capture.grab()
            if frame is None:
                logger.warning("⚠️  فشل التقاط الشاشة")
                return "error"

            time.sleep(LOOP_CONFIG.get("post_capture_delay", 0.15))

            # ============================================================
            # 2) كشف اللوحة
            # ============================================================
            board = self.board_detector.detect(frame)

            # ============================================================
            # 3) كشف القطع
            # ============================================================
            blocks = self.block_detector.detect(frame)

            if not blocks:
                logger.warning("⚠️  لم يتم كشف أي قطعة")
                return "error"

            # ============================================================
            # 4) بناء الحالة
            # ============================================================
            state = GameState(board=board, blocks=blocks)
            self._last_state = state

            logger.info(
                f"📸 حالة: filled={state.count_filled()}/64, "
                f"blocks={len(blocks)}"
            )

            # ============================================================
            # 5) فحص Game Over
            # ============================================================
            if state.is_game_over():
                logger.warning("💀 Game Over detected")
                self._save_gameover_screenshot(frame)
                return "game_over"

            # ============================================================
            # 6) إيجاد أفضل حركة
            # ============================================================
            move = self.solver.find_best_move(state)
            if move is None:
                logger.warning("⚠️  Solver لم يجد حركة")
                return "no_moves"

            logger.info(f"🎯 الحركة المختارة: {move}")

            # ============================================================
            # 7) تنفيذ الحركة
            # ============================================================
            success = self.touch.execute(move)
            if not success:
                logger.error("❌ فشل تنفيذ الحركة")
                return "error"

            # ============================================================
            # 8) تحديث الإحصائيات
            # ============================================================
            self.stats_data["total_lines_cleared"] += move.lines_cleared
            if move.lines_cleared > self.stats_data["best_single_move_lines"]:
                self.stats_data["best_single_move_lines"] = move.lines_cleared

            # ============================================================
            # 9) تأخير بعد الحركة
            # ============================================================
            time.sleep(LOOP_CONFIG.get("post_move_delay", 0.5))

            return "success"

        except Exception as e:
            logger.exception(f"❌ خطأ في دورة اللعب: {e}")
            return "error"

    # ========================================================
    # فحوصات أولية
    # ========================================================

    def _preflight_check(self) -> bool:
        """فحص كل شيء قبل البدء"""
        logger.info("🔍 فحص أولي...")

        # 1) هل الهاتف متصل؟
        if not self.adb.is_connected():
            logger.error("❌ لا يوجد هاتف متصل")
            return False
        logger.success("  ✓ الهاتف متصل")

        # 2) هل الشاشة مضاءة؟
        if not self.adb.is_screen_on():
            logger.warning("  ⚠️  الشاشة مغلقة — محاولة إيقاظ")
            self.adb.wake_screen()
            time.sleep(1)

        # 3) هل المعايرة موجودة؟
        try:
            from config import CONFIG
            if not CONFIG.get("calibrated"):
                logger.error("❌ المعايرة غير مكتملة")
                logger.info("   شغّل: python main.py --calibrate")
                return False
            logger.success("  ✓ المعايرة موجودة")
        except Exception as e:
            logger.warning(f"  ⚠️  {e}")

        # 4) اختبار التقاط الشاشة
        logger.info("  📸 اختبار التقاط الشاشة...")
        frame = self.capture.grab()
        if frame is None:
            logger.error("  ❌ فشل التقاط الشاشة")
            return False

        h, w = frame.shape[:2]
        logger.success(f"  ✓ الشاشة: {w}x{h}")

        # 5) اختبار كشف اللوحة
        logger.info("  🔍 اختبار كشف اللوحة...")
        board = self.board_detector.detect(frame)
        filled = int(np.sum(board))
        logger.success(f"  ✓ اللوحة: {filled}/64 خلية ممتلئة")

        # 6) اختبار كشف القطع
        logger.info("  🔍 اختبار كشف القطع...")
        blocks = self.block_detector.detect(frame)
        if not blocks:
            logger.warning("  ⚠️  لم يتم كشف قطع — تأكد من أن اللعبة مفتوحة")
        else:
            logger.success(f"  ✓ تم كشف {len(blocks)} قطعة")

        # 7) اختبار Solver
        logger.info("  🧠 اختبار Solver...")
        if blocks:
            state = GameState(board=board, blocks=blocks)
            if not state.is_game_over():
                move = self.solver.find_best_move(state)
                if move:
                    logger.success(f"  ✓ Solver يعمل: {move}")
                else:
                    logger.warning("  ⚠️  Solver لم يجد حركة")
            else:
                logger.warning("  ⚠️  Game Over من البداية!")

        logger.success("✅ الفحص الأولي نجح")
        return True

    # ========================================================
    # حفظ الصور
    # ========================================================

    def _save_gameover_screenshot(self, frame: np.ndarray):
        """حفظ صورة Game Over"""
        if not LOOP_CONFIG.get("save_gameover_screenshot", True):
            return

        try:
            import cv2
            from datetime import datetime

            DEBUG_DIR.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = DEBUG_DIR / f"gameover_{timestamp}.png"
            cv2.imwrite(str(path), frame)
            logger.info(f"💾 صورة Game Over: {path}")
        except Exception as e:
            logger.warning(f"⚠️  فشل حفظ الصورة: {e}")

    def save_current_state_screenshot(self, name: str = "state"):
        """حفظ صورة الحالة الحالية"""
        frame = self.capture.grab()
        if frame is None:
            return

        try:
            import cv2
            from datetime import datetime

            DEBUG_DIR.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%H%M%S")
            path = DEBUG_DIR / f"{name}_{timestamp}.png"
            cv2.imwrite(str(path), frame)
            logger.info(f"💾 {path}")
        except Exception as e:
            logger.warning(f"⚠️  {e}")

    # ========================================================
    # الإحصائيات
    # ========================================================

    def stats(self) -> dict:
        """إحصائيات الجلسة"""
        s = self.stats_data.copy()

        # حساب المدة
        if s["start_time"] and s["end_time"]:
            duration = s["end_time"] - s["start_time"]
            s["duration_sec"] = round(duration, 1)

            if s["moves_played"] > 0:
                s["avg_move_ms"] = round(duration / s["moves_played"] * 1000, 1)

        return s

    def _print_final_stats(self):
        """طباعة الإحصائيات النهائية"""
        s = self.stats()

        logger.info("")
        logger.info("=" * 60)
        logger.info("📊 الإحصائيات النهائية")
        logger.info("=" * 60)
        logger.info(f"  الحركات:              {s['moves_played']}")
        logger.info(f"  الخطوط الممسوحة:      {s['total_lines_cleared']}")
        logger.info(f"  أفضل حركة:            {s['best_single_move_lines']} خط")
        logger.info(f"  Game Overs:           {s['game_overs']}")
        logger.info(f"  الأخطاء:              {s['errors']}")

        if "duration_sec" in s:
            logger.info(f"  المدة:                {s['duration_sec']}s")
        if "avg_move_ms" in s:
            logger.info(f"  متوسط الحركة:         {s['avg_move_ms']}ms")

        logger.info("=" * 60)

    # ========================================================
    # أدوات تشخيص
    # ========================================================

    def test_single_turn(self, save_images: bool = True) -> bool:
        """
        اختبار دورة واحدة بدون تنفيذ الحركة
        (مفيد للتصحيح)
        """
        logger.info("🧪 اختبار دورة واحدة (بدون تنفيذ)")

        # 1) التقاط
        frame = self.capture.grab()
        if frame is None:
            logger.error("❌ فشل الالتقاط")
            return False

        # 2) كشف اللوحة
        board = self.board_detector.detect(frame)
        logger.info(f"📋 اللوحة: {int(np.sum(board))}/64")

        # 3) كشف القطع
        blocks = self.block_detector.detect(frame)
        logger.info(f"🎯 القطع: {len(blocks)}")

        if not blocks:
            return False

        # 4) بناء الحالة
        state = GameState(board=board, blocks=blocks)
        print("\n" + state.summary())

        # 5) أفضل حركة
        move = self.solver.find_best_move(state)
        if move:
            logger.info(f"✨ أفضل حركة: {move}")
            logger.info(f"   ستمسح: {move.lines_cleared} خط")
        else:
            logger.warning("⚠️  لا حركة")

        # 6) حفظ صور التشخيص
        if save_images:
            import cv2

            DEBUG_DIR.mkdir(parents=True, exist_ok=True)

            board_img = self.board_detector.draw(frame, board)
            cv2.imwrite(str(DEBUG_DIR / "loop_board.png"), board_img)

            blocks_img = self.block_detector.draw(frame, blocks)
            cv2.imwrite(str(DEBUG_DIR / "loop_blocks.png"), blocks_img)

            logger.info(f"💾 صور في: {DEBUG_DIR}")

        return move is not None


# ============================================================
# اختبار سريع
# ============================================================

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from utils.logger import setup_logger, log_section
    import argparse

    setup_logger(level="DEBUG")
    log_section("اختبار Loop Controller")

    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true", help="اختبار دورة واحدة")
    parser.add_argument("--run", action="store_true", help="تشغيل فعلي")
    parser.add_argument("--moves", type=int, default=5, help="عدد الحركات")
    args = parser.parse_args()

    try:
        controller = LoopController(max_moves=args.moves)

        if args.test:
            # اختبار بدون تنفيذ
            controller.test_single_turn()

        elif args.run:
            # تشغيل فعلي
            print("\n" + "!" * 60)
            print("⚠️  تحذير: سيبدأ البوت باللعب فعلياً على هاتفك!")
            print("!" * 60)
            response = input("\nابدأ؟ (y/n): ").strip().lower()

            if response == "y":
                controller.run()
            else:
                print("⏹️  أُلغي")

        else:
            # افتراضي: اختبار
            logger.info("استخدم --test للاختبار أو --run للتشغيل الفعلي")
            controller.test_single_turn()

    except KeyboardInterrupt:
        logger.info("\n⏹️  تم الإلغاء")
    except Exception as e:
        logger.exception(f"❌ خطأ: {e}")