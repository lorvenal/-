"""
Block Blast Bot - Screen Capture
=================================
التقاط صور من شاشة الهاتف عبر USB
يدعم طريقتين: ADB (بسيط) و scrcpy (سريع)
"""

import sys
import time
import subprocess
from pathlib import Path
from typing import Optional
from datetime import datetime

import cv2
import numpy as np

from loguru import logger

try:
    from config import CAPTURE_CONFIG, DEBUG_DIR, SCREEN_CONFIG
except ImportError:
    CAPTURE_CONFIG = {
        "method": "adb",
        "format": "png",
        "save_debug_frames": False,
        "debug_frames_limit": 100,
    }
    DEBUG_DIR = Path(__file__).parent.parent / "debug"
    SCREEN_CONFIG = {"width": 1080, "height": 2400}


# ============================================================
# كلاس التقاط الشاشة
# ============================================================

class ScreenCapture:
    """التقاط صور من شاشة الهاتف"""

    def __init__(self, adb_controller, method: str = None):
        """
        Args:
            adb_controller: نسخة من ADBController
            method: طريقة الالتقاط ("adb" أو "scrcpy")
        """
        self.adb = adb_controller
        self.method = method or CAPTURE_CONFIG["method"]

        # عدّاد الصور (للتشخيص)
        self._frame_count = 0
        self._save_debug = CAPTURE_CONFIG["save_debug_frames"]
        self._debug_limit = CAPTURE_CONFIG["debug_frames_limit"]

        # إحصائيات
        self._capture_times: list = []
        self._last_capture_ms = 0.0

        # التحقق من الطريقة
        if self.method == "scrcpy":
            if not self._check_scrcpy():
                logger.warning("⚠️  scrcpy غير متاح، التبديل إلى adb")
                self.method = "adb"

        logger.debug(f"📸 ScreenCapture جاهز (الطريقة: {self.method})")

    # ========================================================
    # التحقق من scrcpy
    # ========================================================

    @staticmethod
    def _check_scrcpy() -> bool:
        """هل scrcpy مثبت؟"""
        try:
            result = subprocess.run(
                ["scrcpy", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    # ========================================================
    # الطريقة 1: ADB (بسيطة وموثوقة)
    # ========================================================

    def _grab_adb(self) -> Optional[np.ndarray]:
        """
        التقاط الشاشة عبر ADB
        يستخدم: adb exec-out screencap -p
        """
        start = time.perf_counter()

        # نطلب الصورة كبيانات ثنائية (raw PNG bytes)
        png_bytes = self.adb._run(
            ["exec-out", "screencap", "-p"],
            binary=True,
        )

        if not png_bytes or len(png_bytes) < 100:
            logger.warning("⚠️  فشل التقاط الشاشة (بيانات فارغة)")
            return None

        # تحويل bytes → numpy array → OpenCV image
        try:
            arr = np.frombuffer(png_bytes, dtype=np.uint8)
            frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        except Exception as e:
            logger.error(f"❌ خطأ في فك ترميز الصورة: {e}")
            return None

        if frame is None:
            logger.warning("⚠️  cv2.imdecode أعاد None")
            return None

        # قياس الزمن
        elapsed_ms = (time.perf_counter() - start) * 1000
        self._last_capture_ms = elapsed_ms
        self._capture_times.append(elapsed_ms)
        if len(self._capture_times) > 50:
            self._capture_times.pop(0)

        return frame

    # ========================================================
    # الطريقة 2: scrcpy (fallback إلى ADB)
    # ========================================================

    def _grab_scrcpy(self) -> Optional[np.ndarray]:
        """التقاط الشاشة عبر scrcpy (مبسّط — يعود لـ ADB)"""
        logger.debug("scrcpy غير مُفعّل بالكامل، استخدام ADB")
        return self._grab_adb()

    # ========================================================
    # الواجهة الرئيسية
    # ========================================================

    def grab(self, save_debug: bool = False) -> Optional[np.ndarray]:
        """
        التقاط إطار واحد من الشاشة

        Args:
            save_debug: حفظ الصورة في مجلد debug/

        Returns:
            صورة OpenCV (numpy array) أو None عند الفشل
        """
        if self.method == "scrcpy":
            frame = self._grab_scrcpy()
        else:
            frame = self._grab_adb()

        if frame is None:
            return None

        self._frame_count += 1

        # حفظ تلقائي إن مُفعّل
        if save_debug or (
            self._save_debug and self._frame_count <= self._debug_limit
        ):
            self._save_frame(frame)

        return frame

    def grab_and_verify(self, expected_size: bool = True) -> Optional[np.ndarray]:
        """
        التقاط مع التحقق من الحجم

        Args:
            expected_size: التحقق من مطابقة الحجم المتوقع
        """
        frame = self.grab()
        if frame is None:
            return None

        if expected_size:
            h, w = frame.shape[:2]
            expected_w = SCREEN_CONFIG["width"]
            expected_h = SCREEN_CONFIG["height"]

            if w != expected_w or h != expected_h:
                logger.warning(
                    f"⚠️  حجم الصورة ({w}x{h}) مختلف عن المتوقع "
                    f"({expected_w}x{expected_h})"
                )
                # تحديث الإعدادات تلقائياً
                SCREEN_CONFIG["width"] = w
                SCREEN_CONFIG["height"] = h

        return frame

    # ========================================================
    # حفظ الصور
    # ========================================================

    def _save_frame(self, frame: np.ndarray, prefix: str = "frame"):
        """حفظ إطار في مجلد debug"""
        try:
            DEBUG_DIR.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            filename = f"{prefix}_{timestamp}.png"
            path = DEBUG_DIR / filename
            cv2.imwrite(str(path), frame)
            logger.trace(f"💾 حفظ: {filename}")
        except Exception as e:
            logger.warning(f"⚠️  فشل حفظ الصورة: {e}")

    def save(self, frame: np.ndarray, filename: str) -> bool:
        """
        حفظ إطار باسم محدد

        Args:
            frame: الصورة
            filename: اسم الملف (بدون مسار)
        """
        try:
            DEBUG_DIR.mkdir(parents=True, exist_ok=True)
            path = DEBUG_DIR / filename
            cv2.imwrite(str(path), frame)
            logger.info(f"💾 حفظ: {path}")
            return True
        except Exception as e:
            logger.error(f"❌ فشل الحفظ: {e}")
            return False

    # ========================================================
    # التسجيل (فيديو)
    # ========================================================

    def record_video(
        self,
        duration_sec: int = 5,
        fps: int = 5,
        filename: str = None,
    ):
        """
        تسجيل فيديو قصير من الشاشة

        Args:
            duration_sec: مدة التسجيل بالثواني
            fps: عدد الإطارات في الثانية
            filename: اسم الملف (اختياري)
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"recording_{timestamp}.mp4"

        DEBUG_DIR.mkdir(parents=True, exist_ok=True)
        path = DEBUG_DIR / filename
        delay = 1.0 / fps
        frames = []
        total = duration_sec * fps

        logger.info(f"🎥 بدء التسجيل ({duration_sec}s, {fps}fps)...")

        try:
            for i in range(total):
                frame = self.grab()
                if frame is not None:
                    frames.append(frame)
                time.sleep(delay)

            if not frames:
                logger.error("❌ لم يتم التقاط أي إطار")
                return None

            # حفظ الفيديو
            h, w = frames[0].shape[:2]
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(str(path), fourcc, fps, (w, h))

            for frame in frames:
                writer.write(frame)
            writer.release()

            logger.success(f"✅ تم حفظ الفيديو: {path} ({len(frames)} إطار)")
            return str(path)

        except Exception as e:
            logger.exception(f"❌ فشل التسجيل: {e}")
            return None

    # ========================================================
    # إحصائيات الأداء
    # ========================================================

    def stats(self) -> dict:
        """إحصائيات الالتقاط"""
        if not self._capture_times:
            return {
                "frames": self._frame_count,
                "avg_ms": 0,
                "min_ms": 0,
                "max_ms": 0,
            }

        return {
            "frames": self._frame_count,
            "avg_ms": round(sum(self._capture_times) / len(self._capture_times), 1),
            "min_ms": round(min(self._capture_times), 1),
            "max_ms": round(max(self._capture_times), 1),
            "last_ms": round(self._last_capture_ms, 1),
        }

    def reset_stats(self):
        """تصفير الإحصائيات"""
        self._capture_times.clear()
        self._frame_count = 0

    # ========================================================
    # أدوات مساعدة
    # ========================================================

    def grab_gray(self) -> Optional[np.ndarray]:
        """التقاط صورة رمادية (أسرع للمعالجة)"""
        frame = self.grab()
        if frame is None:
            return None
        return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    def grab_crop(
        self,
        x1: int, y1: int,
        x2: int, y2: int,
    ) -> Optional[np.ndarray]:
        """التقاط منطقة محددة فقط"""
        frame = self.grab()
        if frame is None:
            return None
        return frame[y1:y2, x1:x2]

    def grab_region(
        self,
        x: int, y: int,
        w: int, h: int,
    ) -> Optional[np.ndarray]:
        """التقاط منطقة بإحداثيات x,y,width,height"""
        return self.grab_crop(x, y, x + w, y + h)


# ============================================================
# اختبار سريع
# ============================================================

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from utils.logger import setup_logger, log_section, log_time
    from core.adb_controller import ADBController

    setup_logger(level="DEBUG")
    log_section("اختبار Screen Capture")

    try:
        # 1) الاتصال
        adb = ADBController()
        if not adb.is_connected():
            logger.error("❌ لا يوجد هاتف متصل!")
            raise SystemExit(1)

        logger.success("✅ الهاتف متصل")

        # 2) إنشاء كائن الالتقاط
        capture = ScreenCapture(adb)
        logger.success(f"✅ ScreenCapture جاهز (الطريقة: {capture.method})")

        # 3) التقاط إطار واحد
        logger.info("\n📸 اختبار التقاط واحد...")
        with log_time("التقاط إطار"):
            frame = capture.grab()

        if frame is None:
            logger.error("❌ فشل الالتقاط")
            raise SystemExit(1)

        h, w = frame.shape[:2]
        logger.success(f"✅ تم الالتقاط: {w}x{h}, dtype={frame.dtype}")

        # 4) حفظ الصورة
        capture.save(frame, "test_capture.png")
        logger.info(f"📁 الصورة محفوظة في: {DEBUG_DIR}/test_capture.png")

        # 5) اختبار الالتقاط السريع (5 مرات)
        logger.info("\n⚡ اختبار الالتقاط السريع (5 مرات)...")
        for i in range(5):
            with log_time(f"التقاط {i + 1}"):
                _ = capture.grab()

        # 6) الإحصائيات
        stats = capture.stats()
        print("\n📊 إحصائيات الالتقاط:")
        print(f"   عدد الإطارات:   {stats['frames']}")
        print(f"   متوسط الزمن:    {stats['avg_ms']} ms")
        print(f"   أسرع:           {stats['min_ms']} ms")
        print(f"   أبطأ:           {stats['max_ms']} ms")

        # 7) اختبار منطقة محددة
        logger.info("\n✂️  اختبار التقاط منطقة محددة (100,100) → (500,500)...")
        region = capture.grab_region(100, 100, 400, 400)
        if region is not None:
            capture.save(region, "test_region.png")
            logger.success(f"✅ المنطقة: {region.shape}")

        log_section("انتهى الاختبار بنجاح", char="-")
        logger.info(f"\n📁 تحقق من الصور في: {DEBUG_DIR}")

    except KeyboardInterrupt:
        logger.info("\n⏹️  تم الإلغاء")
    except Exception as e:
        logger.exception(f"❌ خطأ: {e}")