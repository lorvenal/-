"""
Block Blast Bot - Calibration Tool
====================================
أداة تفاعلية لتحديد إحداثيات اللوحة والقطع في Block Blast
تستخدم OpenCV لعرض الصورة والنقر لتحديد النقاط
"""

import sys
import json
from pathlib import Path

import cv2
import numpy as np

from loguru import logger

try:
    from config import (
        BOARD_CONFIG, TRAY_CONFIG, SCREEN_CONFIG,
        DEBUG_DIR, BASE_DIR, save_config, CONFIG,
    )
except ImportError:
    BASE_DIR = Path(__file__).parent.parent
    DEBUG_DIR = BASE_DIR / "debug"
    BOARD_CONFIG = {}
    TRAY_CONFIG = {}
    SCREEN_CONFIG = {}
    CONFIG = {}


# ============================================================
# كلاس المعايرة
# ============================================================

class Calibration:
    """أداة تفاعلية لمعايرة اللوحة والقطع"""

    def __init__(self, adb_controller=None):
        """
        Args:
            adb_controller: نسخة ADBController لالتقاط صورة (اختياري)
        """
        self.adb = adb_controller
        self.frame = None
        self.original_frame = None
        self.display_frame = None

        # نقاط مكتشفة
        self.points = {
            "board_tl": None,       # top-left
            "board_tr": None,       # top-right
            "board_bl": None,       # bottom-left
            "board_br": None,       # bottom-right
            "slot_1": None,
            "slot_2": None,
            "slot_3": None,
        }

        # ترتيب المعايرة
        self.steps = [
            ("board_tl", "الزاوية العلوية اليسرى للوحة"),
            ("board_tr", "الزاوية العلوية اليمنى للوحة"),
            ("board_bl", "الزاوية السفلية اليسرى للوحة"),
            ("board_br", "الزاوية السفلية اليمنى للوحة"),
            ("slot_1", "مركز القطعة الأولى (يسار)"),
            ("slot_2", "مركز القطعة الثانية (وسط)"),
            ("slot_3", "مركز القطعة الثالثة (يمين)"),
        ]

        self.current_step = 0
        self.scale = 0.5  # تصغير الصورة للعرض

        # حجم النافذة
        self.window_name = "Block Blast - Calibration"
        self._window_created = False

        # للتراجع
        self._undo_stack = []

    # ========================================================
    # تشغيل المعايرة
    # ========================================================

    def run_interactive(self):
        """تشغيل المعايرة التفاعلية الكاملة"""
        logger.info("=" * 60)
        logger.info("🎯 أداة معايرة Block Blast")
        logger.info("=" * 60)
        logger.info("")
        logger.info("📖 التعليمات:")
        logger.info("   1. ستظهر نافذة بصورة شاشة الهاتف")
        logger.info("   2. انقر على النقاط المطلوبة بالترتيب")
        logger.info("   3. انقر على **مركز** الخلية الأولى (وليس حافتها)")
        logger.info("")
        logger.info("⌨️  المفاتيح:")
        logger.info("   [R] إعادة الخطوة الحالية")
        logger.info("   [S] حفظ المعايرة")
        logger.info("   [Q] خروج بدون حفظ")
        logger.info("")

        input("👉 اضغط Enter للبدء...")

        # 1) التقاط صورة
        if not self._capture_screen():
            logger.error("❌ فشل التقاط الشاشة")
            return False

        # 2) إنشاء النافذة
        if not self._create_window():
            return False

        # 3) حلقة المعايرة
        try:
            self._calibration_loop()
        finally:
            self._close_window()

        return True

    # ========================================================
    # التقاط الشاشة
    # ========================================================

    def _capture_screen(self) -> bool:
        """التقاط صورة من الهاتف"""
        if self.adb is None:
            # التقاط من صورة موجودة (للاختبار)
            test_path = DEBUG_DIR / "test_capture.png"
            if test_path.exists():
                logger.info(f"📁 استخدام صورة موجودة: {test_path}")
                self.frame = cv2.imread(str(test_path))
            else:
                logger.error(f"❌ لم يتم إيجاد صورة اختبار في {test_path}")
                logger.info("   شغّل أولاً: python core/screen_capture.py")
                return False
        else:
            # التقاط مباشر من الهاتف
            try:
                from core.screen_capture import ScreenCapture
                capture = ScreenCapture(self.adb)
                logger.info("📸 جاري التقاط صورة من الهاتف...")
                self.frame = capture.grab(save_debug=True)
            except Exception as e:
                logger.error(f"❌ خطأ في الالتقاط: {e}")
                return False

        if self.frame is None:
            return False

        self.original_frame = self.frame.copy()

        # تحجيم الصورة للعرض
        h, w = self.frame.shape[:2]
        new_w = int(w * self.scale)
        new_h = int(h * self.scale)
        self.display_frame = cv2.resize(self.frame, (new_w, new_h))

        logger.success(f"✅ تم التقاط الصورة: {w}x{h}")
        return True

    # ========================================================
    # إدارة النافذة
    # ========================================================

    def _create_window(self) -> bool:
        """إنشاء نافذة OpenCV"""
        try:
            cv2.namedWindow(self.window_name, cv2.WINDOW_AUTOSIZE)
            cv2.setMouseCallback(self.window_name, self._on_mouse)
            self._window_created = True
            logger.info("🖼️  اضغط على الصورة لتحديد النقاط")
            return True
        except Exception as e:
            logger.error(f"❌ فشل إنشاء النافذة: {e}")
            return False

    def _close_window(self):
        """إغلاق النافذة"""
        if self._window_created:
            try:
                cv2.destroyAllWindows()
                for _ in range(3):
                    cv2.waitKey(1)
            except Exception:
                pass
            self._window_created = False

    # ========================================================
    # معالجة النقر
    # ========================================================

    def _on_mouse(self, event, x, y, flags, param):
        """معالج النقر على النافذة"""
        if event != cv2.EVENT_LBUTTONDOWN:
            return

        if self.current_step >= len(self.steps):
            logger.info("✅ اكتملت كل النقاط — اضغط [S] للحفظ")
            return

        # تحويل الإحداثيات من العرض إلى الأصلية
        real_x = int(x / self.scale)
        real_y = int(y / self.scale)

        # حفظ النقطة الحالية
        key, desc = self.steps[self.current_step]
        self.points[key] = (real_x, real_y)

        # أضف للـ undo stack
        self._undo_stack.append((key, self.current_step))

        logger.info(f"📍 {desc}: ({real_x}, {real_y})")

        # الانتقال للخطوة التالية
        self.current_step += 1

        if self.current_step >= len(self.steps):
            logger.success("🎉 اكتملت كل النقاط!")
            logger.info("   اضغط [S] للحفظ")
        else:
            next_key, next_desc = self.steps[self.current_step]
            logger.info(f"   التالي: {next_desc}")

    # ========================================================
    # رسم العناصر
    # ========================================================

    def _draw_overlay(self) -> np.ndarray:
        """رسم النقاط والشبكة على الصورة"""
        canvas = self.display_frame.copy()

        # رسم النقاط المحددة
        for key, pos in self.points.items():
            if pos is None:
                continue

            dx = int(pos[0] * self.scale)
            dy = int(pos[1] * self.scale)

            # اللون حسب النوع
            if key.startswith("board"):
                color = (0, 255, 0)  # أخضر للوحة
            else:
                color = (0, 165, 255)  # برتقالي للقطع

            # دائرة
            cv2.circle(canvas, (dx, dy), 8, color, -1)
            cv2.circle(canvas, (dx, dy), 10, (255, 255, 255), 2)

            # كتابة الاسم
            label = key.replace("board_", "").replace("slot_", "S")
            cv2.putText(
                canvas, label,
                (dx + 12, dy - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                (0, 0, 0), 4,
            )
            cv2.putText(
                canvas, label,
                (dx + 12, dy - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                (255, 255, 255), 2,
            )

        # رسم شبكة اللوحة إن أمكن
        if all(self.points[k] for k in ["board_tl", "board_tr", "board_bl", "board_br"]):
            self._draw_board_grid(canvas)

        # رسم إطار القطع
        for i in range(1, 4):
            pos = self.points.get(f"slot_{i}")
            if pos:
                dx = int(pos[0] * self.scale)
                dy = int(pos[1] * self.scale)
                cv2.rectangle(
                    canvas,
                    (dx - 35, dy - 35),
                    (dx + 35, dy + 35),
                    (0, 165, 255), 2,
                )

        # نص التعليمات
        self._draw_instructions(canvas)

        return canvas

    def _draw_board_grid(self, canvas: np.ndarray):
        """رسم شبكة 8×8 على اللوحة"""
        tl = self.points["board_tl"]
        tr = self.points["board_tr"]
        bl = self.points["board_bl"]
        br = self.points["board_br"]

        rows = BOARD_CONFIG.get("rows", 8)
        cols = BOARD_CONFIG.get("cols", 8)

        # خطوط أفقية
        for i in range(rows + 1):
            t = i / rows
            x1 = tl[0] + (bl[0] - tl[0]) * t
            y1 = tl[1] + (bl[1] - tl[1]) * t
            x2 = tr[0] + (br[0] - tr[0]) * t
            y2 = tr[1] + (br[1] - tr[1]) * t

            cv2.line(
                canvas,
                (int(x1 * self.scale), int(y1 * self.scale)),
                (int(x2 * self.scale), int(y2 * self.scale)),
                (0, 255, 255), 1,
            )

        # خطوط عمودية
        for i in range(cols + 1):
            t = i / cols
            x1 = tl[0] + (tr[0] - tl[0]) * t
            y1 = tl[1] + (tr[1] - tl[1]) * t
            x2 = bl[0] + (br[0] - bl[0]) * t
            y2 = bl[1] + (br[1] - bl[1]) * t

            cv2.line(
                canvas,
                (int(x1 * self.scale), int(y1 * self.scale)),
                (int(x2 * self.scale), int(y2 * self.scale)),
                (0, 255, 255), 1,
            )

    def _draw_instructions(self, canvas: np.ndarray):
        """رسم النص التوضيحي"""
        h, w = canvas.shape[:2]

        # شريط علوي
        cv2.rectangle(canvas, (0, 0), (w, 80), (0, 0, 0), -1)

        # الخطوة الحالية
        if self.current_step < len(self.steps):
            _, desc = self.steps[self.current_step]
            text = f"الخطوة {self.current_step + 1}/{len(self.steps)}: {desc}"
            cv2.putText(
                canvas, text,
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                (0, 255, 255), 2,
            )
            cv2.putText(
                canvas,
                "انقر على النقطة الصحيحة",
                (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                (200, 200, 200), 1,
            )
        else:
            cv2.putText(
                canvas,
                "All points set - Press [S] to Save, [R] to Redo, [Q] to Quit",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                (0, 255, 0), 2,
            )

        # شريط سفلي
        cv2.rectangle(canvas, (0, h - 40), (w, h), (0, 0, 0), -1)
        cv2.putText(
            canvas,
            "[R] Redo | [S] Save | [Q] Quit",
            (10, h - 12),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5,
            (255, 255, 255), 1,
        )

    # ========================================================
    # الحلقة الرئيسية
    # ========================================================

    def _calibration_loop(self):
        """حلقة عرض النافذة واستقبال الأحداث"""
        while True:
            display = self._draw_overlay()
            cv2.imshow(self.window_name, display)

            key = cv2.waitKey(30) & 0xFF

            # ESC أو Q = خروج
            if key in (27, ord("q"), ord("Q")):
                logger.info("⏹️  خروج بدون حفظ")
                break

            # S = حفظ
            elif key in (ord("s"), ord("S")):
                if self._validate_points():
                    self._save_calibration()
                    break
                else:
                    logger.warning("⚠️  لم يتم تحديد كل النقاط بعد")

            # R = إعادة الخطوة الأخيرة
            elif key in (ord("r"), ord("R")):
                if self._undo_stack:
                    key_prev, step_prev = self._undo_stack.pop()
                    self.points[key_prev] = None
                    self.current_step = step_prev
                    logger.info(f"↩️  إعادة: {key_prev}")

    # ========================================================
    # التحقق والحفظ
    # ========================================================

    def _validate_points(self) -> bool:
        """التحقق من أن كل النقاط محددة"""
        for key, _ in self.steps:
            if self.points[key] is None:
                logger.warning(f"⚠️  النقطة {key} غير محددة")
                return False
        return True

    def _save_calibration(self):
        """حساب الإعدادات وحفظها"""
        logger.info("💾 جاري حفظ المعايرة...")

        # ============================================================
        # 1) حساب إحداثيات اللوحة
        # ============================================================
        tl = self.points["board_tl"]
        tr = self.points["board_tr"]
        bl = self.points["board_bl"]
        br = self.points["board_br"]

        rows = BOARD_CONFIG.get("rows", 8)
        cols = BOARD_CONFIG.get("cols", 8)

        # عرض وارتفاع اللوحة الكلية
        board_width = ((tr[0] - tl[0]) + (br[0] - bl[0])) / 2
        board_height = ((bl[1] - tl[1]) + (br[1] - tr[1])) / 2

        # حجم الخلية
        cell_w = board_width / cols
        cell_h = board_height / rows
        cell_size = int(round((cell_w + cell_h) / 2))

        # نقطة البداية (مركز أول خلية)
        x_start = int(round(tl[0] + cell_w / 2))
        y_start = int(round(tl[1] + cell_h / 2))

        # تحديث الإعدادات
        BOARD_CONFIG["x_start"] = x_start
        BOARD_CONFIG["y_start"] = y_start
        BOARD_CONFIG["cell_size"] = cell_size

        logger.info(f"📐 اللوحة:")
        logger.info(f"   الحجم الكلي: {board_width:.0f} x {board_height:.0f} px")
        logger.info(f"   حجم الخلية: {cell_w:.1f} x {cell_h:.1f} px")
        logger.info(f"   حجم موحّد: {cell_size} px")
        logger.info(f"   نقطة البداية: ({x_start}, {y_start})")

        # ============================================================
        # 2) حساب إحداثيات القطع
        # ============================================================
        slots = []
        for i in range(1, 4):
            pos = self.points[f"slot_{i}"]
            if pos:
                slots.append((int(pos[0]), int(pos[1])))

        if len(slots) == 3:
            TRAY_CONFIG["slot_positions"] = slots
            logger.info(f"🎯 القطع:")
            for i, s in enumerate(slots, 1):
                logger.info(f"   قطعة {i}: {s}")

        # ============================================================
        # 3) تحديث CONFIG في الذاكرة
        # ============================================================
        try:
            CONFIG["calibrated"] = True
            CONFIG["cell_size"] = cell_size
            save_config()
        except Exception as e:
            logger.warning(f"⚠️  لم يتم تحديث CONFIG: {e}")
            # احفظ مباشرة
            self._write_config_file()

        logger.success("✅ تم حفظ المعايرة بنجاح!")

        # عرض ملخص
        print("\n" + "=" * 60)
        print("📋 ملخص المعايرة")
        print("=" * 60)
        print(f"اللوحة:")
        print(f"  حجم الخلية:   {cell_size} px")
        print(f"  البداية:      ({x_start}, {y_start})")
        print(f"  الشبكة:       {rows} × {cols}")
        print(f"\nالقطع:")
        for i, s in enumerate(slots, 1):
            print(f"  قطعة {i}:       {s}")
        print("=" * 60)

    def _write_config_file(self):
        """كتابة ملف config_saved.json مباشرة"""
        data = {
            "calibrated": True,
            "board": {
                "rows": BOARD_CONFIG.get("rows", 8),
                "cols": BOARD_CONFIG.get("cols", 8),
                "x_start": BOARD_CONFIG.get("x_start"),
                "y_start": BOARD_CONFIG.get("y_start"),
                "cell_size": BOARD_CONFIG.get("cell_size"),
            },
            "tray": {
                "slots": 3,
                "slot_positions": [
                    list(p) for p in TRAY_CONFIG.get("slot_positions", [])
                ],
            },
            "screen": {
                "width": SCREEN_CONFIG.get("width", 1080),
                "height": SCREEN_CONFIG.get("height", 2400),
            },
        }

        save_path = BASE_DIR / "config_saved.json"
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"📁 تم الحفظ في: {save_path}")

    # ========================================================
    # معايرة يدوية (بدون نافذة)
    # ========================================================

    def set_points_manually(self, **kwargs):
        """
        تحديد النقاط يدوياً بدون واجهة

        الاستخدام:
            calib = Calibration()
            calib.set_points_manually(
                board_tl=(100, 1100),
                board_tr=(980, 1100),
                board_bl=(100, 1980),
                board_br=(980, 1980),
                slot_1=(250, 2100),
                slot_2=(540, 2100),
                slot_3=(830, 2100),
            )
            calib._save_calibration()
        """
        for key, value in kwargs.items():
            if key in self.points:
                self.points[key] = value
                logger.debug(f"📍 {key} = {value}")

        self.current_step = len(self.steps)


# ============================================================
# اختبار سريع
# ============================================================

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from utils.logger import setup_logger, log_section

    setup_logger(level="DEBUG")
    log_section("اختبار Calibration")

    # محاولة الاتصال بالهاتف
    adb = None
    try:
        from core.adb_controller import ADBController
        adb = ADBController()
        if not adb.is_connected():
            logger.warning("⚠️  لا يوجد هاتف — استخدام صورة اختبار")
            adb = None
        else:
            logger.success("✅ الهاتف متصل")
    except Exception as e:
        logger.warning(f"⚠️  فشل الاتصال: {e}")
        adb = None

    # تشغيل المعايرة
    calib = Calibration(adb_controller=adb)

    try:
        calib.run_interactive()
    except KeyboardInterrupt:
        logger.info("\n⏹️  تم الإلغاء")
    except Exception as e:
        logger.exception(f"❌ خطأ: {e}")