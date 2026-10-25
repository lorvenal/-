import os
from datetime import datetime


LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "activity.log")


# ─── ألوان (اختياري) ───
class Color:
    RESET = "\033[0m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    PURPLE = "\033[95m"
    CYAN = "\033[96m"


def _ensure_log_dir():
    """يتأكد من وجود مجلد السجلات"""
    os.makedirs(LOG_DIR, exist_ok=True)


def log(message, level="INFO"):
    """
    يسجل + يطبع في الشاشة
    level: INFO, OK, WARN, ERROR
    """
    _ensure_log_dir()

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] [{level}] {message}"

    # ─── لون حسب المستوى ───
    color = Color.RESET
    if level == "OK":
        color = Color.GREEN
    elif level == "WARN":
        color = Color.YELLOW
    elif level == "ERROR":
        color = Color.RED
    elif level == "INFO":
        color = Color.CYAN

    # ─── طبع ───
    print(f"{color}{line}{Color.RESET}")

    # ─── احفظ في الملف ───
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(line + "\n")
    except:
        pass


def log_success(message):
    """تسجيل نجاح"""
    log(message, "OK")


def log_error(message):
    """تسجيل خطأ"""
    log(message, "ERROR")


def log_warn(message):
    """تسجيل تحذير"""
    log(message, "WARN")


def clear_log():
    """يمسح ملف السجل"""
    _ensure_log_dir()
    try:
        with open(LOG_FILE, 'w', encoding='utf-8') as f:
            f.write("")
        return True
    except:
        return False