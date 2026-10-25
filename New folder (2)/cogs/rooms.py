# cogs/rooms.py
import discord
from discord.ext import commands
import asyncio
import time


class Rooms(commands.Cog):
    """📁 أوامر الرومات"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="mass_rooms")
    async def mass_rooms(self, ctx, count: int = 50, name: str = "room"):
        """!mass_rooms <عدد> [اسم]"""
        if count < 1 or count > 500:
            return await ctx.send("⚠️ العدد بين 1 و 500")

        try:
            await ctx.message.delete()
        except:
            pass

        msg = await ctx.send(f"⚡ إنشاء {count} روم...")

        created = 0
        failed = 0
        batch_size = 2
        start_time = time.time()

        for batch_start in range(0, count, batch_size):
            batch_end = min(batch_start + batch_size, count)
            batch_tasks = []

            for i in range(batch_start + 1, batch_end + 1):
                batch_tasks.append(ctx.guild.create_text_channel(name=f"{name}-{i}"))

            results = await asyncio.gather(*batch_tasks, return_exceptions=True)

            for idx, result in enumerate(results):
                i = batch_start + idx + 1
                if isinstance(result, Exception):
                    failed += 1
                    print(f"❌ [{i}/{count}] {result}")
                else:
                    created += 1
                    print(f"✅ [{i}/{count}] {result.name}")

            try:
                await msg.edit(content=f"⚡ إنشاء... [{batch_end}/{count}]")
            except:
                pass

            await asyncio.sleep(3)

        elapsed = time.time() - start_time

        await ctx.send(
            f"✅ **انتهى**\n"
            f"📊 نجح: `{created}` | فشل: `{failed}`\n"
            f"⏱️ `{elapsed:.1f}s`"
        )

    @commands.command(name="nuke_channels")
    async def nuke_channels(self, ctx, confirm: str = ""):
        """!nuke_channels yes"""
        if confirm.lower() != "yes":
            return await ctx.send("⚠️ اكتب `!nuke_channels yes` للتأكيد")

        try:
            await ctx.message.delete()
        except:
            pass

        msg = await ctx.send("🗑️ جاري حذف الرومات...")

        deleted = 0
        failed = 0
        total = len(ctx.guild.channels)

        for batch_start in range(0, total, 3):
            channels = ctx.guild.channels[batch_start:batch_start + 3]
            tasks = [ch.delete() for ch in channels]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for r in results:
                if isinstance(r, Exception):
                    failed += 1
                else:
                    deleted += 1

            try:
                await msg.edit(content=f"🗑️ حُذف: {deleted} | فشل: {failed}")
            except:
                pass

            await asyncio.sleep(2)

        await ctx.send(f"✅ انتهى\n🗑️ حُذف: `{deleted}`\n❌ فشل: `{failed}`")

    @commands.command(name="cleanup")
    async def cleanup(self, ctx, prefix: str = None):
        """!cleanup [prefix]"""
        try:
            await ctx.message.delete()
        except:
            pass

        msg = await ctx.send("🗑️ جاري التنظيف...")

        prefixes = [prefix] if prefix else ["room-", "chat-", "temp-"]

        deleted = 0
        failed = 0

        for channel in ctx.guild.text_channels:
            if any(channel.name.startswith(p) for p in prefixes):
                try:
                    await channel.delete()
                    deleted += 1
                    print(f"🗑️ {channel.name}")

                    if deleted % 3 == 0:
                        try:
                            await msg.edit(content=f"🗑️ حُذف: {deleted}")
                        except:
                            pass
                        await asyncio.sleep(1.5)
                except:
                    failed += 1

        await msg.edit(content=
            f"✅ انتهى\n"
            f"🗑️ حُذف: `{deleted}`\n"
            f"❌ فشل: `{failed}`"
        )

    @commands.command(name="roomlist")
    async def roomlist(self, ctx, prefix: str = None):
        """!roomlist [prefix]"""
        try:
            await ctx.message.delete()
        except:
            pass

        channels = ctx.guild.text_channels

        if prefix:
            channels = [ch for ch in channels if ch.name.startswith(prefix)]

        if not channels:
            return await ctx.send("❌ ما فيه رومات")

        total = len(channels)

        lines = [f"**📁 الرومات ({total}):**\n"]

        for i, ch in enumerate(channels[:50], 1):
            lines.append(f"`{i}.` **{ch.name}** (`{ch.id}`)")

        if total > 50:
            lines.append(f"\n... و `{total - 50}` رومات ثانية")

        text = "\n".join(lines)

        if len(text) > 1900:
            parts = [text[i:i+1900] for i in range(0, len(text), 1900)]
            for part in parts:
                await ctx.send(part)
                await asyncio.sleep(0.3)
        else:
            await ctx.send(text)

    @commands.command(name="serverinfo")
    async def serverinfo(self, ctx):
        """!serverinfo"""
        try:
            await ctx.message.delete()
        except:
            pass

        guild = ctx.guild

        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)
        categories = len(guild.categories)

        room_count = len([c for c in guild.text_channels if c.name.startswith("room-")])
        chat_count = len([c for c in guild.text_channels if c.name.startswith("chat-")])
        temp_count = len([c for c in guild.text_channels if c.name.startswith("temp-")])

        await ctx.send(
            f"**📊 معلومات السيرفر:**\n"
            f"📛 الاسم: `{guild.name}`\n"
            f"🆔 ID: `{guild.id}`\n"
            f"👥 الأعضاء: `{guild.member_count}`\n"
            f"📁 الرومات النصية: `{text_channels}`\n"
            f"🔊 الرومات الصوتية: `{voice_channels}`\n"
            f"📂 الفئات: `{categories}`\n"
            f"\n**📌 الرومات اللي عندنا:**\n"
            f"🪝 room-: `{room_count}`\n"
            f"💬 chat-: `{chat_count}`\n"
            f"⚡ temp-: `{temp_count}`"
        )

    @commands.command(name="mkchannels")
    async def mkchannels(self, ctx, *, names: str):
        """!mkchannels اسم1 | اسم2 | اسم3"""
        try:
            await ctx.message.delete()
        except:
            pass

        name_list = [n.strip() for n in names.split("|") if n.strip()]

        if not name_list:
            return await ctx.send("❌ ما فيه أسماء صحيحة")

        if len(name_list) > 20:
            return await ctx.send("⚠️ الحد الأقصى 20 روم")

        msg = await ctx.send(f"⚡ إنشاء {len(name_list)} روم...")

        created = 0
        failed = 0

        for i, name in enumerate(name_list, 1):
            try:
                clean_name = name.replace(" ", "-")[:100]
                await ctx.guild.create_text_channel(name=clean_name)
                created += 1
                print(f"✅ [{i}/{len(name_list)}] {clean_name}")
            except Exception as e:
                failed += 1
                print(f"❌ [{i}/{len(name_list)}] {name}: {e}")

            try:
                await msg.edit(content=f"⚡ إنشاء... [{i}/{len(name_list)}]")
            except:
                pass

            await asyncio.sleep(3)

        await ctx.send(f"✅ انتهى\n📊 نجح: `{created}` | فشل: `{failed}`")

    @commands.command(name="clonech")
    async def clonech(self, ctx, count: int = 5):
        """!clonech <عدد>"""
        if count < 1 or count > 50:
            return await ctx.send("⚠️ العدد بين 1 و 50")

        try:
            await ctx.message.delete()
        except:
            pass

        base_name = ctx.channel.name
        msg = await ctx.send(f"⚡ إنشاء {count} نسخة من `{base_name}`...")

        created = 0
        failed = 0

        for i in range(1, count + 1):
            try:
                await ctx.guild.create_text_channel(name=f"{base_name}-{i}")
                created += 1
                print(f"✅ [{i}/{count}] {base_name}-{i}")
            except Exception as e:
                failed += 1
                print(f"❌ [{i}/{count}] {e}")

            try:
                await msg.edit(content=f"⚡ إنشاء... [{i}/{count}]")
            except:
                pass

            await asyncio.sleep(3)

        await ctx.send(f"✅ انتهى\n📊 نجح: `{created}` | فشل: `{failed}`")


async def setup(bot):
    await bot.add_cog(Rooms(bot))