"""
Block Blast Bot - ADB Controller
=================================
التواصل مع الهاتف عبر USB باستخدام ADB (Android Debug Bridge)
يوفر: الأوامر، اللمس، السحب، معلومات الجهاز، لقطات الشاشة
"""

import subprocess
import re
import time
import shutil
from typing import Optional, Tuple, Dict, Any, List

from loguru import logger

try:
    from config import ADB_CONFIG, SCREEN_CONFIG
except ImportError:
    ADB_CONFIG = {
        "adb_path": "adb",
        "command_timeout": 10,
        "tap_duration": 50,
        "swipe_duration": 350,
        "retry_attempts": 3,
        "retry_delay": 0.5,
    }
    SCREEN_CONFIG = {"width": 1080, "height": 2400}


# ============================================================
# كلاس التحكم بـ ADB
# ============================================================

class ADBController:
    """التحكم الكامل بالهاتف عبر ADB"""

    def __init__(self, adb_path: str = None, device_serial: str = None):
        """
        Args:
            adb_path: مسار adb (افتراضي من config)
            device_serial: رقم الجهاز (إن كان هناك أكثر من جهاز)
        """
        self.adb_path = adb_path or ADB_CONFIG["adb_path"]
        self.device_serial = device_serial
        self.timeout = ADB_CONFIG["command_timeout"]
        self._device_info: Optional[Dict[str, Any]] = None

        # التحقق من وجود adb
        if not self._check_adb_exists():
            raise RuntimeError(
                "❌ لم يتم العثور على adb!\n"
                "   تأكد من تثبيته وإضافته إلى PATH\n"
                "   أو حدّد مساره في config.py → ADB_CONFIG['adb_path']"
            )

    # ========================================================
    # التحقق والتشغيل
    # ========================================================

    def _check_adb_exists(self) -> bool:
        """التحقق من وجود adb في النظام"""
        try:
            result = subprocess.run(
                [self.adb_path, "version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def _build_command(self, args: list) -> list:
        """بناء أمر adb كامل"""
        cmd = [self.adb_path]
        if self.device_serial:
            cmd.extend(["-s", self.device_serial])
        cmd.extend(args)
        return cmd

    def _run(
        self,
        args: list,
        binary: bool = False,
        timeout: Optional[int] = None,
    ) -> Optional[Any]:
        """
        تشغيل أمر adb

        Args:
            args: قائمة المعاملات (بدون "adb")
            binary: هل الناتج بيانات ثنائية (مثل صورة)؟
            timeout: مهلة مخصصة

        Returns:
            str أو bytes أو None عند الفشل
        """
        cmd = self._build_command(args)
        timeout = timeout or self.timeout

        for attempt in range(1, ADB_CONFIG["retry_attempts"] + 1):
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    timeout=timeout,
                )

                if result.returncode != 0:
                    err = result.stderr.decode("utf-8", errors="ignore").strip()
                    logger.warning(f"⚠️  adb فشل (محاولة {attempt}): {err}")
                    if attempt < ADB_CONFIG["retry_attempts"]:
                        time.sleep(ADB_CONFIG["retry_delay"])
                        continue
                    return None

                if binary:
                    return result.stdout
                return result.stdout.decode("utf-8", errors="ignore").strip()

            except subprocess.TimeoutExpired:
                logger.warning(f"⏱️  انتهت مهلة adb (محاولة {attempt})")
                if attempt < ADB_CONFIG["retry_attempts"]:
                    time.sleep(ADB_CONFIG["retry_delay"])
            except Exception as e:
                logger.error(f"❌ خطأ في تشغيل adb: {e}")
                return None

        return None

    # ========================================================
    # معلومات الجهاز
    # ========================================================

    def is_connected(self) -> bool:
        """هل هناك جهاز متصل؟"""
        output = self._run(["devices"])
        if not output:
            return False

        # تنسيق: "List of devices attached\n<serial>\tdevice"
        lines = output.strip().split("\n")[1:]
        for line in lines:
            parts = line.strip().split("\t")
            if len(parts) >= 2 and parts[1] == "device":
                if not self.device_serial:
                    self.device_serial = parts[0]
                return True
        return False

    def get_device_info(self, force_refresh: bool = False) -> Dict[str, Any]:
        """الحصول على معلومات الجهاز (تُخزَّن مؤقتاً)"""
        if self._device_info and not force_refresh:
            return self._device_info

        info = {
            "serial": self.device_serial or "unknown",
            "model": "Unknown",
            "android_version": "Unknown",
            "width": SCREEN_CONFIG["width"],
            "height": SCREEN_CONFIG["height"],
            "density": 0,
        }

        # اسم الموديل
        model = self._run(["shell", "getprop", "ro.product.model"])
        if model:
            info["model"] = model

        # إصدار Android
        version = self._run(["shell", "getprop", "ro.build.version.release"])
        if version:
            info["android_version"] = version

        # دقة الشاشة
        size = self._run(["shell", "wm", "size"])
        if size:
            # تنسيق: "Physical size: 1080x2400"
            match = re.search(r"(\d+)x(\d+)", size)
            if match:
                info["width"] = int(match.group(1))
                info["height"] = int(match.group(2))
                # تحديث الإعدادات
                SCREEN_CONFIG["width"] = info["width"]
                SCREEN_CONFIG["height"] = info["height"]

        # الكثافة
        density = self._run(["shell", "wm", "density"])
        if density:
            match = re.search(r"(\d+)", density)
            if match:
                info["density"] = int(match.group(1))

        self._device_info = info
        return info

    # ========================================================
    # أوامر Shell
    # ========================================================

    def shell(self, command: str, binary: bool = False) -> Optional[Any]:
        """تنفيذ أمر shell على الهاتف"""
        return self._run(["shell", command], binary=binary)

    def current_app(self) -> Optional[str]:
        """اسم الحزمة الحالية (ما اللعبة المفتوحة الآن؟)"""
        output = self._run([
            "shell", "dumpsys", "window", "windows",
        ])

        if not output:
            return None

        # ابحث عن mCurrentFocus
        for line in output.split("\n"):
            if "mCurrentFocus" in line:
                match = re.search(r"u0\s+([\w\.]+)/", line)
                if match:
                    return match.group(1)
                # بديل: استخراج اسم الحزمة
                match = re.search(r"([a-z][\w\.]+\.[\w\.]+)/", line)
                if match:
                    return match.group(1)
        return None

    def is_screen_on(self) -> bool:
        """هل الشاشة مضاءة؟"""
        output = self._run([
            "shell",
            "dumpsys", "power",
        ])
        if output and "mWakefulness=Awake" in output:
            return True
        return False

    def wake_screen(self):
        """إيقاظ الشاشة"""
        self._run(["shell", "input", "keyevent", "KEYCODE_WAKEUP"])

    # ========================================================
    # اللمس والسحب
    # ========================================================

    def tap(self, x: int, y: int, duration: int = None):
        """
        نقرة على إحداثيات محددة

        Args:
            x, y: الإحداثيات بالبكسل
            duration: مدة اللمس (ms)
        """
        duration = duration or ADB_CONFIG["tap_duration"]
        x, y = int(x), int(y)

        if duration <= 100:
            # نقرة سريعة
            self._run(["shell", "input", "tap", str(x), str(y)])
        else:
            # ضغط مطوّل
            self._run([
                "shell", "input", "swipe",
                str(x), str(y), str(x), str(y), str(duration),
            ])

        logger.debug(f"👆 نقرة على ({x}, {y}) - {duration}ms")

    def swipe(
        self,
        x1: int, y1: int,
        x2: int, y2: int,
        duration: int = None,
    ):
        """
        سحب من نقطة إلى نقطة

        Args:
            x1, y1: نقطة البداية
            x2, y2: نقطة النهاية
            duration: مدة السحب (ms)
        """
        duration = duration or ADB_CONFIG["swipe_duration"]
        x1, y1 = int(x1), int(y1)
        x2, y2 = int(x2), int(y2)

        self._run([
            "shell", "input", "swipe",
            str(x1), str(y1),
            str(x2), str(y2),
            str(duration),
        ])

        logger.debug(
            f"👉 سحب من ({x1}, {y1}) إلى ({x2}, {y2}) - {duration}ms"
        )

    def drag_and_drop(
        self,
        x1: int, y1: int,
        x2: int, y2: int,
        duration: int = None,
    ):
        """
        سحب وإفلات (لتحريك القطع في Block Blast)
        """
        duration = duration or ADB_CONFIG["swipe_duration"]

        # سحب بطيء
        self._run([
            "shell", "input", "swipe",
            str(x1), str(y1),
            str(x2), str(y2),
            str(duration),
        ])

        # تأخير بسيط للإفلات
        time.sleep(0.05)

        logger.debug(
            f"🎯 سحب القطعة من ({x1}, {y1}) إلى ({x2}, {y2})"
        )

    def long_press(self, x: int, y: int, duration: int = 800):
        """ضغط مطوّل"""
        self.tap(x, y, duration=duration)

    # ========================================================
    # الأزرار الفيزيائية
    # ========================================================

    def press_back(self):
        """زر الرجوع"""
        self._run(["shell", "input", "keyevent", "KEYCODE_BACK"])

    def press_home(self):
        """زر الرئيسية"""
        self._run(["shell", "input", "keyevent", "KEYCODE_HOME"])

    def press_power(self):
        """زر الطاقة"""
        self._run(["shell", "input", "keyevent", "KEYCODE_POWER"])

    def press_key(self, keycode: str):
        """زر مخصص"""
        self._run(["shell", "input", "keyevent", keycode])

    # ========================================================
    # التطبيقات
    # ========================================================

    def launch_app(self, package: str) -> bool:
        """تشغيل تطبيق بالاسم"""
        result = self._run([
            "shell", "monkey",
            "-p", package,
            "-c", "android.intent.category.LAUNCHER",
            "1",
        ])
        if result and "No activities found" not in result:
            logger.info(f"🚀 تم تشغيل {package}")
            return True
        logger.warning(f"⚠️  فشل تشغيل {package}")
        return False

    def stop_app(self, package: str):
        """إيقاف تطبيق"""
        self._run(["shell", "am", "force-stop", package])

    def list_packages(self, filter_str: str = "") -> List[str]:
        """قائمة الحزم المثبتة"""
        output = self._run(["shell", "pm", "list", "packages"])
        if not output:
            return []

        packages = [
            line.replace("package:", "").strip()
            for line in output.split("\n")
            if line.startswith("package:")
        ]

        if filter_str:
            packages = [p for p in packages if filter_str.lower() in p.lower()]

        return packages

    def find_game_package(self) -> Optional[str]:
        """محاولة إيجاد حزمة Block Blast تلقائياً"""
        # أسماء محتملة
        candidates = [
            "com.blockblast",
            "com.hungrystudio.blockblast",
            "com.block.juggle",
            "block.blast",
        ]

        packages = self.list_packages()

        # البحث الدقيق
        for pkg in packages:
            pkg_lower = pkg.lower()
            for cand in candidates:
                if cand in pkg_lower:
                    logger.info(f"🎮 تم إيجاد اللعبة: {pkg}")
                    return pkg

        # البحث بالكلمات المفتاحية
        for pkg in packages:
            pkg_lower = pkg.lower()
            if "block" in pkg_lower and ("blast" in pkg_lower or "puzzle" in pkg_lower):
                logger.info(f"🎮 تم إيجاد اللعبة (تقريبي): {pkg}")
                return pkg

        return None

    # ========================================================
    # معلومات إضافية
    # ========================================================

    def get_battery(self) -> Optional[int]:
        """نسبة البطارية"""
        output = self._run(["shell", "dumpsys", "battery"])
        if output:
            match = re.search(r"level:\s*(\d+)", output)
            if match:
                return int(match.group(1))
        return None

    def get_current_activity(self) -> Optional[str]:
        """النشاط الحالي"""
        return self.current_app()

    def take_screenshot_to_file(self, remote_path: str = "/sdcard/screen.png") -> bool:
        """التقاط صورة وحفظها على الهاتف"""
        result = self._run([
            "shell", "screencap", "-p", remote_path,
        ])
        return result is not None

    def pull_file(self, remote: str, local: str) -> bool:
        """سحب ملف من الهاتف إلى اللابتوب"""
        result = self._run(["pull", remote, local], timeout=30)
        return result is not None

    # ========================================================
    # الاتصال
    # ========================================================

    def connect_wifi(self, ip: str, port: int = 5555) -> bool:
        """الاتصال بالهاتف عبر WiFi (اختياري)"""
        output = self._run(["connect", f"{ip}:{port}"])
        if output and "connected" in output.lower():
            self.device_serial = f"{ip}:{port}"
            logger.success(f"✅ متصل عبر WiFi: {ip}:{port}")
            return True
        return False

    def disconnect(self):
        """قطع الاتصال (WiFi فقط)"""
        if self.device_serial and ":" in self.device_serial:
            self._run(["disconnect", self.device_serial])
            logger.info(f"🔌 تم قطع الاتصال بـ {self.device_serial}")


# ============================================================
# اختبار سريع
# ============================================================

if __name__ == "__main__":
    from utils.logger import setup_logger, log_section

    setup_logger(level="DEBUG")

    log_section("اختبار ADB Controller")

    try:
        adb = ADBController()
        logger.success("✅ تم إنشاء ADBController")

        # 1) هل متصل؟
        if not adb.is_connected():
            logger.error("❌ لا يوجد هاتف متصل!")
            logger.info("تأكد من:")
            logger.info("  1. تفعيل USB Debugging")
            logger.info("  2. توصيل الكابل")
            logger.info("  3. الموافقة على نافذة السماح في الهاتف")
            raise SystemExit(1)

        logger.success("✅ الهاتف متصل")

        # 2) معلومات الجهاز
        info = adb.get_device_info()
        print("\n📱 معلومات الجهاز:")
        for k, v in info.items():
            print(f"   {k:20s}: {v}")

        # 3) حالة الشاشة
        print(f"\n💡 الشاشة مضاءة: {adb.is_screen_on()}")

        # 4) البطارية
        battery = adb.get_battery()
        if battery is not None:
            print(f"🔋 البطارية: {battery}%")

        # 5) التطبيق الحالي
        current = adb.current_app()
        print(f"📲 التطبيق الحالي: {current}")

        # 6) البحث عن اللعبة
        print("\n🎮 البحث عن Block Blast...")
        pkg = adb.find_game_package()
        if pkg:
            print(f"   ✅ تم إيجادها: {pkg}")
        else:
            print("   ❌ لم يتم إيجادها - جرّب البحث اليدوي:")
            print("      adb shell pm list packages | grep -i block")

        # 7) اختبار لمسة
        print("\n🧪 اختبار اللمس على (500, 500)...")
        print("   ⚠️  سيتم لمس منتصف الشاشة - احذر!")

        response = input("   هل تريد المتابعة؟ (y/n): ").strip().lower()
        if response == "y":
            adb.tap(500, 500)
            logger.success("✅ تم تنفيذ اللمسة")

        log_section("انتهى الاختبار بنجاح", char="-")

    except RuntimeError as e:
        logger.error(str(e))
        logger.info("\n💡 لتثبيت ADB:")
        logger.info("   Ubuntu/Debian: sudo apt install adb")
        logger.info("   Mac:           brew install android-platform-tools")
        logger.info("   Windows:       حمّله من developer.android.com")
    except KeyboardInterrupt:
        logger.info("\n⏹️  تم الإلغاء")
    except Exception as e:
        logger.exception(f"❌ خطأ: {e}")