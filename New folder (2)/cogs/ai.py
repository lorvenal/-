import discord
from discord.ext import commands
import json
import os
import aiohttp
import asyncio
from collections import Counter


# ═════════════════════════════════════════
# ⚙️ الإعدادات
# ═════════════════════════════════════════
API_PROVIDER = "groq"
API_KEY = "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"
API_URL = "https://api.groq.com/openai/v1/chat/completions"
API_MODEL = "openai/gpt-oss-120b"

DATA_DIR = "cherry_data"
AI_FILE = os.path.join(DATA_DIR, "ai_config.json")
SUMMARIES_FILE = os.path.join(DATA_DIR, "summaries.json")

SYSTEM_PROMPT = (
    "أنت مساعد ذكي مختصر. "
    "رد بالعربي بإجابات قصيرة ومفيدة. "
    "لو السؤال بالإنجليزي، رد بالإنجليزي."
)

SUMMARIZE_PROMPT = """أنت محلل محادثات محترف. اقرأ الرسائل التالية ولخّصها بالعربي.

**المطلوب:**
1. 📝 **ملخص عام** (2-3 أسطر يوضح الموضوع الرئيسي)
2. 📌 **النقاط المهمة** (5-10 نقاط بصيغة bullets)
3. 👥 **أكثر المشاركين** (أسماء + عدد رسائلهم)
4. 🔗 **المواضيع الرئيسية** (كلمات مفتاحية)
5. 🎯 **الخلاصة** (جملة وحدة)

**الرسائل:**
---
{messages}
---

**اكتب التلخيص بشكل منظم وواضح.**
"""

USER_ANALYSIS_PROMPT = """أنت محلل شخصيات. حلل رسائل المستخدم التالية:

**المطلوب:**
1. 📊 **إحصائيات** (عدد رسائل، أوقات نشاط)
2. 💬 **المواضيع اللي يتكلم عنها** (5 نقاط)
3. 🎭 **أسلوب الكلام** (رسمي/عامي، طويل/قصير)
4. 🎯 **الاهتمامات** (استنتاج من كلامه)
5. 👤 **نبذة مختصرة** عنه

**الرسائل:**
---
{messages}
---

**اكتب التحليل بشكل موضوعي ومحترم.**
"""

MAX_HISTORY = 10
MAX_TOKENS = 2000
FETCH_TIMEOUT = 60


# ═════════════════════════════════════════
# 🤖 كلاس AI
# ═════════════════════════════════════════
class AI(commands.Cog):
    """🤖 ردود AI + تلخيص + تحليل"""

    def __init__(self, bot):
        self.bot = bot
        self.config = {}
        self.summaries = {}

        os.makedirs(DATA_DIR, exist_ok=True)
        self._load()

    # ═════════════════════════════════════════
    # 📂 تحميل / حفظ
    # ═════════════════════════════════════════
    def _load(self):
        # ai_config
        if os.path.exists(AI_FILE):
            try:
                with open(AI_FILE, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
            except:
                self.config = {}

        self.config.setdefault("enabled", True)
        self.config.setdefault("trigger_word", "ai")
        self.config.setdefault("history", {})
        self.config.setdefault("default_limit", 1000)
        self._save_config()

        # summaries
        if os.path.exists(SUMMARIES_FILE):
            try:
                with open(SUMMARIES_FILE, 'r', encoding='utf-8') as f:
                    self.summaries = json.load(f)
            except:
                self.summaries = {}

        self.summaries.setdefault("summaries", {})
        self.summaries.setdefault("user_analyses", {})
        self._save_summaries()

    def _save_config(self):
        try:
            with open(AI_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except:
            pass

    def _save_summaries(self):
        try:
            with open(SUMMARIES_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.summaries, f, indent=2, ensure_ascii=False)
        except:
            pass

    # ═════════════════════════════════════════
    # 🌐 استدعاء Groq API
    # ═════════════════════════════════════════
    async def _call_api(self, messages, max_tokens=MAX_TOKENS, temperature=0.7):
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": API_MODEL,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        try:
            timeout = aiohttp.ClientTimeout(total=FETCH_TIMEOUT)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(API_URL, headers=headers, json=payload) as resp:

                    if resp.status == 401:
                        return "❌ مفتاح API غلط أو منتهي"
                    if resp.status == 429:
                        return "⏳ تم تجاوز الحد (Rate Limit). جرب بعد شوي"
                    if resp.status != 200:
                        err = await resp.text()
                        return f"❌ خطأ API ({resp.status}):\n```{err[:200]}```"

                    data = await resp.json()
                    return data["choices"][0]["message"]["content"].strip()

        except asyncio.TimeoutError:
            return "⏳ AI تأخر بالرد. جرب مرة ثانية"
        except aiohttp.ClientError as e:
            return f"❌ خطأ اتصال: `{e}`"
        except Exception as e:
            return f"❌ خطأ: `{type(e).__name__}: {e}`"

    # ═════════════════════════════════════════
    # 🤖 ask_ai — للـ محادثة العادية
    # ═════════════════════════════════════════
    async def ask_ai(self, user_id: str, question: str) -> str:
        history = self.config.get("history", {}).get(user_id, [])

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend(history[-MAX_HISTORY:])
        messages.append({"role": "user", "content": question})

        reply = await self._call_api(messages)

        if "❌" not in reply and "⏳" not in reply:
            if "history" not in self.config:
                self.config["history"] = {}
            if user_id not in self.config["history"]:
                self.config["history"][user_id] = []

            self.config["history"][user_id].append(
                {"role": "user", "content": question}
            )
            self.config["history"][user_id].append(
                {"role": "assistant", "content": reply}
            )

            max_msgs = MAX_HISTORY * 2
            self.config["history"][user_id] = self.config["history"][user_id][-max_msgs:]
            self._save_config()

        return reply

    # ═════════════════════════════════════════
    # 📥 جلب الرسائل من روم
    # ═════════════════════════════════════════
    async def _fetch_messages(self, channel, limit: int, oldest_first: bool = False,
                              user_id: int = None):
        """
        يجلب الرسائل من الروم
        - oldest_first: True = من البداية (الأقدم أول)
        - user_id: يفلتر رسائل شخص معين
        """
        messages = []

        try:
            if oldest_first:
                # من الأقدم للأحدث
                async for msg in channel.history(limit=limit, oldest_first=True):
                    if user_id and msg.author.id != user_id:
                        continue
                    if msg.author.bot:
                        continue
                    if not msg.content and not msg.attachments:
                        continue
                    messages.append(msg)
            else:
                # من الأحدث للأقدم، ثم نعكس
                async for msg in channel.history(limit=limit):
                    if user_id and msg.author.id != user_id:
                        continue
                    if msg.author.bot:
                        continue
                    if not msg.content and not msg.attachments:
                        continue
                    messages.append(msg)
                messages.reverse()

        except discord.Forbidden:
            return None
        except Exception as e:
            print(f"❌ فشل جلب الرسائل: {e}")
            return None

        return messages

    # ═════════════════════════════════════════
    # 📝 ضغط الرسائل قبل إرسالها للـ AI
    # ═════════════════════════════════════════
    def _compress_messages(self, messages, max_chars: int = 60000):
        """يضغط الرسائل عشان ما تتجاوز حجم AI"""
        lines = []
        char_count = 0
        last_author = None

        for msg in messages:
            content = msg.content.strip()

            # تجاهل القصير جداً
            if len(content) < 2 and not msg.attachments:
                continue

            # إرفاق الصور
            if msg.attachments:
                att_text = f" [📎{len(msg.attachments)} مرفق]"
            else:
                att_text = ""

            # اختصار لو نفس الشخص يكتب متتالي
            if msg.author == last_author:
                line = f"  ↳ {content}{att_text}"
            else:
                line = f"\n**{msg.author.display_name}:** {content}{att_text}"
                last_author = msg.author

            # تحقق من الحد
            if char_count + len(line) > max_chars:
                lines.append(f"\n...(تم اقتصاص {len(messages) - len(lines)} رسالة)")
                break

            lines.append(line)
            char_count += len(line)

        return "".join(lines)

    # ═════════════════════════════════════════
    # 📊 إحصائيات الرسائل
    # ═════════════════════════════════════════
    def _get_stats(self, messages):
        authors = Counter()
        channels = Counter()
        attachments = 0

        for msg in messages:
            authors[msg.author.display_name] += 1
            channels[msg.channel.name if hasattr(msg.channel, 'name') else 'DM'] += 1
            attachments += len(msg.attachments)

        return {
            "total": len(messages),
            "top_authors": authors.most_common(5),
            "attachments": attachments,
        }

    # ═════════════════════════════════════════
    # 📌 !sum — يلخص آخر N رسالة
    # ═════════════════════════════════════════
    @commands.command(name="sum")
    async def sum_cmd(self, ctx, limit: int = None, channel_id: int = None, *,
                      extra: str = ""):
        """
        !sum → آخر 1000 رسالة في الروم الحالي
        !sum 500 → آخر 500
        !sum 500 123456789 → من روم ثاني
        """
        try:
            await ctx.message.delete()
        except:
            pass

        if limit is None:
            limit = self.config.get("default_limit", 1000)

        if limit > 5000:
            return await ctx.send("⚠️ الحد الأقصى 5000 رسالة")

        # تحديد الروم
        if channel_id:
            channel = self.bot.get_channel(channel_id)
            if not channel:
                try:
                    channel = await self.bot.fetch_channel(channel_id)
                except:
                    return await ctx.send(f"❌ ما لقيت الروم: `{channel_id}`")
        else:
            channel = ctx.channel

        ch_name = getattr(channel, 'name', 'DM')

        msg = await ctx.send(f"📥 يقرأ آخر {limit} رسالة من `{ch_name}`...")

        # جلب
        messages = await self._fetch_messages(channel, limit, oldest_first=False)

        if messages is None:
            return await msg.edit(content=f"❌ ما قدرت أقرأ الرسائل (صلاحيات؟)")

        if len(messages) < 5:
            return await msg.edit(content=f"❌ ما فيه رسائل كافية ({len(messages)})")

        try:
            await msg.edit(content=f"📝 يلخص {len(messages)} رسالة...")
        except:
            pass

        # ضغط + إحصائيات
        compressed = self._compress_messages(messages)
        stats = self._get_stats(messages)

        # استدعاء AI
        prompt = SUMMARIZE_PROMPT.replace("{messages}", compressed)
        reply = await self._call_api(
            [{"role": "user", "content": prompt}],
            max_tokens=2000,
            temperature=0.3,
        )

        if "❌" in reply or "⏳" in reply:
            return await msg.edit(content=reply)

        # حفظ
        sid = f"{channel.id}_{int(asyncio.get_event_loop().time())}"
        self.summaries["summaries"][sid] = {
            "channel_id": str(channel.id),
            "channel_name": ch_name,
            "limit": limit,
            "message_count": len(messages),
            "stats": {
                "total": stats["total"],
                "top_authors": [[a, c] for a, c in stats["top_authors"]],
                "attachments": stats["attachments"],
            },
            "summary": reply,
            "time": discord.utils.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            "type": "latest",
        }
        self._save_summaries()

        # عرض
        header = (
            f"📊 **إحصائيات:**\n"
            f"📨 الرسائل: `{stats['total']}`\n"
            f"👥 المشاركون: `{len(stats['top_authors'])}`\n"
            f"📎 المرفقات: `{stats['attachments']}`\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
        )

        full_text = header + reply

        # إرسال
        if len(full_text) > 1900:
            try:
                await msg.edit(content=header)
            except:
                pass
            parts = [reply[i:i+1900] for i in range(0, len(reply), 1900)]
            for part in parts:
                await ctx.send(part)
                await asyncio.sleep(0.3)
        else:
            try:
                await msg.edit(content=full_text)
            except:
                await ctx.send(full_text)

    # ═════════════════════════════════════════
    # 📌 !sumfirst — يلخص أول N رسالة
    # ═════════════════════════════════════════
    @commands.command(name="sumfirst")
    async def sumfirst_cmd(self, ctx, limit: int = None, channel_id: int = None):
        """
        !sumfirst → أول 1000 رسالة في الروم
        !sumfirst 500 → أول 500
        !sumfirst 500 123456789 → من روم ثاني
        """
        try:
            await ctx.message.delete()
        except:
            pass

        if limit is None:
            limit = self.config.get("default_limit", 1000)

        if limit > 5000:
            return await ctx.send("⚠️ الحد الأقصى 5000 رسالة")

        # الروم
        if channel_id:
            channel = self.bot.get_channel(channel_id)
            if not channel:
                try:
                    channel = await self.bot.fetch_channel(channel_id)
                except:
                    return await ctx.send(f"❌ ما لقيت الروم: `{channel_id}`")
        else:
            channel = ctx.channel

        ch_name = getattr(channel, 'name', 'DM')

        msg = await ctx.send(f"📥 يقرأ أول {limit} رسالة من `{ch_name}`...")

        # جلب
        messages = await self._fetch_messages(channel, limit, oldest_first=True)

        if messages is None:
            return await msg.edit(content="❌ ما قدرت أقرأ الرسائل")

        if len(messages) < 5:
            return await msg.edit(content=f"❌ ما فيه رسائل كافية ({len(messages)})")

        try:
            await msg.edit(content=f"📝 يلخص {len(messages)} رسالة...")
        except:
            pass

        compressed = self._compress_messages(messages)
        stats = self._get_stats(messages)

        prompt = SUMMARIZE_PROMPT.replace("{messages}", compressed)
        reply = await self._call_api(
            [{"role": "user", "content": prompt}],
            max_tokens=2000,
            temperature=0.3,
        )

        if "❌" in reply or "⏳" in reply:
            return await msg.edit(content=reply)

        # حفظ
        sid = f"{channel.id}_first_{int(asyncio.get_event_loop().time())}"
        self.summaries["summaries"][sid] = {
            "channel_id": str(channel.id),
            "channel_name": ch_name,
            "limit": limit,
            "message_count": len(messages),
            "summary": reply,
            "time": discord.utils.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            "type": "first",
        }
        self._save_summaries()

        header = (
            f"📊 **إحصائيات (الأقدم):**\n"
            f"📨 الرسائل: `{stats['total']}`\n"
            f"📎 المرفقات: `{stats['attachments']}`\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
        )

        full_text = header + reply

        if len(full_text) > 1900:
            try:
                await msg.edit(content=header)
            except:
                pass
            parts = [reply[i:i+1900] for i in range(0, len(reply), 1900)]
            for part in parts:
                await ctx.send(part)
                await asyncio.sleep(0.3)
        else:
            try:
                await msg.edit(content=full_text)
            except:
                await ctx.send(full_text)

    # ═════════════════════════════════════════
    # 📌 !user — تحليل شخص
    # ═════════════════════════════════════════
    @commands.command(name="user")
    async def user_cmd(self, ctx, user_id: int, limit: int = None,
                       channel_id: int = None):
        """
        !user <user_id> → آخر 1000 رسالة له في الروم
        !user <user_id> 500 → آخر 500
        !user <user_id> 500 123456789 → من روم ثاني
        """
        try:
            await ctx.message.delete()
        except:
            pass

        if limit is None:
            limit = self.config.get("default_limit", 1000)

        if limit > 5000:
            return await ctx.send("⚠️ الحد الأقصى 5000 رسالة")

        # الروم
        if channel_id:
            channel = self.bot.get_channel(channel_id)
            if not channel:
                try:
                    channel = await self.bot.fetch_channel(channel_id)
                except:
                    return await ctx.send(f"❌ ما لقيت الروم: `{channel_id}`")
        else:
            channel = ctx.channel

        ch_name = getattr(channel, 'name', 'DM')

        # جلب رسائل الشخص
        msg = await ctx.send(f"📥 يقرأ رسائل <@{user_id}> من `{ch_name}`...")

        messages = await self._fetch_messages(
            channel, limit,
            oldest_first=False,
            user_id=user_id
        )

        if messages is None:
            return await msg.edit(content="❌ ما قدرت أقرأ الرسائل")

        if len(messages) < 3:
            return await msg.edit(
                content=f"❌ ما فيه رسائل كافية لـ <@{user_id}> ({len(messages)})"
            )

        try:
            await msg.edit(content=f"🧠 يحلل {len(messages)} رسالة...")
        except:
            pass

        # ضغط
        compressed = self._compress_messages(messages, max_chars=50000)

        prompt = USER_ANALYSIS_PROMPT.replace("{messages}", compressed)
        reply = await self._call_api(
            [{"role": "user", "content": prompt}],
            max_tokens=2000,
            temperature=0.3,
        )

        if "❌" in reply or "⏳" in reply:
            return await msg.edit(content=reply)

        # جمع الصور
        images = []
        for m in messages:
            for att in m.attachments:
                if any(att.filename.lower().endswith(ext)
                       for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']):
                    images.append(att.url)

        # حفظ
        aid = f"{user_id}_{channel.id}_{int(asyncio.get_event_loop().time())}"
        self.summaries["user_analyses"][aid] = {
            "user_id": str(user_id),
            "channel_id": str(channel.id),
            "channel_name": ch_name,
            "message_count": len(messages),
            "images_count": len(images),
            "analysis": reply,
            "time": discord.utils.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        }
        self._save_summaries()

        # عرض
        header = (
            f"👤 **تحليل:** <@{user_id}>\n"
            f"📨 الرسائل: `{len(messages)}`\n"
            f"🖼️ الصور: `{len(images)}`\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
        )

        full_text = header + reply

        if len(full_text) > 1900:
            try:
                await msg.edit(content=header)
            except:
                pass
            parts = [reply[i:i+1900] for i in range(0, len(reply), 1900)]
            for part in parts:
                await ctx.send(part)
                await asyncio.sleep(0.3)
        else:
            try:
                await msg.edit(content=full_text)
            except:
                await ctx.send(full_text)

        # أرسل أول 5 صور لو موجودة
        if images:
            imgs_text = "🖼️ **آخر صوره:**\n" + "\n".join(images[:5])
            try:
                await ctx.send(imgs_text)
            except:
                pass

    # ═════════════════════════════════════════
    # 📊 !sumlist — عرض التلخيصات المحفوظة
    # ═════════════════════════════════════════
    @commands.command(name="sumlist")
    async def sumlist_cmd(self, ctx, limit: int = 10):
        """!sumlist [عدد] → عرض آخر التلخيصات"""
        try:
            await ctx.message.delete()
        except:
            pass

        summaries = self.summaries.get("summaries", {})
        if not summaries:
            return await ctx.send("❌ ما فيه تلخيصات محفوظة")

        items = sorted(
            summaries.items(),
            key=lambda x: x[1].get("time", ""),
            reverse=True
        )[:limit]

        lines = [f"**📝 آخر {len(items)} تلخيص:**\n"]

        for i, (sid, s) in enumerate(items, 1):
            emoji = "📌" if s.get("type") == "first" else "📝"
            lines.append(
                f"`{i}.` {emoji} **{s['channel_name']}**\n"
                f"   📨 `{s['message_count']}` رسالة — ⏰ `{s['time']}`"
            )

        await ctx.send("\n".join(lines)[:1900])

    # ═════════════════════════════════════════
    # 🗑️ !sumclear — مسح التلخيصات
    # ═════════════════════════════════════════
    @commands.command(name="sumclear")
    async def sumclear_cmd(self, ctx, confirm: str = ""):
        """!sumclear yes → مسح كل التلخيصات"""
        if confirm.lower() != "yes":
            return await ctx.send("⚠️ اكتب `!sumclear yes` للتأكيد")

        try:
            await ctx.message.delete()
        except:
            pass

        self.summaries["summaries"] = {}
        self.summaries["user_analyses"] = {}
        self._save_summaries()

        await ctx.send("✅ تم مسح كل التلخيصات")

    # ═════════════════════════════════════════
    # 🎧 on_message — الرد التلقائي (القديم)
    # ═════════════════════════════════════════
    @commands.Cog.listener()
    async def on_message(self, message):
        if not self.config.get("enabled", True):
            return
        if message.author.id == self.bot.user.id:
            return
        if message.author.bot:
            return
        if message.content.startswith("!"):
            return

        mentioned_me = self.bot.user in message.mentions

        replied_to_me = False
        if message.reference:
            try:
                ref = await message.channel.fetch_message(message.reference.message_id)
                if ref.author.id == self.bot.user.id:
                    replied_to_me = True
            except:
                pass

        if not (mentioned_me or replied_to_me):
            return

        content = message.content
        content = content.replace(f"<@{self.bot.user.id}>", "")
        content = content.replace(f"<@!{self.bot.user.id}>", "")
        content = content.strip()

        trigger = self.config.get("trigger_word", "ai").lower()

        if not content.lower().startswith(trigger):
            return

        question = content[len(trigger):].strip()

        if not question:
            try:
                await message.reply(
                    f"❌ اكتب سؤال بعد `{trigger}`\n"
                    f"مثال: `{trigger} ايش عاصمة السعودية؟`",
                    mention_author=False
                )
            except:
                pass
            return

        try:
            async with message.channel.typing():
                reply = await self.ask_ai(str(message.author.id), question)
        except:
            reply = await self.ask_ai(str(message.author.id), question)

        await self._send_reply(message, reply)

    async def _send_reply(self, message, reply):
        if len(reply) > 1900:
            parts = [reply[i:i+1900] for i in range(0, len(reply), 1900)]
            for part in parts:
                try:
                    await message.reply(part, mention_author=False)
                except:
                    try:
                        await message.channel.send(part)
                    except:
                        pass
                await asyncio.sleep(0.3)
        else:
            try:
                await message.reply(reply, mention_author=False)
            except:
                try:
                    await message.channel.send(reply)
                except:
                    pass

    # ═════════════════════════════════════════
    # 🎮 !ai — سؤال مباشر
    # ═════════════════════════════════════════
    @commands.command(name="ai")
    async def ai_cmd(self, ctx, *, question: str = ""):
        """!ai <سؤال> → اسأل AI"""
        try:
            await ctx.message.delete()
        except:
            pass

        if not question.strip():
            return await ctx.send("❌ اكتب سؤال")

        msg = await ctx.send("🤔 يفكر...")
        reply = await self.ask_ai(str(ctx.author.id), question)

        if len(reply) > 1900:
            try:
                await msg.delete()
            except:
                pass
            parts = [reply[i:i+1900] for i in range(0, len(reply), 1900)]
            for part in parts:
                await ctx.send(part)
                await asyncio.sleep(0.3)
        else:
            try:
                await msg.edit(content=reply)
            except:
                await ctx.send(reply)

    # ═════════════════════════════════════════
    # ⚙️ !aiset — إعدادات AI
    # ═════════════════════════════════════════
    @commands.command(name="aiset")
    async def aiset(self, ctx, action: str = "status", *, value: str = ""):
        """
        !aiset status → عرض الحالة
        !aiset on / off → تفعيل/إيقاف
        !aiset word <كلمة> → تغيير كلمة التشغيل
        !aiset limit <رقم> → تغيير الحد الافتراضي
        !aiset clear → مسح سجل المحادثات
        !aiset clearme → مسح سجلك
        """
        try:
            await ctx.message.delete()
        except:
            pass

        action = action.lower()

        if action == "status":
            enabled = "🟢 شغال" if self.config.get("enabled") else "🔴 متوقف"
            word = self.config.get("trigger_word", "ai")
            default_limit = self.config.get("default_limit", 1000)
            users = len(self.config.get("history", {}))
            total_msgs = sum(len(v) for v in self.config.get("history", {}).values())
            total_sums = len(self.summaries.get("summaries", {}))
            total_analyses = len(self.summaries.get("user_analyses", {}))

            await ctx.send(
                f"**🤖 إعدادات AI:**\n"
                f"الحالة: {enabled}\n"
                f"كلمة التشغيل: `{word}`\n"
                f"الحد الافتراضي: `{default_limit}`\n"
                f"المزود: `{API_PROVIDER}`\n"
                f"الموديل: `{API_MODEL}`\n\n"
                f"**📊 الإحصائيات:**\n"
                f"مستخدمين: `{users}`\n"
                f"رسائل محفوظة: `{total_msgs}`\n"
                f"تلخيصات: `{total_sums}`\n"
                f"تحليلات: `{total_analyses}`\n\n"
                f"**الأوامر:**\n"
                f"`!sum [عدد]` — تلخيص آخر رسائل\n"
                f"`!sumfirst [عدد]` — تلخيص أول رسائل\n"
                f"`!user <id> [عدد]` — تحليل شخص\n"
                f"`!sumlist` — عرض التلخيصات\n"
                f"`!sumclear yes` — مسح التلخيصات"
            )
            return

        if action == "on":
            self.config["enabled"] = True
            self._save_config()
            return await ctx.send("✅ تم تفعيل AI")

        if action == "off":
            self.config["enabled"] = False
            self._save_config()
            return await ctx.send("🛑 تم إيقاف AI")

        if action == "word":
            if not value.strip():
                return await ctx.send("❌ اكتب: `!aiset word <كلمة>`")
            self.config["trigger_word"] = value.strip().lower()
            self._save_config()
            return await ctx.send(f"✅ كلمة التشغيل: `{value.strip()}`")

        if action == "limit":
            try:
                lim = int(value.strip())
                if lim < 1 or lim > 5000:
                    raise ValueError
                self.config["default_limit"] = lim
                self._save_config()
                return await ctx.send(f"✅ الحد الافتراضي: `{lim}`")
            except:
                return await ctx.send("❌ اكتب رقم بين 1 و 5000")

        if action == "clear":
            self.config["history"] = {}
            self._save_config()
            return await ctx.send("✅ تم مسح سجل المحادثات")

        if action == "clearme":
            uid = str(ctx.author.id)
            if uid in self.config.get("history", {}):
                del self.config["history"][uid]
                self._save_config()
                return await ctx.send("✅ تم مسح سجلك")
            return await ctx.send("❌ ما عندك سجل")

        await ctx.send(
            "**الأوامر:**\n"
            "`!aiset status` — الحالة\n"
            "`!aiset on` / `off` — تفعيل/إيقاف\n"
            "`!aiset word <كلمة>` — تغيير الكلمة\n"
            "`!aiset limit <رقم>` — الحد الافتراضي\n"
            "`!aiset clear` — مسح كل السجل\n"
            "`!aiset clearme` — مسح سجلك فقط"
        )

    # ═════════════════════════════════════════
    # 🧪 !aitest — اختبار الاتصال
    # ═════════════════════════════════════════
    @commands.command(name="aitest")
    async def aitest(self, ctx):
        """!aitest → اختبار الاتصال بـ AI API"""
        try:
            await ctx.message.delete()
        except:
            pass

        msg = await ctx.send("🧪 يختبر الاتصال...")
        reply = await self.ask_ai("test_user", "قل: مرحبا")

        if "❌" in reply or "⏳" in reply:
            await msg.edit(content=f"❌ فشل الاختبار:\n{reply}")
        else:
            await msg.edit(content=f"✅ الاتصال شغال!\nالرد: `{reply[:100]}`")


async def setup(bot):
    await bot.add_cog(AI(bot))