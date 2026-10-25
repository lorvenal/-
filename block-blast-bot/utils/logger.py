"""
Block Blast Bot - Logger Setup
===============================
إعداد نظام السجل باستخدام loguru
يوفّر سجلاً ملوّناً في الطرفية + ملف دوّار
"""

import sys
from pathlib import Path
from loguru import logger

# استيراد الإعدادات (مع حماية من الاستيراد الدائري)
try:
    from config import LOG_CONFIG, LOGS_DIR
except ImportError:
    LOGS_DIR = Path(__file__).parent.parent / "logs"
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    LOG_CONFIG = {
        "level": "INFO",
        "console": True,
        "file": True,
        "file_name": "bot.log",
        "rotation": "10 MB",
        "retention": "7 days",
        "format": (
            "<green>{time:HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan> - "
            "<level>{message}</level>"
        ),
    }


# ============================================================
# متغير لتتبع حالة الإعداد (لتجنب التكرار)
# ============================================================
_IS_SETUP = False


# ============================================================
# الدالة الرئيسية
# ============================================================

def setup_logger(level: str = None):
    """
    إعداد نظام السجل

    Args:
        level: مستوى السجل (DEBUG/INFO/WARNING/ERROR)
               إن لم يُحدد، يُقرأ من config.py
    """
    global _IS_SETUP

    # تجنب الإعداد المتكرر
    if _IS_SETUP:
        return logger

    # إزالة المعالجات الافتراضية
    logger.remove()

    # مستوى السجل
    log_level = level or LOG_CONFIG.get("level", "INFO")

    # ============================================================
    # 1) معالج الطرفية (Console) - ملوّن ومرتّب
    # ============================================================
    if LOG_CONFIG.get("console", True):
        logger.add(
            sys.stderr,
            format=LOG_CONFIG["format"],
            level=log_level,
            colorize=True,
            backtrace=True,
            diagnose=False,
        )

    # ============================================================
    # 2) معالج الملف (File) - بدون ألوان
    # ============================================================
    if LOG_CONFIG.get("file", True):
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        log_file = LOGS_DIR / LOG_CONFIG.get("file_name", "bot.log")

        logger.add(
            str(log_file),
            format=(
                "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
                "{level: <8} | "
                "{name}:{function}:{line} - "
                "{message}"
            ),
            level=log_level,
            rotation=LOG_CONFIG.get("rotation", "10 MB"),
            retention=LOG_CONFIG.get("retention", "7 days"),
            compression="zip",
            encoding="utf-8",
            enqueue=True,
            backtrace=True,
            diagnose=False,
        )

    # ============================================================
    # 3) معالج الأخطاء فقط (ملف منفصل)
    # ============================================================
    if LOG_CONFIG.get("file", True):
        error_file = LOGS_DIR / "errors.log"

        logger.add(
            str(error_file),
            format=(
                "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
                "{level} | "
                "{name}:{function}:{line}\n"
                "{message}\n{exception}"
            ),
            level="ERROR",
            rotation="5 MB",
            retention="30 days",
            encoding="utf-8",
            backtrace=True,
            diagnose=True,
            enqueue=True,
        )

    _IS_SETUP = True
    logger.debug(f"✅ تم إعداد نظام السجل (المستوى: {log_level})")

    return logger


# ============================================================
# دالة مساعدة: تغيير المستوى أثناء التشغيل
# ============================================================

def set_level(level: str):
    """
    تغيير مستوى السجل ديناميكياً

    الاستخدام:
        from utils.logger import set_level
        set_level("DEBUG")
    """
    global _IS_SETUP
    _IS_SETUP = False
    setup_logger(level=level)


# ============================================================
# دالة مساعدة: طباعة عنوان قسم
# ============================================================

def log_section(title: str, char: str = "=", width: int = 60):
    """
    طباعة عنوان قسم مميز في السجل

    الاستخدام:
        log_section("بدء المعايرة")
    """
    line = char * width
    logger.info(line)
    logger.info(f"  {title}")
    logger.info(line)


# ============================================================
# دالة مساعدة: قياس الزمن
# ============================================================

class log_time:
    """
    Context manager لقياس زمن تنفيذ كتلة كود

    الاستخدام:
        with log_time("كشف اللوحة"):
            board = detector.detect(frame)
    """

    def __init__(self, label: str, level: str = "DEBUG"):
        self.label = label
        self.level = level
        self.start = None

    def __enter__(self):
        import time
        self.start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        import time
        elapsed = (time.perf_counter() - self.start) * 1000

        if exc_type is not None:
            logger.error(f"❌ {self.label} فشل بعد {elapsed:.1f}ms")
        else:
            getattr(logger, self.level.lower())(f"⏱️  {self.label}: {elapsed:.1f}ms")

        return False


# ============================================================
# اختبار سريع
# ============================================================

if __name__ == "__main__":
    # إعداد السجل
    setup_logger(level="DEBUG")

    # اختبارات
    log_section("اختبار نظام السجل")

    logger.debug("🔍 رسالة تشخيص")
    logger.info("ℹ️  رسالة معلومات")
    logger.success("✅ رسالة نجاح")
    logger.warning("⚠️  رسالة تحذير")
    logger.error("❌ رسالة خطأ")

    # اختبار قياس الزمن
    import time
    with log_time("عملية تجريبية"):
        time.sleep(0.15)

    # اختبار مع استثناء
    try:
        with log_time("عملية فاشلة"):
            raise ValueError("خطأ تجريبي")
    except ValueError:
        pass

    # اختبار تغيير المستوى
    set_level("INFO")
    logger.debug("هذه الرسالة لن تظهر (المستوى INFO)")

    log_section("تم الاختبار بنجاح", char="-")

    print(f"\n📁 ملفات السجل في: {LOGS_DIR}")
    print(f"   - bot.log")
    print(f"   - errors.log")