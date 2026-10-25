
import discord
from discord.ext import commands
import json
import os
import asyncio
from datetime import datetime


DATA_DIR = "cherry_data"
DELETED_FILE = os.path.join(DATA_DIR, "deleted_messages.json")
REQUESTS_FILE = os.path.join(DATA_DIR, "friend_requests.json")


class Logger(commands.Cog):
    """📝 يراقب DMs — رسائل محذوفة + طلبات صداقة"""

    def __init__(self, bot):
        self.bot = bot

      
        self.message_cache = {}

      
        self.deleted_messages = []

      
        self.friend_requests = []

        
        self.MAX_CACHE = 5000
        self.MAX_LOGS = 2000

        os.makedirs(DATA_DIR, exist_ok=True)
        self._load()

 
    def _load(self):
        if os.path.exists(DELETED_FILE):
            try:
                with open(DELETED_FILE, 'r', encoding='utf-8') as f:
                    self.deleted_messages = json.load(f)
            except:
                self.deleted_messages = []

        if os.path.exists(REQUESTS_FILE):
            try:
                with open(REQUESTS_FILE, 'r', encoding='utf-8') as f:
                    self.friend_requests = json.load(f)
            except:
                self.friend_requests = []

    def _save_deleted(self):
        try:
            
            self.deleted_messages = self.deleted_messages[-self.MAX_LOGS:]
            with open(DELETED_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.deleted_messages, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"❌ فشل حفظ deleted: {e}")

    def _save_requests(self):
        try:
            self.friend_requests = self.friend_requests[-self.MAX_LOGS:]
            with open(REQUESTS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.friend_requests, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"❌ فشل حفظ requests: {e}")


    @commands.Cog.listener()
    async def on_message(self, message):
       
        if message.author.id == self.bot.user.id:
            return

        
        if message.author.bot:
            return

     
        if not isinstance(message.channel, discord.DMChannel):
            return

       
        if message.content.startswith("!"):
            return

    
        self.message_cache[message.id] = {
            "content": message.content,
            "author_id": str(message.author.id),
            "author_name": str(message.author),
            "author_avatar": str(message.author.display_avatar.url),
            "channel_id": str(message.channel.id),
            "time": message.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "attachments": [a.url for a in message.attachments],
        }

        
        if len(self.message_cache) > self.MAX_CACHE:
       
            keys = sorted(self.message_cache.keys())[:1000]
            for k in keys:
                del self.message_cache[k]


    @commands.Cog.listener()
    async def on_message_delete(self, message):
       
        if message.author.id == self.bot.user.id:
            return

  
        if not isinstance(message.channel, discord.DMChannel):
            return

        cached = self.message_cache.get(message.id)

        if cached:
            entry = {
                "type": "deleted_message",
                "author_id": cached["author_id"],
                "author_name": cached["author_name"],
                "author_avatar": cached["author_avatar"],
                "content": cached["content"],
                "attachments": cached.get("attachments", []),
                "channel_id": cached["channel_id"],
                "original_time": cached["time"],
                "deleted_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            del self.message_cache[message.id]
        else:
         
            entry = {
                "type": "deleted_message",
                "author_id": str(message.author.id),
                "author_name": str(message.author),
                "author_avatar": str(message.author.display_avatar.url),
                "content": message.content or "[unknown]",
                "attachments": [a.url for a in message.attachments],
                "channel_id": str(message.channel.id),
                "original_time": message.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "deleted_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }

        self.deleted_messages.append(entry)
        self._save_deleted()

        print(f"\n🗑️ رسالة محذوفة من: {entry['author_name']}")
        print(f"   📝 المحتوى: {entry['content'][:100]}")
        print(f"   ⏰ الأصلي: {entry['original_time']}")
        print(f"   🗑️ الحذف: {entry['deleted_time']}\n")

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.author.id == self.bot.user.id:
            return
        if before.author.bot:
            return
        if not isinstance(before.channel, discord.DMChannel):
            return
        if before.content == after.content:
            return

        entry = {
            "type": "edited_message",
            "author_id": str(before.author.id),
            "author_name": str(before.author),
            "old_content": before.content,
            "new_content": after.content,
            "channel_id": str(before.channel.id),
            "edited_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        self.deleted_messages.append(entry)
        self._save_deleted()

        print(f"\n✏️ رسالة معدّلة من: {before.author}")
        print(f"   📝 قبل: {before.content[:80]}")
        print(f"   📝 بعد: {after.content[:80]}\n")


    @commands.Cog.listener()
    async def on_relationship_add(self, relationship):
    
        if relationship.type != discord.RelationshipType.incoming_request:
            return

        user = relationship.user

        entry = {
            "user_id": str(user.id),
            "user_name": str(user),
            "user_avatar": str(user.display_avatar.url),
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        if any(r["user_id"] == str(user.id) for r in self.friend_requests):
            return

        self.friend_requests.append(entry)
        self._save_requests()

        print(f"\n👥 طلب صداقة جديد:")
        print(f"   👤 {user}")
        print(f"   🆔 {user.id}")
        print(f"   ⏰ {entry['time']}\n")

    @commands.command(name="deleted")
    async def deleted(self, ctx, limit: int = 20):
        """!deleted [عدد] → عرض الرسائل المحذوفة"""
        try:
            await ctx.message.delete()
        except:
            pass

        if not self.deleted_messages:
            return await ctx.send("✅ ما فيه رسائل محذوفة")

        recent = list(reversed(self.deleted_messages[-limit:]))

        lines = [f"**🗑️ الرسائل المحذوفة (آخر {len(recent)}):**\n"]

        for i, entry in enumerate(recent, 1):
            if entry.get("type") == "edited_message":
                lines.append(
                    f"`{i}.` **✏️ معدّلة** — **{entry['author_name']}**\n"
                    f"   قبل: `{entry['old_content'][:50]}`\n"
                    f"   بعد: `{entry['new_content'][:50]}`\n"
                    f"   🕐 {entry['edited_time']}"
                )
            else:
                att = f"\n   📎 {len(entry.get('attachments', []))} مرفق" if entry.get("attachments") else ""
                lines.append(
                    f"`{i}.` **🗑️ محذوفة** — **{entry['author_name']}**\n"
                    f"   💬 `{entry['content'][:100]}`{att}\n"
                    f"   🕐 {entry['original_time']}\n"
                    f"   🗑️ {entry['deleted_time']}"
                )

        text = "\n\n".join(lines)

        if len(text) > 1900:
            parts = [text[i:i+1900] for i in range(0, len(text), 1900)]
            for part in parts:
                await ctx.send(part)
                await asyncio.sleep(0.3)
        else:
            await ctx.send(text)

    @commands.command(name="requests")
    async def requests(self, ctx, limit: int = 20):
        """!requests [عدد] → عرض طلبات الصداقة"""
        try:
            await ctx.message.delete()
        except:
            pass

        if not self.friend_requests:
            return await ctx.send("✅ ما فيه طلبات صداقة")

        recent = list(reversed(self.friend_requests[-limit:]))

        lines = [f"**👥 طلبات الصداقة (آخر {len(recent)}):**\n"]

        for i, entry in enumerate(recent, 1):
            lines.append(
                f"`{i}.` **{entry['user_name']}**\n"
                f"   🆔 `{entry['user_id']}`\n"
                f"   🕐 {entry['time']}"
            )

        text = "\n".join(lines)

        if len(text) > 1900:
            parts = [text[i:i+1900] for i in range(0, len(text), 1900)]
            for part in parts:
                await ctx.send(part)
                await asyncio.sleep(0.3)
        else:
            await ctx.send(text)

    @commands.command(name="finddel")
    async def finddel(self, ctx, user_id: int = None, limit: int = 30):
        """!finddel <user_id> [عدد] → رسائل شخص محذوفة"""
        try:
            await ctx.message.delete()
        except:
            pass

        if user_id is None:
            return await ctx.send("❌ اكتب: `!finddel <user_id>`")

        uid = str(user_id)
        matches = [e for e in self.deleted_messages if e.get("author_id") == uid]

        if not matches:
            return await ctx.send(f"❌ ما فيه رسائل محذوفة من `{user_id}`")

        recent = list(reversed(matches[-limit:]))

        lines = [f"**🗑️ رسائل محذوفة من `{user_id}` (آخر {len(recent)}):**\n"]

        for i, entry in enumerate(recent, 1):
            if entry.get("type") == "edited_message":
                lines.append(
                    f"`{i}.` ✏️\n"
                    f"   قبل: `{entry['old_content'][:60]}`\n"
                    f"   بعد: `{entry['new_content'][:60]}`\n"
                    f"   🕐 {entry['edited_time']}"
                )
            else:
                lines.append(
                    f"`{i}.` 💬 `{entry['content'][:100]}`\n"
                    f"   🕐 {entry['original_time']}"
                )

        text = "\n\n".join(lines)

        if len(text) > 1900:
            parts = [text[i:i+1900] for i in range(0, len(text), 1900)]
            for part in parts:
                await ctx.send(part)
                await asyncio.sleep(0.3)
        else:
            await ctx.send(text)
    @commands.command(name="clearlogs")
    async def clearlogs(self, ctx, what: str = "all", confirm: str = ""):
        """
        !clearlogs deleted yes → مسح سجل الرسائل المحذوفة
        !clearlogs requests yes → مسح سجل طلبات الصداقة
        !clearlogs all yes → مسح الكل
        """
        if confirm.lower() != "yes":
            return await ctx.send(f"⚠️ اكتب `!clearlogs {what} yes` للتأكيد")

        try:
            await ctx.message.delete()
        except:
            pass

        what = what.lower()

        if what in ("deleted", "all"):
            self.deleted_messages.clear()
            self._save_deleted()

        if what in ("requests", "all"):
            self.friend_requests.clear()
            self._save_requests()

        await ctx.send(f"✅ تم مسح: `{what}`", delete_after=5)

    @commands.command(name="logstats")
    async def logstats(self, ctx):
        """!logstats → إحصائيات المراقبة"""
        try:
            await ctx.message.delete()
        except:
            pass

        deleted_count = sum(1 for e in self.deleted_messages if e.get("type") == "deleted_message")
        edited_count = sum(1 for e in self.deleted_messages if e.get("type") == "edited_message")

        await ctx.send(
            f"**📊 إحصائيات المراقبة:**\n"
            f"🗑️ رسائل محذوفة: `{deleted_count}`\n"
            f"✏️ رسائل معدّلة: `{edited_count}`\n"
            f"👥 طلبات صداقة: `{len(self.friend_requests)}`\n"
            f"💾 في الكاش: `{len(self.message_cache)}`"
        )

    @commands.command(name="cache")
    async def cache_cmd(self, ctx, limit: int = 10):
        """!cache [عدد] → عرض آخر رسائل DM في الكاش"""
        try:
            await ctx.message.delete()
        except:
            pass

        if not self.message_cache:
            return await ctx.send("❌ الكاش فاضي")

        
        sorted_msgs = sorted(
            self.message_cache.items(),
            key=lambda x: x[1]["time"],
            reverse=True
        )[:limit]

        lines = [f"**💾 الكاش (آخر {len(sorted_msgs)}):**\n"]

        for i, (mid, data) in enumerate(sorted_msgs, 1):
            lines.append(
                f"`{i}.` **{data['author_name']}**\n"
                f"   💬 `{data['content'][:80]}`\n"
                f"   🕐 {data['time']}"
            )

        text = "\n".join(lines)

        if len(text) > 1900:
            parts = [text[i:i+1900] for i in range(0, len(text), 1900)]
            for part in parts:
                await ctx.send(part)
                await asyncio.sleep(0.3)
        else:
            await ctx.send(text)


async def setup(bot):
    await bot.add_cog(Logger(bot))