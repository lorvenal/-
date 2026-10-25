"""
Block Blast Bot - Configuration
================================
ملف الإعدادات المركزي لكل المشروع
يحتوي على: إعدادات ADB، إحداثيات اللوحة، الألوان، معايير AI
"""

import os
from pathlib import Path


# ============================================================
# المسارات الأساسية
# ============================================================
BASE_DIR = Path(__file__).parent
LOGS_DIR = BASE_DIR / "logs"
DEBUG_DIR = BASE_DIR / "debug"
TEMPLATES_DIR = BASE_DIR / "vision" / "templates"

# إنشاء المجلدات إن لم تكن موجودة
for d in [LOGS_DIR, DEBUG_DIR, TEMPLATES_DIR]:
    d.mkdir(parents=True, exist_ok=True)


# ============================================================
# إعدادات ADB والاتصال بالهاتف
# ============================================================
ADB_CONFIG = {
    # مسار adb (اتركه فارغاً إذا كان في PATH)
    "adb_path": os.getenv("ADB_PATH", "adb"),

    # مهلة الأوامر بالثواني
    "command_timeout": 10,

    # مدة اللمس الافتراضية (ms)
    "tap_duration": 50,

    # مدة السحب الافتراضية (ms) - مهمة للعبة Block Blast
    "swipe_duration": 350,

    # عدد مرات إعادة المحاولة عند فشل أمر
    "retry_attempts": 3,
    "retry_delay": 0.5,
}


# ============================================================
# إعدادات التقاط الشاشة
# ============================================================
CAPTURE_CONFIG = {
    # طريقة الالتقاط: "adb" (أبطأ، أدق) أو "scrcpy" (أسرع)
    "method": "adb",

    # صيغة الصورة
    "format": "png",

    # حفظ لقطات الشاشة للتشخيص؟
    "save_debug_frames": False,
    "debug_frames_limit": 100,
}


# ============================================================
# إعدادات دقة الشاشة (تُملأ تلقائياً عند الاتصال)
# ============================================================
SCREEN_CONFIG = {
    "width": 1080,          # عرض الشاشة بالبكسل
    "height": 2400,         # ارتفاع الشاشة بالبكسل
    "orientation": "portrait",
}


# ============================================================
# إعدادات اللوحة (Board) - 8x8
# ⚠️ هذه القيم تحتاج معايرة يدوية مرة واحدة
# ============================================================
BOARD_CONFIG = {
    # أبعاد الشبكة
    "rows": 8,
    "cols": 8,

    # إحداثيات الزاوية العلوية اليسرى للوحة (بكسل)
    "x_start": 100,
    "y_start": 1100,

    # حجم كل خلية (بكسل)
    "cell_size": 100,

    # الفاصل بين الخلايا (عادة 0 أو صغير)
    "cell_padding": 0,

    # حجم القطعة داخل الخلية (نسبة من cell_size)
    "piece_scale": 0.85,
}


# ============================================================
# إعدادات القطع الثلاث (Tray) - الأسفل
# ============================================================
TRAY_CONFIG = {
    # عدد القطع المتاحة في كل دور
    "slots": 3,

    # إحداثيات مركز كل قطعة في منطقة السحب (بكسل)
    # ⚠️ تحتاج معايرة
    "slot_positions": [
        (250, 1900),   # القطعة الأولى (يسار)
        (540, 1900),   # القطعة الثانية (وسط)
        (830, 1900),   # القطعة الثالثة (يمين)
    ],

    # حجم خلية القطعة الصغيرة (للعرض في الأسفل)
    "mini_cell_size": 60,
}


# ============================================================
# إعدادات الألوان (HSV للتعرف على القطع)
# ============================================================
COLOR_CONFIG = {
    # نطاقات HSV للألوان (يمكن توسيعها لاحقاً)
    # H: 0-179, S: 0-255, V: 0-255
    "colors": {
        "red":    {"h_min": 0,   "h_max": 10,  "s_min": 100, "v_min": 100},
        "orange": {"h_min": 11,  "h_max": 22,  "s_min": 100, "v_min": 100},
        "yellow": {"h_min": 23,  "h_max": 35,  "s_min": 100, "v_min": 100},
        "green":  {"h_min": 36,  "h_max": 85,  "s_min": 80,  "v_min": 80},
        "cyan":   {"h_min": 86,  "h_max": 100, "s_min": 80,  "v_min": 80},
        "blue":   {"h_min": 101, "h_max": 130, "s_min": 80,  "v_min": 80},
        "purple": {"h_min": 131, "h_max": 160, "s_min": 80,  "v_min": 80},
        "pink":   {"h_min": 161, "h_max": 179, "s_min": 80,  "v_min": 80},
    },

    # خلفية اللوحة (لتمييز الخلايا الفارغة)
    # غالباً داكنة/سوداء مع حد رمادي
    "empty_cell_brightness_threshold": 60,

    # حد التفاوت للتعرف على اللون
    "hue_tolerance": 10,
}


# ============================================================
# إعدادات الذكاء الاصطناعي (AI Solver)
# ============================================================
AI_CONFIG = {
    # أوزان معايير التقييم (كلما زاد الرقم زادت أهميته)
    "weights": {
        # مكافأة مسح صف/عمود (نقاط اللعبة)
        "line_clear": 100.0,

        # مكافأة مسح عدة صفوف بنفس الحركة (combo)
        "combo_multiplier": 1.8,

        # عقوبة الفجوات (الفراغات المحاصرة)
        "hole_penalty": -8.0,

        # مكافأة الحفاظ على مساحة كبيرة فارغة
        "open_space_bonus": 2.5,

        # مكافأة تجاور القطع (تجعل اللوحة مرنة)
        "adjacency_bonus": 1.2,

        # عقوبة الجيوب الضيقة (خلايا يصعب الوصول لها)
        "pocket_penalty": -15.0,

        # مكافأة الحفاظ على الحواف نظيفة
        "edge_bonus": 1.5,
    },

    # عمق البحث (1 = جشع، 2 = نظر لخطوة قادمة)
    "search_depth": 2,

    # تفعيل البحث الشجري للحركات المتعددة
    "enable_lookahead": True,

    # عدد أفضل الحركات للاحتفاظ بها في البحث
    "beam_width": 5,
}


# ============================================================
# إعدادات حلقة اللعب (Loop)
# ============================================================
LOOP_CONFIG = {
    # التأخير بين الحركات (ثواني)
    # لا تجعله أقل من 0.4 لتجنب أخطاء في اللعبة
    "loop_delay": 0.7,

    # التأخير بعد التقاط الشاشة قبل التحليل
    "post_capture_delay": 0.15,

    # التأخير بعد تنفيذ اللمس قبل الالتقاط التالي
    "post_move_delay": 0.5,

    # أقصى عدد حركات (None = بلا حد)
    "max_moves": None,

    # إيقاف عند اكتشاف Game Over
    "stop_on_game_over": True,

    # حفظ صورة عند Game Over
    "save_gameover_screenshot": True,
}


# ============================================================
# إعدادات السجل (Logging)
# ============================================================
LOG_CONFIG = {
    "level": "INFO",            # DEBUG, INFO, WARNING, ERROR
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
# إعدادات التشخيص (Debug)
# ============================================================
DEBUG_CONFIG = {
    # رسم شبكة اللوحة على الصورة
    "draw_board_grid": True,

    # رسم القطع المكتشفة
    "draw_blocks": True,

    # رسم أفضل حركة مقترحة
    "draw_best_move": True,

    # إظهار أرقام الإحداثيات
    "show_coordinates": False,

    # حجم نافذة العرض
    "window_width": 540,
    "window_height": 960,
}


# ============================================================
# قاموس CONFIG الرئيسي (يجمع كل شيء)
# ============================================================
CONFIG = {
    # حالة المعايرة
    "calibrated": False,

    # إعدادات فرعية
    "adb": ADB_CONFIG,
    "capture": CAPTURE_CONFIG,
    "screen": SCREEN_CONFIG,
    "board": BOARD_CONFIG,
    "tray": TRAY_CONFIG,
    "colors": COLOR_CONFIG,
    "ai": AI_CONFIG,
    "loop": LOOP_CONFIG,
    "log": LOG_CONFIG,
    "debug": DEBUG_CONFIG,

    # مسارات
    "paths": {
        "base": BASE_DIR,
        "logs": LOGS_DIR,
        "debug": DEBUG_DIR,
        "templates": TEMPLATES_DIR,
    },

    # اختصارات مباشرة (للوصول السريع)
    "loop_delay": LOOP_CONFIG["loop_delay"],
    "cell_size": BOARD_CONFIG["cell_size"],
    "board_rows": BOARD_CONFIG["rows"],
    "board_cols": BOARD_CONFIG["cols"],
}


# ============================================================
# دوال مساعدة
# ============================================================

def get_board_cell_center(row: int, col: int) -> tuple:
    """
    إرجاع إحداثيات (x, y) لمركز خلية معينة في اللوحة

    Args:
        row: رقم الصف (0-7)
        col: رقم العمود (0-7)

    Returns:
        (x, y) بالبكسل
    """
    cfg = BOARD_CONFIG
    x = cfg["x_start"] + col * cfg["cell_size"] + cfg["cell_size"] // 2
    y = cfg["y_start"] + row * cfg["cell_size"] + cfg["cell_size"] // 2
    return x, y


def get_slot_center(slot_index: int) -> tuple:
    """
    إرجاع إحداثيات مركز قطعة معينة في منطقة السحب

    Args:
        slot_index: 0, 1, أو 2

    Returns:
        (x, y) بالبكسل
    """
    return TRAY_CONFIG["slot_positions"][slot_index]


def update_calibration(**kwargs):
    """
    تحديث إعدادات المعايرة وحفظها في الملف

    الاستخدام:
        update_calibration(
            board_x_start=110,
            board_y_start=1150,
            cell_size=98,
        )
    """
    mapping = {
        "board_x_start": ("board", "x_start"),
        "board_y_start": ("board", "y_start"),
        "cell_size": ("board", "cell_size"),
        "screen_width": ("screen", "width"),
        "screen_height": ("screen", "height"),
    }

    for key, value in kwargs.items():
        if key in mapping:
            section, field = mapping[key]
            CONFIG[section][field] = value
            # تحديث الاختصار المباشر
            if section == "board" and field == "cell_size":
                CONFIG["cell_size"] = value

    CONFIG["calibrated"] = True
    save_config()


def save_config():
    """حفظ الإعدادات الحالية في ملف config_saved.py"""
    try:
        import json
        save_path = BASE_DIR / "config_saved.json"

        # ننسخ الإعدادات بدون المسارات (Path objects)
        data = {
            "calibrated": CONFIG["calibrated"],
            "board": BOARD_CONFIG,
            "screen": SCREEN_CONFIG,
            "tray": TRAY_CONFIG,
        }

        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return True
    except Exception as e:
        print(f"خطأ في حفظ الإعدادات: {e}")
        return False


def load_config():
    """تحميل الإعدادات المحفوظة إن وجدت"""
    try:
        import json
        save_path = BASE_DIR / "config_saved.json"
        if not save_path.exists():
            return False

        with open(save_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if "board" in data:
            BOARD_CONFIG.update(data["board"])
            CONFIG["board"].update(data["board"])
        if "screen" in data:
            SCREEN_CONFIG.update(data["screen"])
        if "tray" in data:
            TRAY_CONFIG.update(data["tray"])

        CONFIG["calibrated"] = data.get("calibrated", False)
        CONFIG["cell_size"] = BOARD_CONFIG["cell_size"]

        return True
    except Exception as e:
        print(f"خطأ في تحميل الإعدادات: {e}")
        return False


# تحميل تلقائي عند الاستيراد
load_config()


# ============================================================
# اختبار سريع عند تشغيل الملف مباشرة
# ============================================================
if __name__ == "__main__":
    print("=" * 60)
    print("📋 Block Blast Bot - الإعدادات الحالية")
    print("=" * 60)

    print(f"\n📱 الشاشة: {SCREEN_CONFIG['width']}x{SCREEN_CONFIG['height']}")
    print(f"🎯 اللوحة: {BOARD_CONFIG['rows']}x{BOARD_CONFIG['cols']} خلية")
    print(f"📐 حجم الخلية: {BOARD_CONFIG['cell_size']}px")
    print(f"📍 بداية اللوحة: ({BOARD_CONFIG['x_start']}, {BOARD_CONFIG['y_start']})")
    print(f"⏱️  تأخير الحلقة: {LOOP_CONFIG['loop_delay']}s")
    print(f"🔧 المعايرة: {'✅ تمت' if CONFIG['calibrated'] else '❌ لم تتم بعد'}")

    print("\n🎨 الألوان المدعومة:")
    for color in COLOR_CONFIG["colors"].keys():
        print(f"   • {color}")

    print("\n📦 القطع في منطقة السحب:")
    for i, pos in enumerate(TRAY_CONFIG["slot_positions"], 1):
        print(f"   • قطعة {i}: {pos}")

    print("\n" + "=" * 60)

    # اختبار دالة إحداثيات الخلية
    print("\n🧪 اختبار get_board_cell_center:")
    for r, c in [(0, 0), (3, 4), (7, 7)]:
        x, y = get_board_cell_center(r, c)
        print(f"   خلية ({r},{c}) → مركز ({x}, {y})")

    print("\n✅ config.py يعمل بشكل صحيح")