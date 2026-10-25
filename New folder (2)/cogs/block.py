
import discord
from discord.ext import commands
import asyncio


class Block(commands.Cog):
    """🚫 أوامر الحظر (Block)"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="blockall")
    async def blockall(self, ctx, guild_id: int = None, confirm: str = ""):
        """!blockall [guild_id] yes → حظر كل أعضاء سيرفر"""
        if confirm.lower() != "yes":
            target = self.bot.get_guild(guild_id) if guild_id else ctx.guild
            if not target:
                return await ctx.send("❌ ما قدرت أجيب السيرفر")
            return await ctx.send(
                f"⚠️ **تحذير:**\n"
                f"📁 `{target.name}`\n"
                f"👥 الأعضاء: **{target.member_count}**\n"
                f"🆔 `{target.id}`\n\n"
                f"**للتأكيد:** `!blockall {target.id} yes`"
            )

        try:
            await ctx.message.delete()
        except:
            pass

        target = self.bot.get_guild(guild_id) if guild_id else ctx.guild
        if not target:
            return await ctx.send("❌ ما قدرت أجيب السيرفر")

        msg = await ctx.send(f"🚫 جاري الحظر...\n📁 `{target.name}`")

        blocked = 0
        failed = 0
        skipped = 0

        
        try:
            members = [m async for m in target.fetch_members(limit=None)]
        except Exception as e:
            print(f"⚠️ fetch_members فشل: {e}")
            members = list(target.members)

        total = len(members)

        if total == 0:
            return await msg.edit(content="❌ ما فيه أعضاء أقدر أوصلهم")

       
        for idx, member in enumerate(members, 1):
            if member.id == self.bot.user.id:
                skipped += 1
                continue

            if member.bot:
                skipped += 1
                continue

            try:
                await member.block()
                blocked += 1
                print(f"🚫 [{idx}/{total}] {member}")
            except discord.Forbidden:
                failed += 1
                print(f"❌ [{idx}/{total}] {member} - Forbidden")
            except discord.HTTPException as e:
                failed += 1
                if e.status == 429:
                    print(f"⚠️ Rate limit — انتظر 10 ثواني")
                    await asyncio.sleep(10)
                    try:
                        await member.block()
                        blocked += 1
                    except:
                        pass

        
            if idx % 10 == 0:
                try:
                    await msg.edit(content=
                        f"🚫 جاري الحظر...\n"
                        f"✅ حُظر: **{blocked}**\n"
                        f"❌ فشل: `{failed}`\n"
                        f"⏭️ تخطي: `{skipped}`\n"
                        f"📊 التقدم: {idx}/{total}"
                    )
                except:
                    pass

           
            if idx % 5 == 0:
                await asyncio.sleep(1)

        await ctx.send(
            f"✅ **انتهى**\n"
            f"📁 `{target.name}`\n"
            f"✅ حُظر: **{blocked}**\n"
            f"❌ فشل: `{failed}`\n"
            f"⏭️ تخطي: `{skipped}`\n"
            f"📊 الإجمالي: `{total}`"
        )

    @commands.command(name="blockuser")
    async def blockuser(self, ctx, user_id: int = None):
        """!blockuser <user_id> → حظر عضو"""
        try:
            await ctx.message.delete()
        except:
            pass

        if user_id is None:
            return await ctx.send("❌ اكتب: `!blockuser <user_id>`")

        try:
            user = await self.bot.fetch_user(user_id)
            await user.block()
            await ctx.send(f"🚫 تم حظر: `{user}`")
        except discord.NotFound:
            await ctx.send(f"❌ المستخدم `{user_id}` مو موجود")
        except discord.Forbidden:
            await ctx.send(f"❌ ما قدرت أحظره")
        except Exception as e:
            await ctx.send(f"❌ فشل:\n```{type(e).__name__}: {e}```")

    @commands.command(name="blockids")
    async def blockids(self, ctx, *, ids: str):
        """
        !blockids 123 456 789
        يحظر قائمة IDs
        """
        try:
            await ctx.message.delete()
        except:
            pass

        id_list = [x.strip() for x in ids.replace(",", " ").split() if x.strip().isdigit()]

        if not id_list:
            return await ctx.send("❌ ما فيه IDs صحيحة")

        msg = await ctx.send(f"🚫 جاري حظر {len(id_list)}...")

        blocked = 0
        failed = 0

        for i, uid in enumerate(id_list, 1):
            try:
                user = await self.bot.fetch_user(int(uid))
                await user.block()
                blocked += 1
                print(f"🚫 [{i}/{len(id_list)}] {user}")
            except:
                failed += 1
                print(f"❌ [{i}/{len(id_list)}] {uid}")

            if i % 5 == 0:
                try:
                    await msg.edit(content=f"🚫 حُظر: {blocked} | ❌ {failed} | {i}/{len(id_list)}")
                except:
                    pass
                await asyncio.sleep(1)

        await ctx.send(f"✅ انتهى\n✅ حُظر: `{blocked}`\n❌ فشل: `{failed}`")

    @commands.command(name="unblockuser")
    async def unblockuser(self, ctx, user_id: int = None):
        """!unblockuser <user_id> → فك حظر عضو"""
        try:
            await ctx.message.delete()
        except:
            pass

        if user_id is None:
            return await ctx.send("❌ اكتب: `!unblockuser <user_id>`")

        try:
            user = await self.bot.fetch_user(user_id)
            await user.unblock()
            await ctx.send(f"🔓 تم فك حظر: `{user}`")
        except Exception as e:
            await ctx.send(f"❌ فشل: `{e}`")


    @commands.command(name="unblockall")
    async def unblockall(self, ctx, confirm: str = ""):
        """!unblockall yes → فك حظر الكل"""
        if confirm.lower() != "yes":
            return await ctx.send("⚠️ اكتب `!unblockall yes` للتأكيد")

        try:
            await ctx.message.delete()
        except:
            pass

        msg = await ctx.send("🔓 جاري فك الحظر...")

        unblocked = 0
        failed = 0

     
        try:
            rels = [r async for r in self.bot.fetch_relationships()]
            blocked_users = [r for r in rels if r.type == discord.RelationshipType.blocked]
        except Exception as e:
            return await msg.edit(content=f"❌ فشل: `{e}`")

        total = len(blocked_users)

        if total == 0:
            return await msg.edit(content="✅ ما فيه محظورين")

        for idx, rel in enumerate(blocked_users, 1):
            try:
                await rel.user.unblock()
                unblocked += 1
                print(f"🔓 [{idx}/{total}] {rel.user}")
            except:
                failed += 1

            if idx % 10 == 0:
                try:
                    await msg.edit(content=f"🔓 فُك: {unblocked} | ❌ {failed} | {idx}/{total}")
                except:
                    pass

            if idx % 5 == 0:
                await asyncio.sleep(1)

        await ctx.send(f"✅ انتهى\n🔓 فُك: `{unblocked}`\n❌ فشل: `{failed}`")
    @commands.command(name="blocklist")
    async def blocklist(self, ctx, limit: int = 50):
        """!blocklist [عدد] → عرض المحظورين"""
        try:
            await ctx.message.delete()
        except:
            pass

        try:
            rels = [r async for r in self.bot.fetch_relationships()]
            blocked = [r for r in rels if r.type == discord.RelationshipType.blocked]
        except Exception as e:
            return await ctx.send(f"❌ فشل: `{e}`")

        if not blocked:
            return await ctx.send("✅ ما فيه محظورين")

        total = len(blocked)
        show = min(limit, total)

        lines = [f"**🚫 المحظورين ({total} - بيعرض {show}):**\n"]

        for i, rel in enumerate(blocked[:show], 1):
            user = rel.user
            lines.append(f"`{i}.` **{user}** (`{user.id}`)")

        text = "\n".join(lines)

        if len(text) > 1900:
            parts = [text[i:i+1900] for i in range(0, len(text), 1900)]
            for part in parts:
                await ctx.send(part)
                await asyncio.sleep(0.3)
        else:
            await ctx.send(text)
    @commands.command(name="blockcheck")
    async def blockcheck(self, ctx, user_id: int = None):
        """!blockcheck <user_id> → هل محظور؟"""
        try:
            await ctx.message.delete()
        except:
            pass

        if user_id is None:
            return await ctx.send("❌ اكتب: `!blockcheck <user_id>`")

        try:
            rels = [r async for r in self.bot.fetch_relationships()]
            blocked = [r for r in rels if r.type == discord.RelationshipType.blocked]

            for rel in blocked:
                if rel.user.id == user_id:
                    return await ctx.send(f"🚫 **محظور** — `{rel.user}`")

            return await ctx.send(f"✅ **مو محظور** — `{user_id}`")
        except Exception as e:
            await ctx.send(f"❌ فشل: `{e}`")
    @commands.command(name="blockstats")
    async def blockstats(self, ctx):
        """!blockstats → إحصائيات الحظر"""
        try:
            await ctx.message.delete()
        except:
            pass

        try:
            rels = [r async for r in self.bot.fetch_relationships()]
        except Exception as e:
            return await ctx.send(f"❌ فشل: `{e}`")

        # عد الأنواع
        counts = {}
        for r in rels:
            t = str(r.type).split(".")[-1]
            counts[t] = counts.get(t, 0) + 1

        lines = [f"**📊 إحصائيات العلاقات:**\n"]
        for t, c in counts.items():
            emoji = {
                "blocked": "🚫",
                "friend": "👥",
                "incoming_request": "📥",
                "outgoing_request": "📤",
            }.get(t, "❓")
            lines.append(f"{emoji} **{t}**: `{c}`")

        lines.append(f"\n**📌 الإجمالي:** `{len(rels)}`")

        await ctx.send("\n".join(lines))


async def setup(bot):
    await bot.add_cog(Block(bot))