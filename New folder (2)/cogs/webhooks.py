# cogs/webhooks.py
import discord
from discord.ext import commands
import json
import os
import asyncio
import time


DATA_DIR = "cherry_data"
WEBHOOKS_FILE = os.path.join(DATA_DIR, "webhooks.json")


class Webhooks(commands.Cog):
    """🪝 إدارة الويبوكات والرومات"""

    def __init__(self, bot):
        self.bot = bot
        self.webhooks = {}     
        self.fire_task = None  
        self.fire_channel = None

        os.makedirs(DATA_DIR, exist_ok=True)
        self._load()


    def _load(self):
        if os.path.exists(WEBHOOKS_FILE):
            try:
                with open(WEBHOOKS_FILE, 'r', encoding='utf-8') as f:
                    self.webhooks = json.load(f)
            except:
                self.webhooks = {}

    def _save(self):
        try:
            with open(WEBHOOKS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.webhooks, f, indent=2, ensure_ascii=False)
        except:
            pass

    def _parse_time(self, value):
        value = value.strip().lower()
        try:
            return float(value)
        except:
            pass

        units = {
            's': 1, 'sec': 1, 'second': 1, 'ث': 1, 'ثانية': 1, 'ثواني': 1,
            'm': 60, 'min': 60, 'minute': 60, 'د': 60, 'دقيقة': 60, 'دقائق': 60,
            'h': 3600, 'hr': 3600, 'hour': 3600, 'س': 3600, 'ساعة': 3600, 'ساعات': 3600,
        }

        for unit, mult in units.items():
            if value.endswith(unit):
                try:
                    num = float(value[:-len(unit)].strip())
                    return num * mult
                except:
                    continue
        return None

    def _human_time(self, sec):
        if sec < 60:
            return f"{sec:.1f} ثانية"
        elif sec < 3600:
            return f"{sec/60:.1f} دقيقة"
        else:
            return f"{sec/3600:.2f} ساعة"

    async def _send_webhook(self, url, name, message):
        """ترسل رسالة عبر ويبوك"""
        webhook = discord.Webhook.from_url(url, client=self.bot)
        return await webhook.send(content=message, username=name, wait=True)
    @commands.command(name="hooks")
    async def hooks(self, ctx, count: int = 10, name: str = "webhook"):
        """
        !hooks <عدد> [اسم]
        ينشئ ويبوكات في روم temp-hooks ويحفظهم
        """
        if count < 1 or count > 200:
            return await ctx.send("⚠️ العدد بين 1 و 200")

        try:
            await ctx.message.delete()
        except:
            pass

        guild = ctx.guild
        msg = await ctx.send(f"⚡ إنشاء {count} ويبوك...")

        
        temp = await guild.create_text_channel(name="temp-hooks")

        created = 0
        failed = 0
        batch_size = 3
        start = time.time()

        for batch_start in range(0, count, batch_size):
            batch_end = min(batch_start + batch_size, count)
            tasks = []

            for i in range(batch_start + 1, batch_end + 1):
                tasks.append(temp.create_webhook(name=f"{name}-{i}"))

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for idx, result in enumerate(results):
                i = batch_start + idx + 1
                if isinstance(result, Exception):
                    failed += 1
                    print(f"❌ [{i}/{count}] {result}")
                else:
                    self.webhooks[str(result.id)] = {
                        "url": result.url,
                        "name": result.name,
                        "token": result.token,
                        "id": str(result.id),
                        "guild_id": str(guild.id),
                        "temp_channel": str(temp.id),
                        "channel_id": None,
                        "channel_name": None,
                        "linked": False,
                        "created": time.strftime("%Y-%m-%d %H:%M:%S"),
                    }
                    created += 1
                    print(f"✅ [{i}/{count}] {result.name}")

            try:
                await msg.edit(content=f"⚡ إنشاء... [{batch_end}/{count}]")
            except:
                pass

            await asyncio.sleep(0.5)

        self._save()

        try:
            await temp.delete()
        except:
            pass

        elapsed = time.time() - start

        await ctx.send(
            f"✅ **تم**\n"
            f"📊 نجح: `{created}` | فشل: `{failed}`\n"
            f"⏱️ `{elapsed:.1f}s`\n"
            f"🏦 المجموع: `{len(self.webhooks)}`\n"
            f"💡 التالي: `!rooms {created} room`"
        )


    @commands.command(name="rooms")
    async def rooms(self, ctx, count: int = 10, name: str = "room", *, message: str = None):
        """
        !rooms <عدد> [اسم] [رسالة]
        ينشئ رومات + يربط الويبوكات + يرسل أول رسالة
        """
        unlinked = {wid: wh for wid, wh in self.webhooks.items() if not wh.get("linked")}

        if not unlinked:
            return await ctx.send("❌ ما فيه ويبوكات غير مربوطة. استخدم `!hooks` أول")

        if count > len(unlinked):
            await ctx.send(f"⚠️ عندك `{len(unlinked)}` ويبوك غير مربوط")
            count = len(unlinked)

        if not message:
            message = "السلام عليكم"

        try:
            await ctx.message.delete()
        except:
            pass

        guild = ctx.guild
        msg = await ctx.send(f"⚡ إنشاء {count} روم + ربط...")

        batch_size = 3
        unlinked_list = list(unlinked.items())
        created_channels = []
        failed = 0

    
        for batch_start in range(0, count, batch_size):
            batch_end = min(batch_start + batch_size, count)
            tasks = []

            for i in range(batch_start + 1, batch_end + 1):
                tasks.append(guild.create_text_channel(name=f"{name}-{i}"))

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for idx, result in enumerate(results):
                i = batch_start + idx + 1
                if isinstance(result, Exception):
                    failed += 1
                    print(f"❌ روم [{i}]: {result}")
                else:
                    wid, wh = unlinked_list[i - 1]
                    created_channels.append((result, wid, wh))
                    print(f"✅ روم [{i}] {result.name}")

            try:
                await msg.edit(content=f"⚡ رومات... [{batch_end}/{count}]")
            except:
                pass

            await asyncio.sleep(0.5)

     
        try:
            await msg.edit(content="⚡ ربط الويبوكات...")
        except:
            pass

        linked_data = []

        for batch_start in range(0, len(created_channels), batch_size):
            batch_end = min(batch_start + batch_size, len(created_channels))
            tasks = []

            for j in range(batch_start, batch_end):
                channel, wid, wh = created_channels[j]
                tasks.append(channel.create_webhook(name=wh["name"]))

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for idx, result in enumerate(results):
                j = batch_start + idx
                channel, wid, wh = created_channels[j]

                if isinstance(result, Exception):
                    print(f"❌ ربط [{channel.name}]: {result}")
                else:
                    linked_data.append((channel, result, wid, wh))

              
                    old_ch_id = wh.get("temp_channel")
                    if old_ch_id:
                        old_ch = guild.get_channel(int(old_ch_id))
                        if old_ch:
                            try:
                                hooks_list = await old_ch.webhooks()
                                for h in hooks_list:
                                    if str(h.id) == wid:
                                        await h.delete()
                                        break
                            except:
                                pass

                    
                    self.webhooks[wid] = {
                        "url": result.url,
                        "name": result.name,
                        "token": result.token,
                        "id": str(result.id),
                        "guild_id": str(guild.id),
                        "channel_id": str(channel.id),
                        "channel_name": channel.name,
                        "linked": True,
                        "created": wh.get("created", time.strftime("%Y-%m-%d %H:%M:%S")),
                    }

            await asyncio.sleep(0.5)

        self._save()
        try:
            await msg.edit(content="⚡ إرسال أول رسالة...")
        except:
            pass

        sent = 0

        for batch_start in range(0, len(linked_data), batch_size):
            batch_end = min(batch_start + batch_size, len(linked_data))
            tasks = []

            for j in range(batch_start, batch_end):
                channel, new_wh, wid, wh = linked_data[j]
                tasks.append(self._send_webhook(new_wh.url, new_wh.name, message))

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for idx, result in enumerate(results):
                j = batch_start + idx
                channel, new_wh, wid, wh = linked_data[j]

                if isinstance(result, Exception):
                    print(f"❌ إرسال [{channel.name}]: {result}")
                else:
                    sent += 1
                    print(f"✅ إرسال [{channel.name}]")

            await asyncio.sleep(0.5)

        await ctx.send(
            f"✅ **تم**\n"
            f"📊 رومات: `{len(created_channels)}` | مربوط: `{len(linked_data)}`\n"
            f"📨 رسائل: `{sent}`\n"
            f"💡 التالي: `!fire 30s مرحبا`"
        )
    @commands.command(name="fire")
    async def fire(self, ctx, interval: str, *, message: str):
        """
        !fire <وقت> <رسالة>
        إرسال متكرر عبر الويبوكات المربوطة
        """
        linked = {wid: wh for wid, wh in self.webhooks.items() if wh.get("linked")}

        if not linked:
            return await ctx.send("❌ ما فيه ويبوكات مربوطة. استخدم `!hooks` و `!rooms` أول")

        delay = self._parse_time(interval)
        if delay is None:
            return await ctx.send(f"❌ صيغة وقت غلط: `{interval}`")

        if delay <= 0:
            return await ctx.send("❌ الوقت لازم أكبر من 0")

        message = message.strip()
        if not message:
            return await ctx.send("❌ الرسالة فاضية")

        try:
            await ctx.message.delete()
        except:
            pass

        # ─── أوقف أي fire قديم ───
        if self.fire_task and not self.fire_task.done():
            self.fire_task.cancel()

        self.fire_channel = ctx.channel

        async def fire_loop():
            cycle = 0
            while True:
                cycle += 1
                cycle_start = time.time()
                total = len(linked)
                success = 0
                failed = 0

                print(f"\n🔥 دورة #{cycle} - {total} ويبوك")

                batch_size = 3
                items = list(linked.items())

                for i in range(0, total, batch_size):
                    batch = items[i:i+batch_size]
                    tasks = []

                    for wid, wh in batch:
                        tasks.append(self._send_webhook(wh["url"], wh["name"], message))

                    results = await asyncio.gather(*tasks, return_exceptions=True)

                    for r in results:
                        if isinstance(r, Exception):
                            failed += 1
                            print(f"❌ {r}")
                        else:
                            success += 1

                    await asyncio.sleep(0.5)

                cycle_time = time.time() - cycle_start
                print(f"🏁 دورة #{cycle}: {success}/{total} بـ {cycle_time:.1f}s")

                wait = max(0, delay - cycle_time)
                if wait > 0:
                    await asyncio.sleep(wait)

        self.fire_task = asyncio.create_task(fire_loop())

        await ctx.send(
            f"🔥 **بدأ الإرسال**\n"
            f"📌 الويبوكات: `{len(linked)}`\n"
            f"⏱️ كل: `{self._human_time(delay)}`\n"
            f"💬 الرسالة: `{message[:60]}{'...' if len(message) > 60 else ''}`\n"
            f"🛑 للإيقاف: `!stop`"
        )

    @commands.command(name="stop")
    async def stop(self, ctx):
        """!stop → إيقاف fire"""
        try:
            await ctx.message.delete()
        except:
            pass

        if self.fire_task and not self.fire_task.done():
            self.fire_task.cancel()
            self.fire_task = None

        await ctx.send("🛑 تم الإيقاف", delete_after=5)
    @commands.command(name="send")
    async def send(self, ctx, *, message: str):
        """!send <رسالة> → إرسال مرة وحدة عبر الكل"""
        try:
            await ctx.message.delete()
        except:
            pass

        linked = {wid: wh for wid, wh in self.webhooks.items() if wh.get("linked")}

        if not linked:
            return await ctx.send("❌ ما فيه ويبوكات مربوطة")

        if not message.strip():
            return await ctx.send("❌ الرسالة فاضية")

        msg = await ctx.send(f"📤 جاري الإرسال...")

        sent = 0
        failed = 0

        for wid, wh in linked.items():
            try:
                await self._send_webhook(wh["url"], wh["name"], message)
                sent += 1

                if sent % 5 == 0:
                    try:
                        await msg.edit(content=f"📤 أُرسل: {sent}")
                    except:
                        pass
                await asyncio.sleep(0.3)
            except Exception as e:
                failed += 1
                print(f"❌ {wh['name']}: {e}")

        await ctx.send(f"✅ تم\n📤 أُرسل: `{sent}`\n❌ فشل: `{failed}`")
    @commands.command(name="whlist")
    async def whlist(self, ctx, limit: int = 30):
        """!whlist [عدد] → عرض الويبوكات"""
        try:
            await ctx.message.delete()
        except:
            pass

        if not self.webhooks:
            return await ctx.send("❌ ما فيه ويبوكات")

        all_wh = list(self.webhooks.values())
        linked = sum(1 for w in all_wh if w.get("linked"))
        total = len(all_wh)

        lines = [f"**🪝 الويبوكات ({total} - مربوط: {linked}):**\n"]

        for i, wh in enumerate(all_wh[:limit], 1):
            status = "🔗" if wh.get("linked") else "🆓"
            ch = wh.get("channel_name") or "—"
            lines.append(f"`{i}.` {status} **{wh['name']}** → `{ch}`")

        if total > limit:
            lines.append(f"\n... و `{total - limit}` غيرهم")

        text = "\n".join(lines)

        if len(text) > 1900:
            parts = [text[i:i+1900] for i in range(0, len(text), 1900)]
            for part in parts:
                await ctx.send(part)
                await asyncio.sleep(0.3)
        else:
            await ctx.send(text)
    @commands.command(name="whstatus")
    async def whstatus(self, ctx):
        """!whstatus → حالة الويبوكات"""
        try:
            await ctx.message.delete()
        except:
            pass

        total = len(self.webhooks)
        linked = sum(1 for w in self.webhooks.values() if w.get("linked"))
        fire = "🟢 شغال" if (self.fire_task and not self.fire_task.done()) else "🔴 متوقف"

        await ctx.send(
            f"**📊 حالة الويبوكات:**\n"
            f"🔥 fire: {fire}\n"
            f"🪝 الكل: `{total}`\n"
            f"🔗 مربوط: `{linked}`\n"
            f"🆓 غير مربوط: `{total - linked}`"
        )
    @commands.command(name="whtest")
    async def whtest(self, ctx, *, message: str = "تجربة"):
        """!whtest [رسالة] → اختبار ويبوك واحد"""
        try:
            await ctx.message.delete()
        except:
            pass

        linked = {wid: wh for wid, wh in self.webhooks.items() if wh.get("linked")}
        if not linked:
            return await ctx.send("❌ ما فيه ويبوكات مربوطة")

        wid, wh = list(linked.items())[0]

        try:
            result = await self._send_webhook(wh["url"], wh["name"], message)
            await ctx.send(f"✅ نجح!\n🪝 `{wh['name']}`\n📨 `{result.id}`")
        except Exception as e:
            await ctx.send(f"❌ فشل:\n```{type(e).__name__}: {e}```")
    @commands.command(name="whdel")
    async def whdel(self, ctx, webhook_id: str = None, confirm: str = ""):
        """
        !whdel <id> yes → حذف ويبوك
        !whdel all yes → حذف الكل
        """
        if confirm.lower() != "yes":
            if webhook_id is None:
                return await ctx.send("⚠️ `!whdel <id> yes` أو `!whdel all yes`")
            return await ctx.send(f"⚠️ للتأكيد: `!whdel {webhook_id} yes`")

        try:
            await ctx.message.delete()
        except:
            pass

        if webhook_id.lower() == "all":
            count = 0
            for wid, wh in list(self.webhooks.items()):
                try:
                    webhook = discord.Webhook.from_url(wh["url"], client=self.bot)
                    await webhook.delete()
                    count += 1
                except:
                    pass
                await asyncio.sleep(0.5)

            self.webhooks.clear()
            self._save()
            return await ctx.send(f"✅ تم حذف `{count}` ويبوك")

        if webhook_id not in self.webhooks:
            return await ctx.send(f"❌ مو موجود: `{webhook_id}`")

        wh = self.webhooks[webhook_id]
        try:
            webhook = discord.Webhook.from_url(wh["url"], client=self.bot)
            await webhook.delete()
        except:
            pass

        del self.webhooks[webhook_id]
        self._save()

        await ctx.send(f"✅ تم حذف الويبوك: `{wh['name']}`")
    @commands.command(name="whclear")
    async def whclear(self, ctx, confirm: str = ""):
        """!whclear yes → مسح القائمة فقط"""
        if confirm.lower() != "yes":
            return await ctx.send("⚠️ اكتب `!whclear yes` للتأكيد")

        try:
            await ctx.message.delete()
        except:
            pass

        self.webhooks.clear()
        self._save()

        await ctx.send("✅ تم مسح القائمة", delete_after=5)


async def setup(bot):
    await bot.add_cog(Webhooks(bot))