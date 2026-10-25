import discord
from discord.ext import commands
import asyncio
import time


# ═════════════════════════════════════════
# ⚙️ إعدادات السرعة
# ═════════════════════════════════════════
BATCH_DELETE = 8          # كم رسالة نحذف بالتوازي
BATCH_SLEEP = 0.3         # تأخير بين الدفعات
FAST_BATCH = 15           # سرعة قصوى
FAST_SLEEP = 0.2


class Purge(commands.Cog):
    """🗑️ أوامر حذف الرسائل (سريعة)"""

    def __init__(self, bot):
        self.bot = bot

    # ═════════════════════════════════════════
    # 🔧 دوال مساعدة
    # ═════════════════════════════════════════
    async def _delete_batch(self, messages):
        """يحذف دفعة بالتوازي — يرجّع (نجح، فشل)"""
        tasks = [m.delete() for m in messages]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        ok = 0
        fail = 0
        for r in results:
            if isinstance(r, Exception):
                if isinstance(r, discord.HTTPException) and r.status == 429:
                    # Rate limit — انتظر
                    await asyncio.sleep(2)
                fail += 1
            else:
                ok += 1

        return ok, fail

    # ═════════════════════════════════════════
    # 🗑️ !purge — حذف رسائلك (سريع)
    # ═════════════════════════════════════════
    @commands.command(name="purge")
    async def purge(self, ctx, channel_id: int = None, limit: int = 1000):
        """
        !purge → الروم الحالي
        !purge <channel_id> → روم محدد
        !purge <channel_id> <limit> → بحد معين
        !purge <channel_id> 0 → كل الرسائل
        """
        try:
            await ctx.message.delete()
        except:
            pass

        # ─── الروم ───
        if channel_id is None:
            channel = ctx.channel
        else:
            channel = self.bot.get_channel(channel_id)
            if channel is None:
                try:
                    channel = await self.bot.fetch_channel(channel_id)
                except Exception as e:
                    return await ctx.send(f"❌ ما قدرت أجيب الروم:\n```{e}```")

        channel_name = getattr(channel, "name", "DM")

        msg = await ctx.send(
            f"🗑️ حذف من `{channel_name}`...\n"
            f"الحد: `{limit if limit > 0 else 'الكل'}`"
        )

        deleted = 0
        scanned = 0
        failed = 0
        start_time = time.time()
        history_limit = None if limit == 0 else limit

        # ─── اجمع رسائلك ───
        my_messages = []
        try:
            async for message in channel.history(limit=history_limit):
                scanned += 1
                if message.author.id == self.bot.user.id:
                    my_messages.append(message)

                # تحديث كل 200 رسالة
                if scanned % 200 == 0:
                    try:
                        await msg.edit(content=
                            f"🗑️ `{channel_name}`\n"
                            f"📥 جمع: {len(my_messages)}\n"
                            f"🔍 فُحص: {scanned}"
                        )
                    except:
                        pass
        except discord.Forbidden:
            return await msg.edit(content=f"❌ ما عندي صلاحية في `{channel_name}`")
        except Exception as e:
            return await msg.edit(content=f"❌ خطأ:\n```{type(e).__name__}: {e}```")

        if not my_messages:
            return await msg.edit(content=f"❌ ما فيه رسائل لك في `{channel_name}`")

        try:
            await msg.edit(content=
                f"🗑️ حذف `{channel_name}`...\n"
                f"📊 جاهز: `{len(my_messages)}`"
            )
        except:
            pass

        # ─── احذف بالتوازي ───
        for i in range(0, len(my_messages), BATCH_DELETE):
            batch = my_messages[i:i + BATCH_DELETE]
            ok, fail = await self._delete_batch(batch)
            deleted += ok
            failed += fail

            if (i // BATCH_DELETE) % 3 == 0:
                try:
                    await msg.edit(content=
                        f"🗑️ `{channel_name}`\n"
                        f"✅ حُذف: **{deleted}**\n"
                        f"❌ فشل: `{failed}`\n"
                        f"📊 {deleted}/{len(my_messages)}"
                    )
                except:
                    pass

            await asyncio.sleep(BATCH_SLEEP)

        elapsed = time.time() - start_time

        await msg.edit(content=
            f"✅ **انتهى!**\n"
            f"📁 `{channel_name}`\n"
            f"🗑️ حُذف: **{deleted}**\n"
            f"🔍 فُحص: {scanned}\n"
            f"❌ فشل: {failed}\n"
            f"⏱️ `{elapsed:.1f}s`"
        )

    # ═════════════════════════════════════════
    # ⚡ !purgefast — سرعة قصوى
    # ═════════════════════════════════════════
    @commands.command(name="purgefast")
    async def purgefast(self, ctx, limit: int = 500, channel_id: int = None):
        """
        !purgefast [limit] [channel_id]
        حذف بأقصى سرعة ممكنة (قد يجيب rate limit)
        """
        try:
            await ctx.message.delete()
        except:
            pass

        # ─── الروم ───
        if channel_id is None:
            channel = ctx.channel
        else:
            channel = self.bot.get_channel(channel_id)
            if channel is None:
                try:
                    channel = await self.bot.fetch_channel(channel_id)
                except Exception as e:
                    return await ctx.send(f"❌ ما قدرت أجيب الروم: `{e}`")

        channel_name = getattr(channel, "name", "DM")

        msg = await ctx.send(f"⚡ حذف سريع من `{channel_name}` (آخر {limit})...")

        deleted = 0
        failed = 0
        start_time = time.time()

        # ─── اجمع + احذف بنفس الوقت ───
        batch = []
        try:
            async for message in channel.history(limit=limit):
                if message.author.id == self.bot.user.id:
                    batch.append(message)

                # احذف لما توصل للحد
                if len(batch) >= FAST_BATCH:
                    ok, fail = await self._delete_batch(batch)
                    deleted += ok
                    failed += fail
                    batch = []

                    try:
                        await msg.edit(content=
                            f"⚡ `{channel_name}`\n"
                            f"✅ حُذف: **{deleted}**\n"
                            f"❌ فشل: `{failed}`"
                        )
                    except:
                        pass

                    await asyncio.sleep(FAST_SLEEP)

            # احذف الباقي
            if batch:
                ok, fail = await self._delete_batch(batch)
                deleted += ok
                failed += fail

        except discord.Forbidden:
            return await msg.edit(content=f"❌ ما عندي صلاحية في `{channel_name}`")
        except Exception as e:
            return await msg.edit(content=f"❌ خطأ: `{type(e).__name__}: {e}`")

        elapsed = time.time() - start_time

        await msg.edit(content=
            f"✅ **انتهى!**\n"
            f"📁 `{channel_name}`\n"
            f"🗑️ حُذف: **{deleted}**\n"
            f"❌ فشل: {failed}\n"
            f"⏱️ `{elapsed:.1f}s`"
        )

    # ═════════════════════════════════════════
    # 📦 !purgebulk — bulk delete (14 يوم)
    # ═════════════════════════════════════════
    @commands.command(name="purgebulk")
    async def purgebulk(self, ctx, limit: int = 100, channel_id: int = None):
        """
        !purgebulk [limit] [channel_id]
        يستخدم bulk delete (أسرع شي متاح — 14 يوم فقط)
        """
        try:
            await ctx.message.delete()
        except:
            pass

        # ─── الروم ───
        if channel_id is None:
            channel = ctx.channel
        else:
            channel = self.bot.get_channel(channel_id)
            if channel is None:
                try:
                    channel = await self.bot.fetch_channel(channel_id)
                except Exception as e:
                    return await ctx.send(f"❌ ما قدرت أجيب الروم: `{e}`")

        channel_name = getattr(channel, "name", "DM")

        msg = await ctx.send(f"📦 bulk delete من `{channel_name}` (آخر {limit})...")

        deleted = 0
        start_time = time.time()

        try:
            # Bulk delete (2-100 رسالة بالمرة)
            while deleted < limit:
                to_delete = min(100, limit - deleted)

                # اجمع رسائلك
                my_batch = []
                async for m in channel.history(limit=200):
                    if m.author.id == self.bot.user.id:
                        my_batch.append(m)
                    if len(my_batch) >= to_delete:
                        break

                if not my_batch:
                    break

                # bulk delete
                try:
                    await channel.delete_messages(my_batch)
                    deleted += len(my_batch)
                    print(f"📦 bulk: {len(my_batch)} — total: {deleted}")
                except discord.HTTPException:
                    # fallback: احذف واحد واحد
                    for m in my_batch:
                        try:
                            await m.delete()
                            deleted += 1
                            await asyncio.sleep(0.4)
                        except:
                            pass

                try:
                    await msg.edit(content=
                        f"📦 `{channel_name}`\n"
                        f"✅ حُذف: **{deleted}**"
                    )
                except:
                    pass

                await asyncio.sleep(1)

        except Exception as e:
            return await msg.edit(content=f"❌ خطأ: `{type(e).__name__}: {e}`")

        elapsed = time.time() - start_time

        await msg.edit(content=
            f"✅ **انتهى!**\n"
            f"📦 bulk delete\n"
            f"🗑️ حُذف: **{deleted}**\n"
            f"⏱️ `{elapsed:.1f}s`"
        )

    # ═════════════════════════════════════════
    # 🗑️ !purgeall — كل الرومات
    # ═════════════════════════════════════════
    @commands.command(name="purgeall")
    async def purgeall(self, ctx, limit_per_channel: int = 500):
        """
        !purgeall [limit]
        يحذف رسائلك من كل الرومات في السيرفر
        """
        try:
            await ctx.message.delete()
        except:
            pass

        msg = await ctx.send(f"🗑️ حذف من كل الرومات...")

        total_deleted = 0
        channels_done = 0
        channels_skipped = 0
        total_channels = len(ctx.guild.text_channels)
        start_time = time.time()

        for channel in ctx.guild.text_channels:

            # ─── تحقق من الصلاحيات ───
            try:
                perms = channel.permissions_for(ctx.guild.me)
                if not perms.read_message_history or not perms.manage_messages:
                    channels_skipped += 1
                    continue
            except:
                channels_skipped += 1
                continue

            # ─── اجمع رسائلك ───
            try:
                my_messages = []
                async for message in channel.history(limit=limit_per_channel):
                    if message.author.id == self.bot.user.id:
                        my_messages.append(message)

                # ─── احذف بالتوازي ───
                deleted_here = 0
                for i in range(0, len(my_messages), BATCH_DELETE):
                    batch = my_messages[i:i + BATCH_DELETE]
                    ok, _ = await self._delete_batch(batch)
                    deleted_here += ok
                    total_deleted += ok
                    await asyncio.sleep(BATCH_SLEEP)

                channels_done += 1

                try:
                    await msg.edit(content=
                        f"🗑️ التقدم: {channels_done}/{total_channels}\n"
                        f"✅ حُذف: **{total_deleted}**\n"
                        f"⏭️ تخطي: {channels_skipped}"
                    )
                except:
                    pass

            except:
                pass

            await asyncio.sleep(1)

        elapsed = time.time() - start_time

        await ctx.send(
            f"✅ **انتهى!**\n"
            f"📊 حُذف: **{total_deleted}** رسالة\n"
            f"📁 رومات: {channels_done}\n"
            f"⏭️ تخطي: {channels_skipped}\n"
            f"⏱️ `{elapsed:.1f}s`"
        )

    # ═════════════════════════════════════════
    # ⚠️ !purgeeveryone — حذف كل الرسائل
    # ═════════════════════════════════════════
    @commands.command(name="purgeeveryone")
    async def purgeeveryone(self, ctx, channel_id: int = None,
                            limit: int = 1000, confirm: str = ""):
        """
        !purgeeveryone <channel_id> <limit> yes
        يحذف كل الرسائل (مو بس رسائلك)
        ⚠️ خطر — ما فيه تراجع
        """
        if confirm.lower() != "yes":
            return await ctx.send(
                "⚠️ **تحذير:** هذا بيحذف **كل** الرسائل!\n"
                f"**للتأكيد:** `!purgeeveryone {channel_id or ''} {limit} yes`"
            )

        try:
            await ctx.message.delete()
        except:
            pass

        # ─── الروم ───
        if channel_id is None:
            channel = ctx.channel
        else:
            channel = self.bot.get_channel(channel_id)
            if channel is None:
                try:
                    channel = await self.bot.fetch_channel(channel_id)
                except Exception as e:
                    return await ctx.send(f"❌ ما قدرت أجيب الروم: `{e}`")

        channel_name = getattr(channel, "name", "DM")
        msg = await ctx.send(f"🗑️ حذف **كل** الرسائل من `{channel_name}`...")

        deleted = 0
        failed = 0
        start_time = time.time()
        history_limit = None if limit == 0 else limit

        # ─── اجمع كل الرسائل ───
        all_messages = []
        try:
            async for message in channel.history(limit=history_limit):
                all_messages.append(message)
        except:
            pass

        if not all_messages:
            return await msg.edit(content="❌ ما فيه رسائل")

        # ─── احذف بالتوازي ───
        for i in range(0, len(all_messages), BATCH_DELETE):
            batch = all_messages[i:i + BATCH_DELETE]
            ok, fail = await self._delete_batch(batch)
            deleted += ok
            failed += fail

            if (i // BATCH_DELETE) % 3 == 0:
                try:
                    await msg.edit(content=
                        f"🗑️ حُذف: **{deleted}**\n"
                        f"❌ فشل: `{failed}`\n"
                        f"📊 {deleted}/{len(all_messages)}"
                    )
                except:
                    pass

            await asyncio.sleep(BATCH_SLEEP)

        elapsed = time.time() - start_time

        await msg.edit(content=
            f"✅ انتهى!\n"
            f"🗑️ حُذف: **{deleted}**\n"
            f"❌ فشل: {failed}\n"
            f"⏱️ `{elapsed:.1f}s`"
        )

    # ═════════════════════════════════════════
    # 📋 !dms — قائمة DMs
    # ═════════════════════════════════════════
    @commands.command(name="dms")
    async def dms(self, ctx):
        """!dms → قائمة DMs + IDs"""
        try:
            await ctx.message.delete()
        except:
            pass

        lines = ["**📋 قائمة DMs:**\n"]
        count = 0

        for channel in self.bot.private_channels:
            if isinstance(channel, discord.DMChannel):
                user = channel.recipient
                lines.append(f"👤 **{user}**\n   🆔 `{channel.id}`\n")
                count += 1
            elif isinstance(channel, discord.GroupChannel):
                lines.append(f"👥 **Group: {channel.name}**\n   🆔 `{channel.id}`\n")
                count += 1

        if count == 0:
            return await ctx.send("❌ ما فيه DMs")

        text = "\n".join(lines)

        if len(text) > 1900:
            parts = [text[i:i+1900] for i in range(0, len(text), 1900)]
            for part in parts:
                await ctx.send(part)
                await asyncio.sleep(0.3)
        else:
            await ctx.send(text)

    # ═════════════════════════════════════════
    # 📁 !chinfo — معلومات الروم
    # ═════════════════════════════════════════
    @commands.command(name="chinfo")
    async def chinfo(self, ctx, channel_id: int = None):
        """!chinfo [channel_id] → معلومات الروم"""
        try:
            await ctx.message.delete()
        except:
            pass

        if channel_id is None:
            channel = ctx.channel
        else:
            channel = self.bot.get_channel(channel_id)
            if channel is None:
                try:
                    channel = await self.bot.fetch_channel(channel_id)
                except:
                    return await ctx.send(f"❌ ما لقيت الروم")

        # ─── عدد رسائلك ───
        my_msgs = 0
        try:
            async for m in channel.history(limit=500):
                if m.author.id == self.bot.user.id:
                    my_msgs += 1
        except:
            pass

        await ctx.send(
            f"**📁 معلومات الروم:**\n"
            f"📛 الاسم: `{getattr(channel, 'name', 'DM')}`\n"
            f"🆔 ID: `{channel.id}`\n"
            f"📝 رسائلك (آخر 500): `{my_msgs}`"
        )


async def setup(bot):
    await bot.add_cog(Purge(bot))