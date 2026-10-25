import discord
from discord.ext import commands
import asyncio


class Help(commands.Cog):
    """📖 أمر المساعدة"""

    def __init__(self, bot):
        self.bot = bot

    # ═════════════════════════════════════════
    # 📖 !cmds — كل الأوامر
    # ═════════════════════════════════════════
    @commands.command(name="cmds")
    async def cmds(self, ctx):
        """!cmds → عرض كل الأوامر"""
        try:
            await ctx.message.delete()
        except:
            pass

        text = """# 📖 **Cherry Selfbot — كل الأوامر**

## 🎮 **الحالة** (`status.py`)
- `!setstatus play <لعبة>` — Playing
- `!setstatus listen <شي>` — Listening to
- `!setstatus watch <شي>` — Watching
- `!setstatus compete <شي>` — Competing in
- `!setstatus stream <عنوان>` — Streaming
- `!setstatus clear` — مسح
- `!setstream <url> [عنوان]` — Streaming مع رابط
- `!mystatus` — حالتك الحالية
- `!statustest` — اختبار كل الحالات
- `!setonline` / `!setidle` / `!setdnd` / `!setinvisible`

## 🗑️ **حذف الرسائل** (`purge.py`) ⚡
- `!purge` — رسائلك في الروم الحالي (سريع)
- `!purge <id> [limit]` — روم محدد
- `!purgefast [limit]` — **سرعة قصوى** ⚡⚡⚡
- `!purgebulk [limit]` — bulk delete (14 يوم)
- `!purgeall [limit]` — من كل الرومات
- `!purgeeveryone <id> <limit> yes` — ⚠️ كل الرسائل
- `!dms` — قائمة DMs
- `!chinfo [id]` — معلومات روم

## 🚫 **الحظر** (`block.py`)
- `!blockall` — عرض معلومات سيرفر
- `!blockall <guild_id> yes` — حظر الكل
- `!blockuser <user_id>` — عضو واحد
- `!blockids <id1> <id2>` — قائمة IDs
- `!unblockuser <user_id>` — فك حظر
- `!unblockall yes` — فك الكل
- `!blocklist [limit]` — عرض المحظورين
- `!blockcheck <user_id>` — هل محظور؟
- `!blockstats` — إحصائيات

## 📁 **الرومات** (`rooms.py`)
- `!mass_rooms <عدد> [اسم]` — إنشاء رومات كثيرة
- `!nuke_channels yes` — ⚠️ حذف كل الرومات
- `!cleanup [prefix]` — حذف room-/chat-/temp-
- `!roomlist [prefix]` — عرض الرومات
- `!serverinfo` — معلومات السيرفر
- `!mkchannels <اسم1 | اسم2>` — إنشاء بأسماء
- `!clonech <عدد>` — نسخ الروم

## 💬 **mespam** (`spam.py`)
- `!mespam <وقت> <id> <رسالة>` — إرسال بحسابك
- `!mestop [id]` — إيقاف
- `!mestatus` — حالة الإرسالات
- `!mechange <id> <وقت>` — تغيير الوقت
- `!medel <id>/all yes` — حذف إعداد

## 🪝 **الويبوكات** (`webhooks.py`)
- `!hooks <عدد> [اسم]` — إنشاء ويبوكات
- `!rooms <عدد> [اسم] [رسالة]` — رومات + ربط + إرسال
- `!fire <وقت> <رسالة>` — إرسال متكرر
- `!stop` — إيقاف
- `!send <رسالة>` — إرسال مرة
- `!whlist [limit]` — عرض
- `!whstatus` — حالة
- `!whtest [رسالة]` — اختبار
- `!whdel <id>/all yes` — حذف
- `!whclear yes` — مسح القائمة

## 📝 **المراقبة** (`logger.py`)
- `!deleted [limit]` — الرسائل المحذوفة في DM
- `!requests [limit]` — طلبات الصداقة
- `!finddel <user_id>` — رسائل شخص محذوفة
- `!logstats` — إحصائيات
- `!cache [limit]` — الكاش
- `!clearlogs <deleted|requests|all> yes` — مسح

## 🤖 **الردود التلقائية** (`autoreply.py`)
- `!welcome set #ch <رسالة>` — ترحيب
- `!welcome off/status`
- `!trigger add <كلمة> | <رد1> | <رد2>`
- `!trigger react <كلمة> <emoji>`
- `!trigger del/list/clear`
- `!stalk add <user_id> | <رد>`
- `!stalk react/on/off/del/list`

## 🧠 **AI + تلخيص** (`ai.py`) 🆕
- `!ai <سؤال>` — سؤال مباشر
- `@حسابك ai <سؤال>` — منشن
- (رد على البوت) `ai <سؤال>`
- `!sum [عدد] [id]` — 📝 تلخيص آخر رسائل
- `!sumfirst [عدد] [id]` — 📌 تلخيص أول رسائل
- `!user <id> [عدد]` — 👤 تحليل شخص
- `!sumlist [عدد]` — 📋 التلخيصات المحفوظة
- `!sumclear yes` — 🗑️ مسح التلخيصات
- `!aiset status/on/off/word/limit/clear`
- `!aitest` — اختبار

## ⏱️ **صيغ الوقت**
`s` = ثانية | `m` = دقيقة | `h` = ساعة
`ث` | `د` | `س`

---

💡 **للتفاصيل:** `!help <قسم>`
"""

        if len(text) > 1900:
            parts = [text[i:i+1900] for i in range(0, len(text), 1900)]
            for part in parts:
                await ctx.send(part)
                await asyncio.sleep(0.3)
        else:
            await ctx.send(text)

    # ═════════════════════════════════════════
    # 📖 !help — مساعدة مفصلة
    # ═════════════════════════════════════════
    @commands.command(name="help")
    async def help_cmd(self, ctx, *, cmd: str = ""):
        """
        !help → قائمة الأقسام
        !help <قسم> → تفاصيل قسم
        """
        try:
            await ctx.message.delete()
        except:
            pass

        sections = {
            "status": """
🎮 **status.py — حالة الحساب**
- `!setstatus play <لعبة>` — Playing
- `!setstatus listen <شي>` — Listening
- `!setstatus watch <شي>` — Watching
- `!setstatus compete <شي>` — Competing
- `!setstatus stream <عنوان>` — Streaming
- `!setstatus clear` — مسح
- `!setstream <url> [عنوان]` — Streaming مع رابط
- `!mystatus` / `!statustest`
- `!setonline` / `!setidle` / `!setdnd` / `!setinvisible`
""",
            "purge": """
🗑️ **purge.py — حذف الرسائل (سريع)**
- `!purge` — رسائلك في الروم
- `!purge <id> [limit]` — روم محدد
- `!purge <id> 0` — كل رسائلك
- `!purgefast [limit]` — ⚡ سرعة قصوى
- `!purgebulk [limit]` — 📦 bulk delete (14 يوم)
- `!purgeall [limit]` — كل الرومات
- `!purgeeveryone <id> <N> yes` — ⚠️ كل الرسائل
- `!dms` — قائمة DMs
- `!chinfo [id]` — معلومات روم

**الفرق:**
- `!purge` → عادي
- `!purgefast` → سريع (توازي)
- `!purgebulk` → أسرع (API)
""",
            "block": """
🚫 **block.py — الحظر**
- `!blockall` → عرض معلومات
- `!blockall <guild_id> yes` → حظر الكل
- `!blockuser <id>` → واحد
- `!blockids <id1> <id2>` → قائمة
- `!unblockall yes` → فك الكل
- `!blocklist` → عرض
- `!blockcheck <id>` → هل محظور؟
- `!blockstats` → إحصائيات
""",
            "rooms": """
📁 **rooms.py — الرومات**
- `!mass_rooms <عدد> [اسم]` — إنشاء كثير
- `!nuke_channels yes` — ⚠️ حذف الكل
- `!cleanup [prefix]` — حذف رومات
- `!roomlist [prefix]` — عرض
- `!serverinfo` — معلومات السيرفر
- `!mkchannels <اسم1 | اسم2>`
- `!clonech <عدد>`
""",
            "spam": """
💬 **spam.py — mespam**
- `!mespam <وقت> <channel_id> <رسالة>`
- `!mestop [channel_id]`
- `!mestatus`
- `!mechange <id> <وقت>`
- `!medel <id>/all yes`

**الأنسب:** `30s` أو أكثر
""",
            "webhooks": """
🪝 **webhooks.py — الويبوكات**
- `!hooks <عدد> [اسم]` — إنشاء ويبوكات
- `!rooms <عدد> [اسم] [رسالة]` — رومات + ربط
- `!fire <وقت> <رسالة>` 🔥 — إرسال متكرر
- `!stop` — إيقاف
- `!send <رسالة>` — إرسال مرة
- `!whlist` / `!whstatus` / `!whtest`
- `!whdel <id>/all yes`
- `!whclear yes`

**خطوات:**
1. `!hooks 10`
2. `!rooms 10 room`
3. `!fire 30s مرحبا`
""",
            "logger": """
📝 **logger.py — مراقبة DM**
- `!deleted [limit]` — الرسائل المحذوفة
- `!requests [limit]` — طلبات الصداقة
- `!finddel <user_id>` — رسائل شخص
- `!logstats` — إحصائيات
- `!cache [limit]` — الكاش
- `!clearlogs <deleted|requests|all> yes`
""",
            "autoreply": """
🤖 **autoreply.py — ردود تلقائية**
- `!welcome set #ch <رسالة>` — ترحيب
- `!welcome off/status`
- `!trigger add <كلمة> | <رد1> | <رد2>`
- `!trigger react <كلمة> <emoji>`
- `!trigger del/list/clear`
- `!stalk add <user_id> | <رد>`
- `!stalk on/off/del/list/react`

**المتغيرات في welcome:**
`{user}` `{guild}` `{name}`
""",
            "ai": """
🧠 **ai.py — الذكاء الاصطناعي + تلخيص** 🆕

**المحادثة:**
- `@حسابك ai <سؤال>` — منشن
- (رد على البوت) `ai <سؤال>`
- `!ai <سؤال>` — مباشر
- `!aitest` — اختبار

**التلخيص:** 📝
- `!sum` — آخر 1000 رسالة في الروم
- `!sum 500` — آخر 500
- `!sum 500 <channel_id>` — من روم ثاني
- `!sumfirst [عدد] [id]` — أول رسائل

**تحليل شخص:** 👤
- `!user <user_id>` — آخر 1000 رسالة له
- `!user <user_id> 500` — آخر 500
- `!user <user_id> 500 <channel_id>` — من روم ثاني

**الإدارة:**
- `!sumlist [عدد]` — التلخيصات المحفوظة
- `!sumclear yes` — مسح كل التلخيصات
- `!aiset status` — الحالة
- `!aiset on/off` — تشغيل/إيقاف
- `!aiset word <كلمة>` — كلمة التشغيل
- `!aiset limit <رقم>` — الحد الافتراضي
- `!aiset clear` — مسح السجل

**الحد الأقصى:** 5000 رسالة
""",
        }

        if cmd:
            cmd_lower = cmd.lower().strip()
            if cmd_lower in sections:
                text = sections[cmd_lower]
                return await ctx.send(text)
            else:
                return await ctx.send(
                    f"❌ قسم غير معروف: `{cmd}`\n"
                    f"**الأقسام:**\n"
                    f"`status`, `purge`, `block`, `rooms`, `spam`,\n"
                    f"`webhooks`, `logger`, `autoreply`, `ai`"
                )

        text = """
**📖 Cherry Selfbot — الأقسام**

اكتب `!help <قسم>` للتفاصيل:

🎮 `status` — حالة الحساب
🗑️ `purge` — حذف الرسائل ⚡
🚫 `block` — الحظر
📁 `rooms` — الرومات
💬 `spam` — mespam
🪝 `webhooks` — الويبوكات
📝 `logger` — مراقبة DM
🤖 `autoreply` — ردود تلقائية
🧠 `ai` — AI + تلخيص 🆕

💡 **لكل الأوامر:** `!cmds`
"""
        await ctx.send(text)


async def setup(bot):
    await bot.add_cog(Help(bot))