
import discord
from discord.ext import commands
import json
import os
import asyncio
import random


DATA_DIR = "cherry_data"
WELCOME_FILE = os.path.join(DATA_DIR, "welcome.json")
TRIGGERS_FILE = os.path.join(DATA_DIR, "triggers.json")
STALKERS_FILE = os.path.join(DATA_DIR, "stalkers.json")


class AutoReply(commands.Cog):
    """🤖 ترحيب + ردود تلقائية"""

    def __init__(self, bot):
        self.bot = bot
        self.welcome = {}

        self.triggers = {}

        self.stalkers = {}

        os.makedirs(DATA_DIR, exist_ok=True)
        self._load()


    def _load_json(self, path, default):
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return default
        return default

    def _save_json(self, path, data):
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except:
            pass

    def _load(self):
        self.welcome = self._load_json(WELCOME_FILE, {})
        self.triggers = self._load_json(TRIGGERS_FILE, {})
        self.stalkers = self._load_json(STALKERS_FILE, {})

    def _save_welcome(self):
        self._save_json(WELCOME_FILE, self.welcome)

    def _save_triggers(self):
        self._save_json(TRIGGERS_FILE, self.triggers)

    def _save_stalkers(self):
        self._save_json(STALKERS_FILE, self.stalkers)

    @commands.command(name="welcome")
    async def welcome_cmd(self, ctx, action: str = "status", *, args: str = ""):
        """
        !welcome set #channel <الرسالة>
        !welcome off
        !welcome status

        المتغيرات: {user} {guild} {name}
        """
        try:
            await ctx.message.delete()
        except:
            pass

        gid = str(ctx.guild.id)
        action = action.lower()

        
        if action == "off":
            if gid in self.welcome:
                self.welcome[gid]["enabled"] = False
                self._save_welcome()
            return await ctx.send("✅ تم إيقاف الترحيب")

        if action == "status":
            cfg = self.welcome.get(gid)
            if not cfg or not cfg.get("enabled"):
                return await ctx.send(
                    "❌ الترحيب مو مفعّل\n"
                    "**للتفعيل:** `!welcome set #channel <رسالة>`"
                )

            ch = ctx.guild.get_channel(int(cfg["channel_id"]))
            return await ctx.send(
                f"**👋 الترحيب:**\n"
                f"📢 القناة: {ch.mention if ch else '❓'}\n"
                f"💬 الرسالة: `{cfg['message']}`"
            )

    
        if action == "set":
            parts = args.split(maxsplit=1)
            if len(parts) < 2:
                return await ctx.send(
                    "❌ الاستخدام:\n"
                    "`!welcome set #channel <الرسالة>`\n"
                    "مثال: `!welcome set #general أهلاً {user} في {guild}!`"
                )

            channel_mention = parts[0]
            msg = parts[1]

            if channel_mention.startswith("<#") and channel_mention.endswith(">"):
                channel_id = channel_mention[2:-1]
            else:
                try:
                    channel_id = str(int(channel_mention))
                except:
                    return await ctx.send("❌ حدد قناة بمنشن `<#channel>`")

            channel = ctx.guild.get_channel(int(channel_id))
            if not channel:
                return await ctx.send("❌ ما لقيت القناة")

            self.welcome[gid] = {
                "enabled": True,
                "channel_id": channel_id,
                "message": msg,
            }
            self._save_welcome()

            return await ctx.send(
                f"✅ **تم تفعيل الترحيب**\n"
                f"📢 {channel.mention}\n"
                f"💬 `{msg}`"
            )

        await ctx.send("❌ الاستخدام: `!welcome set|off|status`")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        gid = str(member.guild.id)
        cfg = self.welcome.get(gid)

        if not cfg or not cfg.get("enabled"):
            return

        try:
            channel = member.guild.get_channel(int(cfg["channel_id"]))
            if not channel:
                return

            msg = cfg["message"]
            msg = msg.replace("{user}", member.mention)
            msg = msg.replace("{guild}", member.guild.name)
            msg = msg.replace("{name}", member.name)

            await channel.send(msg)
            print(f"👋 رحّبنا بـ: {member}")
        except Exception as e:
            print(f"❌ فشل الترحيب: {e}")

    @commands.command(name="trigger")
    async def trigger_cmd(self, ctx, action: str = "list", *, args: str = ""):
        """
        !trigger add <كلمة> | <رد1> | <رد2>
        !trigger react <كلمة> <emoji>
        !trigger del <كلمة>
        !trigger list
        !trigger clear yes
        """
        try:
            await ctx.message.delete()
        except:
            pass

        gid = str(ctx.guild.id)
        action = action.lower()

        if gid not in self.triggers:
            self.triggers[gid] = {}

        
        if action == "list":
            triggers = self.triggers.get(gid, {})
            if not triggers:
                return await ctx.send("❌ ما فيه كلمات مضافة")

            lines = [f"**💬 الكلمات ({len(triggers)}):**\n"]
            for i, (word, cfg) in enumerate(triggers.items(), 1):
                replies = cfg.get("replies", [])
                react = cfg.get("react", "")
                line = f"`{i}.` **{word}**"
                if replies:
                    line += f" — 💬 {len(replies)} رد"
                if react:
                    line += f" — 🎯 {react}"
                lines.append(line)

            text = "\n".join(lines)
            return await ctx.send(text[:1900])

        
        if action == "add":
            if "|" not in args:
                return await ctx.send(
                    "❌ `!trigger add <كلمة> | <رد1> [| <رد2>]`\n"
                    "مثال: `!trigger add مرحبا | أهلاً | هلا والله`"
                )

            parts = [p.strip() for p in args.split("|")]
            word = parts[0].lower()
            replies = parts[1:]

            if not word:
                return await ctx.send("❌ الكلمة فاضية")
            if not replies:
                return await ctx.send("❌ لازم رد واحد على الأقل")

            self.triggers[gid][word] = {
                "replies": replies,
                "react": None,
            }
            self._save_triggers()

            return await ctx.send(
                f"✅ **تمت الإضافة:** `{word}`\n"
                f"💬 عدد الردود: `{len(replies)}`"
            )

       
        if action == "react":
            parts = args.split(maxsplit=1)
            if len(parts) < 2:
                return await ctx.send("❌ `!trigger react <كلمة> <emoji>`")

            word = parts[0].lower()
            emoji = parts[1].strip()

            if word not in self.triggers[gid]:
                return await ctx.send(f"❌ الكلمة `{word}` مو مضافة")

            self.triggers[gid][word]["react"] = emoji
            self._save_triggers()

            return await ctx.send(f"✅ رد فعل لـ `{word}`: {emoji}")

       
        if action == "del":
            word = args.strip().lower()
            if word in self.triggers.get(gid, {}):
                del self.triggers[gid][word]
                self._save_triggers()
                return await ctx.send(f"✅ تم حذف `{word}`")
            return await ctx.send(f"❌ `{word}` مو موجودة")

     
        if action == "clear":
            if args.strip().lower() != "yes":
                return await ctx.send("⚠️ اكتب `!trigger clear yes`")
            self.triggers[gid] = {}
            self._save_triggers()
            return await ctx.send("✅ تم مسح كل الكلمات")

        await ctx.send("❌ الاستخدام: `!trigger add|del|list|react|clear`")


    @commands.command(name="stalk")
    async def stalk_cmd(self, ctx, action: str = "list", *, args: str = ""):
        """
        !stalk add <user_id> | <رد1> | <رد2>
        !stalk react <user_id> <emoji>
        !stalk on <user_id> / off <user_id>
        !stalk del <user_id>
        !stalk list
        """
        try:
            await ctx.message.delete()
        except:
            pass

        gid = str(ctx.guild.id)
        action = action.lower()

        if gid not in self.stalkers:
            self.stalkers[gid] = {}

        # ─── عرض ───
        if action == "list":
            stalkers = self.stalkers.get(gid, {})
            if not stalkers:
                return await ctx.send("❌ ما فيه أشخاص مضافين")

            lines = [f"**👤 أشخاص مراقبين ({len(stalkers)}):**\n"]
            for i, (uid, cfg) in enumerate(stalkers.items(), 1):
                try:
                    user = await self.bot.fetch_user(int(uid))
                    name = str(user)
                except:
                    name = "❓"

                enabled = "🟢" if cfg.get("enabled", True) else "🔴"
                replies = cfg.get("replies", [])
                react = cfg.get("react", "")

                line = f"`{i}.` {enabled} **{name}** (`{uid}`)"
                if replies:
                    line += f"\n   💬 {len(replies)} رد"
                if react:
                    line += f"\n   🎯 {react}"
                lines.append(line)

            return await ctx.send("\n".join(lines)[:1900])

       
        if action == "add":
            if "|" not in args:
                return await ctx.send(
                    "❌ `!stalk add <user_id> | <رد1> [| <رد2>]`"
                )

            parts = [p.strip() for p in args.split("|")]
            uid = parts[0]
            replies = parts[1:]

            try:
                uid = str(int(uid))
            except:
                return await ctx.send("❌ user_id لازم رقم")

            if not replies:
                return await ctx.send("❌ لازم رد واحد على الأقل")

            self.stalkers[gid][uid] = {
                "replies": replies,
                "react": None,
                "enabled": True,
            }
            self._save_stalkers()

            return await ctx.send(
                f"✅ **تمت الإضافة:** `{uid}`\n"
                f"💬 عدد الردود: `{len(replies)}`"
            )

        
        if action == "react":
            parts = args.split(maxsplit=1)
            if len(parts) < 2:
                return await ctx.send("❌ `!stalk react <user_id> <emoji>`")

            uid = parts[0].strip()
            emoji = parts[1].strip()

            if uid not in self.stalkers[gid]:
                return await ctx.send(f"❌ `{uid}` مو مضاف")

            self.stalkers[gid][uid]["react"] = emoji
            self._save_stalkers()

            return await ctx.send(f"✅ رد فعل: {emoji}")

       
        if action == "del":
            uid = args.strip()
            if uid in self.stalkers.get(gid, {}):
                del self.stalkers[gid][uid]
                self._save_stalkers()
                return await ctx.send(f"✅ تم حذف `{uid}`")
            return await ctx.send(f"❌ `{uid}` مو موجود")

      
        if action in ("on", "off"):
            uid = args.strip()
            if uid not in self.stalkers.get(gid, {}):
                return await ctx.send(f"❌ `{uid}` مو موجود")

            self.stalkers[gid][uid]["enabled"] = (action == "on")
            self._save_stalkers()

            status = "تشغيل" if action == "on" else "إيقاف"
            return await ctx.send(f"✅ تم {status} `{uid}`")

        await ctx.send("❌ الاستخدام: `!stalk add|del|list|react|on|off`")


    @commands.Cog.listener()
    async def on_message(self, message):
      
        if message.author.id == self.bot.user.id:
            return
        if message.author.bot:
            return
        if message.content.startswith("!"):
            return
        if not message.guild:
            return

        gid = str(message.guild.id)

        
        stalkers = self.stalkers.get(gid, {})
        uid = str(message.author.id)

        if uid in stalkers:
            cfg = stalkers[uid]
            if cfg.get("enabled", True):
                react = cfg.get("react")
                if react:
                    try:
                        await message.add_reaction(react)
                    except:
                        pass

                replies = cfg.get("replies", [])
                if replies:
                    reply = random.choice(replies)
                    try:
                        await message.reply(reply, mention_author=False)
                    except:
                        try:
                            await message.channel.send(reply)
                        except:
                            pass
                return  

       
        triggers = self.triggers.get(gid, {})
        content_lower = message.content.lower()

        for word, cfg in triggers.items():
            if word in content_lower:
                react = cfg.get("react")
                if react:
                    try:
                        await message.add_reaction(react)
                    except:
                        pass

                replies = cfg.get("replies", [])
                if replies:
                    reply = random.choice(replies)
                    try:
                        await message.reply(reply, mention_author=False)
                    except:
                        try:
                            await message.channel.send(reply)
                        except:
                            pass

                break  


async def setup(bot):
    await bot.add_cog(AutoReply(bot))