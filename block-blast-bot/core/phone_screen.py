"""
Block Blast Bot - Phone Screen Interface
==========================================
واجهة موحّدة للتعامل مع شاشة الهاتف عبر USB
- قراءة الشاشة (ADB / scrcpy)
- معلومات الشاشة (الدقة، الاتجاه)
- إدارة USB
"""

import sys
import time
import subprocess
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
from datetime import datetime

import cv2
import numpy as np

from loguru import logger

try:
    from config import (
        CAPTURE_CONFIG, SCREEN_CONFIG, DEBUG_DIR, ADB_CONFIG,
    )
except ImportError:
    CAPTURE_CONFIG = {"method": "adb", "save_debug_frames": False}
    SCREEN_CONFIG = {"width": 1080, "height": 2400, "orientation": "portrait"}
    DEBUG_DIR = Path(__file__).parent.parent / "debug"
    ADB_CONFIG = {"adb_path": "adb"}


# ============================================================
# كلاس واجهة شاشة الهاتف
# ============================================================

class PhoneScreen:
    """
    واجهة موحّدة للتعامل مع شاشة الهاتف عبر USB

    الاستخدام:
        phone = PhoneScreen(adb)
        frame = phone.read()
        info = phone.get_info()
    """

    def __init__(self, adb_controller, method: str = None):
        """
        Args:
            adb_controller: نسخة ADBController
            method: طريقة الالتقاط ("adb" أو "scrcpy")
        """
        self.adb = adb_controller
        self.method = method or CAPTURE_CONFIG.get("method", "adb")

        # معلومات الشاشة (تُملأ عند الاتصال)
        self.width: int = SCREEN_CONFIG.get("width", 1080)
        self.height: int = SCREEN_CONFIG.get("height", 2400)
        self.orientation: str = SCREEN_CONFIG.get("orientation", "portrait")

        # إحصائيات
        self._read_count = 0
        self._read_times: list = []
        self._last_read_ms: float = 0.0

        # آخر إطار
        self._last_frame: Optional[np.ndarray] = None

        # قراءة معلومات الشاشة من الهاتف
        self._refresh_screen_info()

        logger.debug(
            f"📱 PhoneScreen جاهز — "
            f"{self.width}x{self.height} ({self.orientation}), "
            f"method={self.method}"
        )

    # ========================================================
    # معلومات الشاشة
    # ========================================================

    def _refresh_screen_info(self):
        """قراءة دقة الشاشة من الهاتف"""
        try:
            info = self.adb.get_device_info()
            self.width = info.get("width", self.width)
            self.height = info.get("height", self.height)

            # تحديد الاتجاه
            if self.width > self.height:
                self.orientation = "landscape"
            else:
                self.orientation = "portrait"

        except Exception as e:
            logger.debug(f"لا يمكن قراءة معلومات الشاشة: {e}")

    def get_info(self) -> Dict[str, Any]:
        """إرجاع معلومات الشاشة الحالية"""
        return {
            "width": self.width,
            "height": self.height,
            "orientation": self.orientation,
            "method": self.method,
            "reads": self._read_count,
            "last_read_ms": round(self._last_read_ms, 1),
        }

    @property
    def size(self) -> Tuple[int, int]:
        """(width, height)"""
        return self.width, self.height

    @property
    def aspect_ratio(self) -> float:
        """النسبة بين العرض والارتفاع"""
        if self.height == 0:
            return 0.0
        return self.width / self.height

    # ========================================================
    # القراءة الرئيسية
    # ========================================================

    def read(self, save_debug: bool = False) -> Optional[np.ndarray]:
        """
        قراءة إطار من الشاشة

        Args:
            save_debug: حفظ الصورة في مجلد debug

        Returns:
            صورة OpenCV أو None عند الفشل
        """
        if self.method == "scrcpy":
            frame = self._read_scrcpy()
        else:
            frame = self._read_adb()

        if frame is None:
            return None

        self._read_count += 1
        self._last_frame = frame

        # تحقق من الدقة (لو تغيرت)
        h, w = frame.shape[:2]
        if w != self.width or h != self.height:
            logger.debug(f"🔄 تغيرت دقة الشاشة: {self.width}x{self.height} → {w}x{h}")
            self.width = w
            self.height = h

        # حفظ تلقائي
        if save_debug:
            self.save_frame(frame)

        return frame

    # ========================================================
    # الطرق المختلفة
    # ========================================================

    def _read_adb(self) -> Optional[np.ndarray]:
        """قراءة عبر ADB screencap"""
        start = time.perf_counter()

        png_bytes = self.adb._run(
            ["exec-out", "screencap", "-p"],
            binary=True,
        )

        if not png_bytes or len(png_bytes) < 100:
            logger.warning("⚠️  بيانات فارغة من screencap")
            return None

        try:
            arr = np.frombuffer(png_bytes, dtype=np.uint8)
            frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        except Exception as e:
            logger.error(f"❌ خطأ في فك ترميز الصورة: {e}")
            return None

        if frame is None:
            return None

        elapsed_ms = (time.perf_counter() - start) * 1000
        self._last_read_ms = elapsed_ms
        self._read_times.append(elapsed_ms)
        if len(self._read_times) > 50:
            self._read_times.pop(0)

        return frame

    def _read_scrcpy(self) -> Optional[np.ndarray]:
        """قراءة عبر scrcpy (fallback إلى ADB)"""
        return self._read_adb()

    # ========================================================
    # مناطق الشاشة
    # ========================================================

    def read_region(
        self,
        x: int, y: int,
        w: int, h: int,
    ) -> Optional[np.ndarray]:
        """
        قراءة منطقة محددة من الشاشة

        Args:
            x, y: الزاوية العلوية اليسرى
            w, h: العرض والارتفاع

        Returns:
            صورة المنطقة أو None
        """
        frame = self.read()
        if frame is None:
            return None

        # التحقق من الحدود
        fh, fw = frame.shape[:2]
        x1 = max(0, x)
        y1 = max(0, y)
        x2 = min(fw, x + w)
        y2 = min(fh, y + h)

        return frame[y1:y2, x1:x2]

    def read_center_region(
        self,
        w: int, h: int,
    ) -> Optional[np.ndarray]:
        """قراءة منطقة في المنتصف"""
        cx = self.width // 2
        cy = self.height // 2
        x = cx - w // 2
        y = cy - h // 2
        return self.read_region(x, y, w, h)

    # ========================================================
    # الحفظ
    # ========================================================

    def save_frame(
        self,
        frame: np.ndarray,
        prefix: str = "phone_screen",
    ) -> Optional[str]:
        """حفظ إطار في مجلد debug"""
        try:
            DEBUG_DIR.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            filename = f"{prefix}_{timestamp}.png"
            path = DEBUG_DIR / filename

            cv2.imwrite(str(path), frame)
            logger.debug(f"💾 حفظ: {filename}")

            return str(path)

        except Exception as e:
            logger.warning(f"⚠️  فشل الحفظ: {e}")
            return None

    def save_last(self, prefix: str = "last_frame") -> Optional[str]:
        """حفظ آخر إطار تم قراءته"""
        if self._last_frame is None:
            logger.warning("⚠️  لا يوجد إطار محفوظ")
            return None
        return self.save_frame(self._last_frame, prefix)

    # ========================================================
    # التسجيل (فيديو)
    # ========================================================

    def record(
        self,
        duration_sec: int = 5,
        fps: int = 5,
        filename: str = None,
    ) -> Optional[str]:
        """
        تسجيل فيديو من الشاشة

        Args:
            duration_sec: المدة
            fps: الإطارات/ثانية
            filename: اسم الملف (اختياري)

        Returns:
            مسار الفيديو أو None
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"record_{timestamp}.mp4"

        DEBUG_DIR.mkdir(parents=True, exist_ok=True)
        path = DEBUG_DIR / filename
        frames = []
        delay = 1.0 / fps
        total = duration_sec * fps

        logger.info(f"🎥 بدء تسجيل {duration_sec}s ({fps}fps)...")

        try:
            for i in range(total):
                frame = self.read()
                if frame is not None:
                    frames.append(frame)
                time.sleep(delay)

            if not frames:
                logger.error("❌ لا يوجد إطارات")
                return None

            h, w = frames[0].shape[:2]
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(str(path), fourcc, fps, (w, h))

            for f in frames:
                writer.write(f)
            writer.release()

            logger.success(f"✅ تم: {path}")
            return str(path)

        except Exception as e:
            logger.exception(f"❌ فشل التسجيل: {e}")
            return None

    # ========================================================
    # فحوصات USB
    # ========================================================

    def is_connected(self) -> bool:
        """هل الهاتف متصل؟"""
        return self.adb.is_connected()

    def is_screen_on(self) -> bool:
        """هل الشاشة مضاءة؟"""
        return self.adb.is_screen_on()

    def wake(self):
        """إيقاظ الشاشة"""
        self.adb.wake_screen()

    def ensure_awake(self) -> bool:
        """ضمان أن الشاشة مضاءة"""
        if not self.is_screen_on():
            logger.info("💡 الشاشة مغلقة — إيقاظ...")
            self.wake()
            time.sleep(1)
            return self.is_screen_on()
        return True

    # ========================================================
    # إحصائيات
    # ========================================================

    def stats(self) -> Dict[str, Any]:
        """إحصائيات القراءة"""
        avg = 0.0
        if self._read_times:
            avg = sum(self._read_times) / len(self._read_times)

        return {
            "total_reads": self._read_count,
            "avg_read_ms": round(avg, 1),
            "last_read_ms": round(self._last_read_ms, 1),
            "min_read_ms": round(min(self._read_times), 1) if self._read_times else 0,
            "max_read_ms": round(max(self._read_times), 1) if self._read_times else 0,
            "size": f"{self.width}x{self.height}",
            "orientation": self.orientation,
        }

    def reset_stats(self):
        """تصفير الإحصائيات"""
        self._read_count = 0
        self._read_times.clear()
        self._last_read_ms = 0.0


# ============================================================
# اختبار سريع
# ============================================================

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from utils.logger import setup_logger, log_section
    from core.adb_controller import ADBController

    setup_logger(level="DEBUG")
    log_section("اختبار Phone Screen")

    try:
        # الاتصال
        adb = ADBController()
        if not adb.is_connected():
            logger.error("❌ لا يوجد هاتف متصل!")
            raise SystemExit(1)

        logger.success("✅ الهاتف متصل")

        # إنشاء الواجهة
        phone = PhoneScreen(adb)

        # 1) معلومات الشاشة
        print("\n" + "=" * 60)
        print("📱 معلومات الشاشة")
        print("=" * 60)
        info = phone.get_info()
        for k, v in info.items():
            print(f"  {k}: {v}")

        # 2) ضمان أن الشاشة مضاءة
        if not phone.ensure_awake():
            logger.warning("⚠️  الشاشة لا تزال مغلقة")

        # 3) قراءة إطار
        print("\n📸 قراءة إطار...")
        frame = phone.read(save_debug=True)

        if frame is None:
            logger.error("❌ فشل القراءة")
            raise SystemExit(1)

        h, w = frame.shape[:2]
        logger.success(f"✅ إطار: {w}x{h}")

        # 4) قراءة سريعة (5 مرات)
        print("\n⚡ 5 قراءات سريعة...")
        for i in range(5):
            start = time.perf_counter()
            _ = phone.read()
            elapsed = (time.perf_counter() - start) * 1000
            print(f"   قراءة {i + 1}: {elapsed:.0f}ms")

        # 5) قراءة منطقة محددة
        print("\n✂️  قراءة منطقة مركزية (400x400)...")
        region = phone.read_center_region(400, 400)
        if region is not None:
            phone.save_frame(region, "center_region")
            print(f"   ✅ الحجم: {region.shape}")

        # 6) الإحصائيات
        print("\n📊 إحصائيات القراءة:")
        stats = phone.stats()
        for k, v in stats.items():
            print(f"   {k}: {v}")

        log_section("انتهى الاختبار بنجاح", char="-")

    except KeyboardInterrupt:
        logger.info("\n⏹️  تم الإلغاء")
    except Exception as e:
        logger.exception(f"❌ خطأ: {e}")