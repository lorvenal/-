"""
Block Blast Bot - Main Entry Point
===================================
نقطة البداية لتشغيل بوت لعبة Block Blast
يقرأ الشاشة عبر USB، يحلل اللعبة، ويقوم بالحركات تلقائياً
"""

import sys
import time
import argparse
from pathlib import Path

# إضافة مسار المشروع
sys.path.insert(0, str(Path(__file__).parent))

from loguru import logger

from config import CONFIG
from core.adb_controller import ADBController
from core.screen_capture import ScreenCapture
from core.board_detector import BoardDetector
from core.block_detector import BlockDetector
from core.game_state import GameState
from ai.solver import Solver
from automation.touch_engine import TouchEngine
from automation.loop_controller import LoopController
from utils.logger import setup_logger, log_section


# ============================================================
# إعداد السجل (Logging)
# ============================================================
setup_logger()


# ============================================================
# دوال مساعدة
# ============================================================

def print_banner():
    """طباعة شعار البوت"""
    banner = r"""
    ╔══════════════════════════════════════════════╗
    ║                                              ║
    ║        🎮  BLOCK BLAST BOT  🎮              ║
    ║                                              ║
    ║        Automated Game Player v1.0           ║
    ║                                              ║
    ╚══════════════════════════════════════════════╝
    """
    print(banner)


def check_environment() -> bool:
    """التحقق من البيئة والمتطلبات"""
    log_section("فحص البيئة")

    # 1) فحص الاتصال بـ ADB
    logger.info("🔍 فحص اتصال ADB...")
    try:
        adb = ADBController()
    except RuntimeError as e:
        logger.error(str(e))
        return False

    if not adb.is_connected():
        logger.error("❌ لا يوجد هاتف متصل عبر USB!")
        logger.error("   تأكد من:")
        logger.error("   1. تفعيل USB Debugging في الهاتف")
        logger.error("   2. توصيل الكابل")
        logger.error("   3. الموافقة على الطلب في الهاتف")
        logger.error("")
        logger.error("   جرّب: adb devices")
        return False

    device = adb.get_device_info()
    logger.success(f"✅ متصل بالهاتف: {device.get('model', 'Unknown')}")
    logger.info(f"   الدقة: {device.get('width')}x{device.get('height')}")
    logger.info(f"   Android: {device.get('android_version', 'Unknown')}")

    # 2) فحص إعدادات المعايرة
    if not CONFIG.get("calibrated", False):
        logger.warning("⚠️  المشروع غير معاير!")
        logger.info("   شغّل أولاً: python main.py --calibrate")
        return False

    logger.success("✅ المعايرة موجودة")

    # 3) فحص التقاط الشاشة
    logger.info("📸 فحص التقاط الشاشة...")
    try:
        capture = ScreenCapture(adb)
        frame = capture.grab()
        if frame is None:
            logger.error("❌ فشل التقاط الشاشة")
            return False
        h, w = frame.shape[:2]
        logger.success(f"✅ الالتقاط يعمل: {w}x{h}")
    except Exception as e:
        logger.error(f"❌ خطأ في الالتقاط: {e}")
        return False

    # 4) فحص كشف اللوحة
    logger.info("🎯 فحص كشف اللوحة...")
    try:
        detector = BoardDetector()
        board = detector.detect(frame)
        filled = int(board.sum()) if board is not None else 0
        logger.success(f"✅ اللوحة: {filled}/64 خلية ممتلئة")
    except Exception as e:
        logger.error(f"❌ خطأ في كشف اللوحة: {e}")
        return False

    # 5) فحص كشف القطع
    logger.info("🧩 فحص كشف القطع...")
    try:
        block_detector = BlockDetector()
        blocks = block_detector.detect(frame)
        if blocks:
            logger.success(f"✅ تم كشف {len(blocks)} قطعة")
        else:
            logger.warning("⚠️  لم يتم كشف أي قطعة (تأكد من أن اللعبة مفتوحة)")
    except Exception as e:
        logger.error(f"❌ خطأ في كشف القطع: {e}")
        return False

    log_section("✅ البيئة جاهزة", char="-")
    return True


# ============================================================
# الأوضاع (Modes)
# ============================================================

def run_calibration():
    """وضع المعايرة - تحديد إحداثيات اللوحة والقطع"""
    log_section("وضع المعايرة")

    try:
        from utils.calibration import Calibration
    except ImportError as e:
        logger.error(f"❌ لا يمكن استيراد Calibration: {e}")
        logger.info("   تأكد من وجود utils/calibration.py")
        return

    # الاتصال (اختياري، قد يعمل بدون)
    adb = None
    try:
        adb = ADBController()
        if not adb.is_connected():
            logger.warning("⚠️  لا يوجد هاتف، استخدام صورة اختبار")
            adb = None
    except Exception as e:
        logger.warning(f"⚠️  {e}")
        adb = None

    calib = Calibration(adb_controller=adb)

    try:
        calib.run_interactive()
        logger.success("✅ انتهت المعايرة")
    except Exception as e:
        logger.exception(f"❌ فشل المعايرة: {e}")


def run_debug_view():
    """وضع التشخيص - عرض ما يراه البوت"""
    log_section("العرض المرئي")

    try:
        from utils.debug_view import DebugView
    except ImportError as e:
        logger.error(f"❌ لا يمكن استيراد DebugView: {e}")
        logger.info("   تأكد من وجود utils/debug_view.py")
        return

    adb = ADBController()
    if not adb.is_connected():
        logger.error("❌ لا يوجد هاتف متصل!")
        return

    capture = ScreenCapture(adb)
    board_detector = BoardDetector()
    block_detector = BlockDetector()
    solver = Solver()
    debug = DebugView()

    logger.info("👁️  اضغط Q أو ESC للخروج")

    try:
        while True:
            frame = capture.grab()
            if frame is None:
                continue

            board = board_detector.detect(frame)
            blocks = block_detector.detect(frame)

            # إيجاد أفضل حركة للعرض
            best_move = None
            try:
                if blocks:
                    state = GameState(board=board, blocks=blocks)
                    if not state.is_game_over():
                        best_move = solver.find_best_move(state)
            except Exception as e:
                logger.debug(f"Solver: {e}")

            debug.show(
                frame,
                board=board,
                blocks=blocks,
                best_move=best_move,
            )

            if debug.should_quit():
                break

            time.sleep(0.05)

    except KeyboardInterrupt:
        logger.info("⏹️  تم إيقاف التشخيص")
    finally:
        debug.close()
        stats = debug.stats()
        logger.info(f"📊 إحصائيات العرض: {stats}")


def run_single_move():
    """تنفيذ حركة واحدة فقط - للاختبار"""
    log_section("تنفيذ حركة واحدة")

    adb = ADBController()
    if not adb.is_connected():
        logger.error("❌ لا يوجد هاتف متصل!")
        return

    capture = ScreenCapture(adb)
    board_detector = BoardDetector()
    block_detector = BlockDetector()
    solver = Solver()
    touch = TouchEngine(adb)

    # 1) التقاط الشاشة
    logger.info("📸 التقاط الشاشة...")
    frame = capture.grab()
    if frame is None:
        logger.error("❌ فشل التقاط الشاشة")
        return

    # 2) كشف اللوحة والقطع
    logger.info("🔍 كشف اللوحة والقطع...")
    board = board_detector.detect(frame)
    blocks = block_detector.detect(frame)

    state = GameState(board=board, blocks=blocks)
    print("\n" + state.summary())

    # 3) إيجاد أفضل حركة
    logger.info("🧠 إيجاد أفضل حركة...")
    move = solver.find_best_move(state)
    if move is None:
        logger.warning("⚠️  لا توجد حركة متاحة!")
        return

    logger.info(f"💡 أفضل حركة: {move}")

    # 4) تأكيد المستخدم
    print("\n" + "!" * 60)
    print("⚠️  سيتم تنفيذ حركة فعلية على الهاتف!")
    print("!" * 60)
    response = input("\nمتابعة؟ (y/n): ").strip().lower()
    if response != "y":
        logger.info("⏹️  تم الإلغاء")
        return

    # 5) تنفيذها
    logger.info("👆 تنفيذ الحركة...")
    success = touch.execute(move)

    if success:
        logger.success("✅ تم تنفيذ الحركة")
    else:
        logger.error("❌ فشل تنفيذ الحركة")


def run_auto_play(max_moves=None, delay=None):
    """التشغيل التلقائي الكامل - قلب المشروع"""
    log_section("اللعب التلقائي")

    if not check_environment():
        logger.error("❌ الفحص الأولي فشل")
        return

    print("\n" + "!" * 60)
    print("⚠️  تحذير: سيبدأ البوت باللعب فعلياً على هاتفك!")
    if max_moves:
        print(f"   عدد الحركات: {max_moves}")
    else:
        print(f"   عدد الحركات: بلا حد (حتى Game Over)")
    print(f"   التأخير: {delay or CONFIG['loop_delay']}s")
    print("!" * 60)

    response = input("\nابدأ؟ (y/n): ").strip().lower()
    if response != "y":
        logger.info("⏹️  تم الإلغاء")
        return

    try:
        loop = LoopController(
            max_moves=max_moves,
            delay=delay,
        )
        loop.run()
    except KeyboardInterrupt:
        logger.info("\n⏹️  تم إيقاف البوت يدوياً")
    except Exception as e:
        logger.exception(f"❌ خطأ غير متوقع: {e}")


# ============================================================
# Point d'entrée
# ============================================================

def parse_args():
    parser = argparse.ArgumentParser(
        description="Block Blast Bot - بوت لعب تلقائي",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
أمثلة:
  python main.py --check              # فحص الاتصال
  python main.py --calibrate          # المعايرة
  python main.py --debug              # عرض مرئي
  python main.py --once               # حركة واحدة
  python main.py                      # اللعب الكامل
  python main.py --moves 50           # 50 حركة فقط
        """,
    )

    parser.add_argument(
        "--calibrate",
        action="store_true",
        help="تشغيل وضع المعايرة (مطلوب أول مرة)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="عرض مرئي لما يراه البوت",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="تنفيذ حركة واحدة فقط (للاختبار)",
    )
    parser.add_argument(
        "--moves",
        type=int,
        default=None,
        help="عدد الحركات قبل التوقف (افتراضي: بلا حد)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=None,
        help="التأخير بين الحركات بالثواني (افتراضي من config)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="التحقق من الاتصال والمتطلبات فقط",
    )

    return parser.parse_args()


def main():
    print_banner()
    args = parse_args()

    # توجيه حسب الوضع المطلوب
    if args.check:
        success = check_environment()
        sys.exit(0 if success else 1)

    elif args.calibrate:
        run_calibration()

    elif args.debug:
        run_debug_view()

    elif args.once:
        run_single_move()

    else:
        run_auto_play(max_moves=args.moves, delay=args.delay)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n⏹️  خروج")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"💥 خطأ قاتل: {e}")
        sys.exit(1)