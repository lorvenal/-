# ═════════════════════════════════════════
# ⚙️ config.py — إعدادات Multi-Account Tool
# ═════════════════════════════════════════

# ─── الملفات ───
ACCOUNTS_FILE = "accounts.json"
TASKS_FILE = "tasks.json"
LOG_DIR = "logs"
LOG_FILE = "logs/activity.log"

# ─── حدود الأمان ───
MAX_ACCOUNTS = 5        # حد أقصى للحسابات (لا تزيد!)
MIN_DELAY = 60          # أقل تأخير بين الحسابات (ثانية) = دقيقة
MAX_DELAY = 300         # أكثر تأخير (ثانية) = 5 دقايق
TIMEOUT = 30            # timeout للطلبات (ثانية)

# ─── Discord API ───
API_VERSION = "v10"
API_BASE = f"https://discord.com/api/{API_VERSION}"

# ─── User-Agent ───
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "discord/1.0.9175 Chrome/128.0.6613.186 "
    "Electron/32.2.7 Safari/537.36"
)

# ─── خيارات ───
SHOW_TOKENS = False     # عرض التوكنات في السجل؟
VERBOSE = True          # طباعة تفاصيل أكثر؟
RETRY_ON_FAIL = False   # إعادة المحاولة لو فشل؟
MAX_RETRIES = 3         # عدد محاولات الإعادة