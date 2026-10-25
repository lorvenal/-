# cogs/status.py
import discord
from discord.ext import commands
import asyncio
import json
import os


DATA_DIR = "cherry_data"
STATUS_FILE = os.path.join(DATA_DIR, "status_config.json")


class Status(commands.Cog):
    """🎮 أوامر حالة الحساب (Rich Presence)"""

    def __init__(self, bot):
        self.bot = bot
        os.makedirs(DATA_DIR, exist_ok=True)
        self._load()

    # ═════════════════════════════════════════
    # 📂 تحميل / حفظ
    # ═════════════════════════════════════════
    def _load(self):
        if os.path.exists(STATUS_FILE):
            try:
                with open(STATUS_FILE, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
            except:
                self.config = {}
        else:
            self.config = {}

    def _save(self):
        try:
            with open(STATUS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except:
            pass

    # ═════════════════════════════════════════
    # 🎮 setstatus — تغيير الحالة
    # ═════════════════════════════════════════
    @commands.command(name="setstatus")
    async def setstatus(self, ctx, status_type: str, *, text: str = ""):
        """
        !setstatus play <لعبة>
        !setstatus listen <شي>
        !setstatus watch <شي>
        !setstatus stream <عنوان>
        !setstatus compete <شي>
        !setstatus clear
        """
        try:
            await ctx.message.delete()
        except:
            pass

        status_type = status_type.lower()

        # ─── مسح ───
        if status_type == "clear":
            await self.bot.change_presence(activity=None, status=discord.Status.online)
            self.config["activity"] = None
            self._save()
            return await ctx.send("✅ تم مسح الحالة")

        # ─── تحقق من النص ───
        if not text.strip():
            return await ctx.send(
                "❌ اكتب النص بعد النوع\n"
                "مثال: `!setstatus play Minecraft`"
            )

        # ─── الأنواع ───
        if status_type == "play":
            activity = discord.Game(name=text)
            emoji = "🎮"
        elif status_type == "stream":
            activity = discord.Streaming(
                name=text,
                url="https://www.twitch.tv/discord"
            )
            emoji = "🔴"
        elif status_type == "listen":
            activity = discord.Activity(
                type=discord.ActivityType.listening,
                name=text
            )
            emoji = "🎵"
        elif status_type == "watch":
            activity = discord.Activity(
                type=discord.ActivityType.watching,
                name=text
            )
            emoji = "📺"
        elif status_type == "compete":
            activity = discord.Activity(
                type=discord.ActivityType.competing,
                name=text
            )
            emoji = "🏆"
        else:
            return await ctx.send(
                "❌ الأنواع:\n"
                "`play`, `stream`, `listen`, `watch`, `compete`, `clear`"
            )

        # ─── غيّر الحالة ───
        try:
            await self.bot.change_presence(
                activity=activity,
                status=discord.Status.online
            )
            self.config["activity"] = {
                "type": status_type,
                "text": text,
            }
            self._save()

            await ctx.send(f"{emoji} تم التغيير: **{status_type}** → `{text}`")
        except Exception as e:
            await ctx.send(f"❌ فشل: `{type(e).__name__}: {e}`")

    # ═════════════════════════════════════════
    # 🔴 setstream — Streaming مع رابط
    # ═════════════════════════════════════════
    @commands.command(name="setstream")
    async def setstream(self, ctx, url: str = None, *, title: str = "Live Stream"):
        """!setstream <twitch_url> [عنوان]"""
        try:
            await ctx.message.delete()
        except:
            pass

        if url is None:
            return await ctx.send(
                "❌ الاستخدام:\n"
                "`!setstream https://twitch.tv/username عنوان البث`"
            )

        # ─── تحقق من الرابط ───
        valid_urls = (
            "https://twitch.tv/",
            "https://www.twitch.tv/",
            "https://youtube.com/",
            "https://www.youtube.com/",
        )

        if not url.startswith(valid_urls):
            return await ctx.send(
                "❌ الرابط لازم يكون **Twitch** أو **YouTube**\n"
                "مثال: `https://twitch.tv/username`"
            )

        try:
            activity = discord.Streaming(name=title, url=url)
            await self.bot.change_presence(
                activity=activity,
                status=discord.Status.online
            )

            self.config["activity"] = {
                "type": "stream",
                "text": title,
                "url": url,
            }
            self._save()

            await ctx.send(f"🔴 **Streaming**\n📺 `{title}`\n🔗 {url}")
        except Exception as e:
            await ctx.send(f"❌ فشل: `{type(e).__name__}: {e}`")

    # ═════════════════════════════════════════
    # 👤 الحضور (Online/Idle/DND/Invisible)
    # ═════════════════════════════════════════
    @commands.command(name="setonline")
    async def setonline(self, ctx):
        """!setonline → 🟢 Online"""
        try:
            await ctx.message.delete()
        except:
            pass
        await self.bot.change_presence(status=discord.Status.online)
        self.config["presence"] = "online"
        self._save()
        await ctx.send("🟢 Online")

    @commands.command(name="setidle")
    async def setidle(self, ctx):
        """!setidle → 🌙 Idle"""
        try:
            await ctx.message.delete()
        except:
            pass
        await self.bot.change_presence(status=discord.Status.idle)
        self.config["presence"] = "idle"
        self._save()
        await ctx.send("🌙 Idle")

    @commands.command(name="setdnd")
    async def setdnd(self, ctx):
        """!setdnd → ⛔ Do Not Disturb"""
        try:
            await ctx.message.delete()
        except:
            pass
        await self.bot.change_presence(status=discord.Status.dnd)
        self.config["presence"] = "dnd"
        self._save()
        await ctx.send("⛔ Do Not Disturb")

    @commands.command(name="setinvisible")
    async def setinvisible(self, ctx):
        """!setinvisible → 👻 Invisible"""
        try:
            await ctx.message.delete()
        except:
            pass
        await self.bot.change_presence(status=discord.Status.invisible)
        self.config["presence"] = "invisible"
        self._save()
        await ctx.send("👻 Invisible")

    # ═════════════════════════════════════════
    # 📊 الحالة الحالية
    # ═════════════════════════════════════════
    @commands.command(name="mystatus")
    async def mystatus(self, ctx):
        """!mystatus → الحالة الحالية"""
        try:
            await ctx.message.delete()
        except:
            pass

        activity = self.config.get("activity")
        presence = self.config.get("presence", "online")

        # ─── اسم الحضور ───
        presence_names = {
            "online": "🟢 Online",
            "idle": "🌙 Idle",
            "dnd": "⛔ DND",
            "invisible": "👻 Invisible",
        }

        # ─── اسم الحالة ───
        if not activity:
            activity_text = "❌ ما فيه حالة"
        else:
            atype = activity.get("type", "?")
            atext = activity.get("text", "")
            aurl = activity.get("url", "")

            type_names = {
                "play": "🎮 Playing",
                "stream": "🔴 Streaming",
                "listen": "🎵 Listening to",
                "watch": "📺 Watching",
                "compete": "🏆 Competing in",
            }

            activity_text = f"{type_names.get(atype, atype)} `{atext}`"
            if aurl:
                activity_text += f"\n🔗 {aurl}"

        await ctx.send(
            f"**📊 حالتك الحالية:**\n"
            f"👤 الحضور: {presence_names.get(presence, presence)}\n"
            f"🎭 الحالة: {activity_text}"
        )

    # ═════════════════════════════════════════
    # 🧪 اختبار سريع
    # ═════════════════════════════════════════
    @commands.command(name="statustest")
    async def statustest(self, ctx):
        """!statustest → يجرب كل الحالات"""
        try:
            await ctx.message.delete()
        except:
            pass

        msg = await ctx.send("🧪 يختبر كل الحالات...")

        tests = [
            ("🎮 Playing", discord.Game(name="Minecraft")),
            ("🎵 Listening", discord.Activity(type=discord.ActivityType.listening, name="Spotify")),
            ("📺 Watching", discord.Activity(type=discord.ActivityType.watching, name="YouTube")),
            ("🔴 Streaming", discord.Streaming(name="Test Stream", url="https://twitch.tv/discord")),
        ]

        for label, act in tests:
            try:
                await self.bot.change_presence(activity=act)
                await msg.edit(content=f"✅ تم: {label}")
                await asyncio.sleep(2)
            except Exception as e:
                await msg.edit(content=f"❌ فشل: {label} — {e}")
                await asyncio.sleep(1)

        # رجع للمسح
        await self.bot.change_presence(activity=None)
        await msg.edit(content="✅ انتهى الاختبار — تم مسح الحالة")

    # ═════════════════════════════════════════
    # 📋 قائمة الحالات المتوفرة
    # ═════════════════════════════════════════
    @commands.command(name="statushelp")
    async def statushelp(self, ctx):
        """!statushelp → شرح أوامر الحالة"""
        try:
            await ctx.message.delete()
        except:
            pass

        text = (
            "**🎮 أوامر الحالة:**\n\n"
            "**الأنواع:**\n"
            "- `!setstatus play <لعبة>` — Playing\n"
            "- `!setstatus listen <شي>` — Listening to\n"
            "- `!setstatus watch <شي>` — Watching\n"
            "- `!setstatus compete <شي>` — Competing in\n"
            "- `!setstatus stream <عنوان>` — Streaming\n"
            "- `!setstatus clear` — مسح الحالة\n\n"
            "**Streaming مع رابط:**\n"
            "- `!setstream <url> [عنوان]`\n"
            "- الرابط: Twitch أو YouTube\n\n"
            "**أمثلة:**\n"
            "`!setstatus play Minecraft`\n"
            "`!setstatus listen Spotify`\n"
            "`!setstream https://twitch.tv/user بث`\n\n"
            "**الحضور:**\n"
            "- `!setonline` / `!setidle` / `!setdnd` / `!setinvisible`\n\n"
            "**عرض:**\n"
            "- `!mystatus` / `!statustest` / `!statushelp`"
        )

        await ctx.send(text)


async def setup(bot):
    await bot.add_cog(Status(bot))