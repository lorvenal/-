# ═════════════════════════════════════════
# 📄 main.py — Multi-Account Tool
# ═════════════════════════════════════════

import json
import os
import sys
import asyncio
import random
import time
from datetime import datetime

# ─── نتأكد إن المكتبات موجودة ───
try:
    import aiohttp
except ImportError:
    print("❌ مكتبة aiohttp مو مثبتة")
    print("   ثبّتها: pip install aiohttp")
    sys.exit(1)


# ═════════════════════════════════════════
# ⚙️ الإعدادات
# ═════════════════════════════════════════
ACCOUNTS_FILE = "accounts.json"
TASKS_FILE = "tasks.json"
LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "activity.log")

# ─── حدود الأمان ───
MIN_DELAY = 60          # أقل تأخير بين الحسابات (ثانية) = دقيقة
MAX_DELAY = 300         # أكثر تأخير (ثانية) = 5 دقايق
MAX_ACCOUNTS = 5        # حد أقصى للحسابات
TIMEOUT = 30            # timeout للطلبات

API = "https://discord.com/api/v10"


# ═════════════════════════════════════════
# 📂 دوال الملفات
# ═════════════════════════════════════════
def load_accounts():
    """يقرأ accounts.json"""
    if not os.path.exists(ACCOUNTS_FILE):
        print(f"❌ ما لقيت {ACCOUNTS_FILE}")
        return []

    try:
        with open(ACCOUNTS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get("accounts", [])
    except json.JSONDecodeError as e:
        print(f"❌ {ACCOUNTS_FILE} تالف: {e}")
        return []


def load_tasks():
    """يقرأ tasks.json"""
    if not os.path.exists(TASKS_FILE):
        print(f"❌ ما لقيت {TASKS_FILE}")
        return []

    try:
        with open(TASKS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get("tasks", [])
    except json.JSONDecodeError as e:
        print(f"❌ {TASKS_FILE} تالف: {e}")
        return []


def save_accounts(accounts):
    """يحفظ accounts.json"""
    try:
        with open(ACCOUNTS_FILE, 'w', encoding='utf-8') as f:
            json.dump({"accounts": accounts}, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"❌ فشل حفظ: {e}")


# ═════════════════════════════════════════
# 📝 التسجيل
# ═════════════════════════════════════════
def log(message, level="INFO"):
    """يسجل + يطبع"""
    os.makedirs(LOG_DIR, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] [{level}] {message}"

    # طبع في الشاشة
    print(line)

    # احفظ في الملف
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(line + "\n")
    except:
        pass


# ═════════════════════════════════════════
# 🎲 التأخير العشوائي
# ═════════════════════════════════════════
def get_random_delay():
    """
    يرجع تأخير عشوائي بالثواني
    - min: 60s (دقيقة)
    - max: 300s (5 دقايق)
    - peak: 150s (2.5 دقيقة - الأكثر احتمالاً)
    """
    return random.triangular(MIN_DELAY, MAX_DELAY, (MIN_DELAY + MAX_DELAY) / 2)


async def wait_random():
    """ينتظر تأخير عشوائي"""
    seconds = get_random_delay()
    minutes = seconds / 60
    log(f"⏳ ينتظر {minutes:.1f} دقيقة قبل الحساب التالي...")
    await asyncio.sleep(seconds)


# ═════════════════════════════════════════
# 🌐 Discord API
# ═════════════════════════════════════════
async def get_user_info(session, token):
    """
    يتحقق من التوكن ويرجع معلومات الحساب
    """
    try:
        async with session.get(
            f"{API}/users/@me",
            headers={"Authorization": token},
            timeout=aiohttp.ClientTimeout(total=TIMEOUT)
        ) as resp:

            if resp.status == 200:
                return await resp.json()
            elif resp.status == 401:
                return {"error": "توكن غلط"}
            elif resp.status == 403:
                return {"error": "الحساب محظور"}
            else:
                return {"error": f"HTTP {resp.status}"}

    except asyncio.TimeoutError:
        return {"error": "Timeout"}
    except Exception as e:
        return {"error": str(e)}


async def join_invite(session, token, invite):
    """
    دخول سيرفر عبر invite
    invite: كود أو رابط كامل
    """
    # استخرج الكود
    code = invite.split("/")[-1].strip()

    try:
        async with session.post(
            f"{API}/invites/{code}",
            headers={"Authorization": token},
            timeout=aiohttp.ClientTimeout(total=TIMEOUT)
        ) as resp:

            if resp.status == 200:
                data = await resp.json()
                guild = data.get("guild", {})
                return {"ok": True, "guild": guild.get("name", "?")}
            elif resp.status == 401:
                return {"ok": False, "error": "توكن غلط"}
            elif resp.status == 403:
                return {"ok": False, "error": "محظور من السيرفر"}
            elif resp.status == 404:
                return {"ok": False, "error": "Invite غلط أو منتهي"}
            elif resp.status == 429:
                retry = resp.headers.get("retry-after", "5")
                return {"ok": False, "error": f"Rate limit ({retry}s)"}
            else:
                err = await resp.text()
                return {"ok": False, "error": f"HTTP {resp.status}: {err[:100]}"}

    except asyncio.TimeoutError:
        return {"ok": False, "error": "Timeout"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


async def add_reaction(session, token, message_url, emoji):
    """
    رد فعل على رسالة
    message_url: https://discord.com/channels/GUILD/CHANNEL/MESSAGE
    """
    try:
        # استخرج IDs
        parts = message_url.strip().split("/")
        if len(parts) < 7:
            return {"ok": False, "error": "رابط غلط"}

        channel_id = parts[-2]
        message_id = parts[-1]

        # Encode emoji
        import urllib.parse
        emoji_encoded = urllib.parse.quote(emoji)

        # API call
        url = f"{API}/channels/{channel_id}/messages/{message_id}/reactions/{emoji_encoded}/@me"

        async with session.put(
            url,
            headers={"Authorization": token},
            timeout=aiohttp.ClientTimeout(total=TIMEOUT)
        ) as resp:

            if resp.status in (200, 204):
                return {"ok": True}
            elif resp.status == 401:
                return {"ok": False, "error": "توكن غلط"}
            elif resp.status == 403:
                return {"ok": False, "error": "محظور/ما عنده صلاحية"}
            elif resp.status == 404:
                return {"ok": False, "error": "الرسالة مو موجودة"}
            elif resp.status == 429:
                retry = resp.headers.get("retry-after", "5")
                return {"ok": False, "error": f"Rate limit ({retry}s)"}
            else:
                err = await resp.text()
                return {"ok": False, "error": f"HTTP {resp.status}: {err[:100]}"}

    except asyncio.TimeoutError:
        return {"ok": False, "error": "Timeout"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ═════════════════════════════════════════
# 🎯 تنفيذ مهمة على حساب
# ═════════════════════════════════════════
async def execute_task_on_account(session, account, task):
    """
    ينفذ مهمة على حساب واحد
    يرجع: (نجاح؟, رسالة)
    """
    name = account.get("name", "?")
    token = account.get("token", "")

    if not token:
        return False, "ما فيه توكن"

    task_type = task.get("type", "").lower()

    # ═══ دخول سيرفر ═══
    if task_type == "join":
        invite = task.get("invite", "")
        if not invite:
            return False, "ما فيه invite"

        result = await join_invite(session, token, invite)

        if result.get("ok"):
            return True, f"دخل: {result.get('guild', '?')}"
        else:
            return False, result.get("error", "?")

    # ═══ رد فعل ═══
    elif task_type == "react":
        message_url = task.get("message_url", "")
        emoji = task.get("emoji", "👍")

        if not message_url:
            return False, "ما فيه message_url"

        result = await add_reaction(session, token, message_url, emoji)

        if result.get("ok"):
            return True, f"رد فعل: {emoji}"
        else:
            return False, result.get("error", "?")

    # ═══ نوع غير معروف ═══
    else:
        return False, f"نوع مهمة غير معروف: {task_type}"


# ═════════════════════════════════════════
# 🚀 الدالة الرئيسية
# ═════════════════════════════════════════
async def main():
    # ─── Header ───
    print()
    print("═" * 60)
    print("  🤖 Multi-Account Tool")
    print("═" * 60)
    print()

    # ─── تحميل البيانات ───
    accounts = load_accounts()
    tasks = load_tasks()

    if not accounts:
        print("❌ ما فيه حسابات. عبّي accounts.json")
        return

    if not tasks:
        print("❌ ما فيه مهام. عبّي tasks.json")
        return

    # ─── حد أقصى ───
    if len(accounts) > MAX_ACCOUNTS:
        print(f"⚠️ عندك {len(accounts)} حساب. الحد الأقصى {MAX_ACCOUNTS}")
        print(f"   سيتم استخدام أول {MAX_ACCOUNTS} فقط")
        accounts = accounts[:MAX_ACCOUNTS]

    # ─── فلترة الحسابات المفعلة ───
    accounts = [a for a in accounts if a.get("enabled", True)]

    if not accounts:
        print("❌ كل الحسابات معطلة")
        return

    # ─── عرض الملخص ───
    print("📊 الملخص:")
    print(f"   👥 الحسابات: {len(accounts)}")
    for i, acc in enumerate(accounts, 1):
        print(f"      {i}. {acc.get('name', '?')}")
    print()

    print(f"   📋 المهام: {len(tasks)}")
    for i, t in enumerate(tasks, 1):
        print(f"      {i}. {t.get('type', '?')}")
    print()

    print(f"   ⏱️ التأخير: {MIN_DELAY//60}-{MAX_DELAY//60} دقيقة بين الحسابات")
    print()

    # ─── تأكيد ───
    print("─" * 60)
    confirm = input("⚠️ اكتب 'yes' للبدء: ").strip().lower()
    if confirm != "yes":
        print("❌ تم الإلغاء")
        return

    print()
    print("═" * 60)
    print("  🚀 بدأ التنفيذ")
    print("═" * 60)
    print()

    # ─── إحصائيات ───
    start_time = time.time()
    total_success = 0
    total_failed = 0

    # ─── عميل HTTP ───
    timeout = aiohttp.ClientTimeout(total=TIMEOUT)
    async with aiohttp.ClientSession(timeout=timeout) as session:

        # ─── لكل مهمة ───
        for task_idx, task in enumerate(tasks, 1):
            task_type = task.get("type", "?")

            print()
            print(f"┌─ المهمة #{task_idx}: {task_type} ─────────────")
            print()

            # ─── الحسابات المعنية ───
            target_names = task.get("accounts", [])

            if target_names:
                target_accounts = [
                    a for a in accounts
                    if a.get("name") in target_names
                ]
            else:
                target_accounts = accounts

            if not target_accounts:
                log(f"⚠️ ما فيه حسابات لهذي المهمة", "WARN")
                continue

            log(f"🎯 المهمة: {task_type} — {len(target_accounts)} حساب")
            print()

            # ─── لكل حساب (بالتوالي) ───
            for acc_idx, account in enumerate(target_accounts, 1):
                name = account.get("name", "?")
                token = account.get("token", "")

                print(f"┌─ [{acc_idx}/{len(target_accounts)}] {name}")

                # 1. تحقق من التوكن
                user = await get_user_info(session, token)

                if "error" in user:
                    log(f"❌ {name}: {user['error']}", "ERROR")
                    total_failed += 1
                    print(f"└─ ❌ {user['error']}")
                    print()

                    # تأخير حتى لو فشل
                    if acc_idx < len(target_accounts):
                        await wait_random()
                    continue

                # 2. عرض معلومات الحساب
                username = user.get("username", "?")
                user_id = user.get("id", "?")
                log(f"👤 {name}: @{username} ({user_id})")

                # 3. نفذ المهمة
                try:
                    success, message = await execute_task_on_account(
                        session, account, task
                    )

                    if success:
                        log(f"✅ {name}: {message}", "OK")
                        total_success += 1
                        print(f"└─ ✅ {message}")
                    else:
                        log(f"❌ {name}: {message}", "ERROR")
                        total_failed += 1
                        print(f"└─ ❌ {message}")

                except Exception as e:
                    log(f"❌ {name}: {type(e).__name__}: {e}", "ERROR")
                    total_failed += 1
                    print(f"└─ ❌ خطأ: {e}")

                print()

                # 4. تأخير عشوائي (إلا الأخير)
                if acc_idx < len(target_accounts):
                    await wait_random()

            print(f"└─ انتهت المهمة #{task_idx}")
            print()

            # ─── تأخير بين المهام ───
            if task_idx < len(tasks):
                log(f"⏳ تأخير بين المهام...")
                await wait_random()

    # ═════════════════════════════════════════
    # 📊 التقرير النهائي
    # ═════════════════════════════════════════
    elapsed = time.time() - start_time
    hours = int(elapsed // 3600)
    minutes = int((elapsed % 3600) // 60)
    seconds = int(elapsed % 60)

    print()
    print("═" * 60)
    print("  ✅ انتهى")
    print("═" * 60)
    print()
    print(f"📊 الإحصائيات:")
    print(f"   ✅ نجح:  {total_success}")
    print(f"   ❌ فشل:  {total_failed}")
    print(f"   📊 المجموع: {total_success + total_failed}")
    print()

    if total_success + total_failed > 0:
        rate = (total_success / (total_success + total_failed)) * 100
        print(f"   📈 معدل النجاح: {rate:.1f}%")
        print()

    print(f"⏱️ الوقت الكلي: {hours}h {minutes}m {seconds}s")
    print()
    print(f"📝 السجل: {LOG_FILE}")
    print()
    print("═" * 60)


# ═════════════════════════════════════════
# ▶️ التشغيل
# ═════════════════════════════════════════
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print()
        print("🛑 تم الإيقاف")
    except Exception as e:
        print()
        print(f"❌ خطأ: {type(e).__name__}: {e}")
        print()
        input("اضغط Enter للخروج...")