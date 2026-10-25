
import discord
from discord.ext import commands
import asyncio
import time
import json
import os


DATA_DIR = "cherry_data"
MESPAM_FILE = os.path.join(DATA_DIR, "mespam_config.json")


class Spam(commands.Cog):
    """💬 أوامر الإرسال المتكرر بحسابك"""

    def __init__(self, bot):
        self.bot = bot
        self.tasks = {}   # {channel_id: asyncio.Task}

        os.makedirs(DATA_DIR, exist_ok=True)
        self._load()


    def _load(self):
        if os.path.exists(MESPAM_FILE):
            try:
                with open(MESPAM_FILE, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
            except:
                self.config = {}
        else:
            self.config = {}

    def _save(self):
        try:
            with open(MESPAM_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
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

    @commands.command(name="mespam")
    async def mespam(self, ctx, interval: str, channel_id: int, *, message: str):
        """
        !mespam <وقت> <channel_id> <رسالة>
        إرسال متكرر بحسابك في روم محدد
        """
        
        delay = self._parse_time(interval)
        if delay is None:
            return await ctx.send(f"❌ صيغة وقت غلط: `{interval}`")

        if delay <= 0:
            return await ctx.send("❌ الوقت لازم أكبر من 0")

       
        message = message.strip()
        if not message:
            return await ctx.send("❌ الرسالة فاضية")

        if len(message) > 2000:
            return await ctx.send(f"❌ الرسالة طويلة ({len(message)} حرف). الحد 2000")

        
        channel = self.bot.get_channel(channel_id)
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(channel_id)
            except Exception as e:
                return await ctx.send(f"❌ ما قدرت أجيب الروم:\n```{e}```")

        
        if channel_id in self.tasks and not self.tasks[channel_id].done():
            self.tasks[channel_id].cancel()

        try:
            await ctx.message.delete()
        except:
            pass

      
        self.config[str(channel_id)] = {
            "interval": delay,
            "message": message,
            "enabled": True,
            "started": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        self._save()

        sent = 0
        failed = 0

        async def loop():
            nonlocal sent, failed
            while True:
                cycle_start = time.time()
                try:
                    await channel.send(message)
                    sent += 1
                    print(f"✅ [{sent}] أُرسل → {getattr(channel, 'name', 'DM')}")
                except discord.Forbidden:
                    print(f"❌ ما عندي صلاحية في {getattr(channel, 'name', 'DM')}")
                    return
                except discord.HTTPException as e:
                    failed += 1
                    if e.status == 429:
                        print(f"⚠️ Rate limit — انتظر 5 ثواني")
                        await asyncio.sleep(5)
                    else:
                        print(f"❌ خطأ: {e}")

                elapsed = time.time() - cycle_start
                wait = max(0, delay - elapsed)
                if wait > 0:
                    await asyncio.sleep(wait)

        self.tasks[channel_id] = asyncio.create_task(loop())

        await ctx.send(
            f"💬 **بدأ الإرسال بحسابك**\n"
            f"📌 الروم: `{getattr(channel, 'name', 'DM')}` (`{channel_id}`)\n"
            f"⏱️ كل: `{self._human_time(delay)}`\n"
            f"💬 الرسالة: `{message[:60]}{'...' if len(message) > 60 else ''}`\n"
            f"🛑 للإيقاف: `!mestop {channel_id}`"
        )

    @commands.command(name="mestop")
    async def mestop(self, ctx, channel_id: int = None):
        """
        !mestop → إيقاف كل الإرسالات
        !mestop <channel_id> → إيقاف إرسال معين
        """
        try:
            await ctx.message.delete()
        except:
            pass

        stopped = 0

        if channel_id is not None:
         
            if channel_id in self.tasks and not self.tasks[channel_id].done():
                self.tasks[channel_id].cancel()
                del self.tasks[channel_id]
                stopped = 1

                if str(channel_id) in self.config:
                    self.config[str(channel_id)]["enabled"] = False
                    self._save()
        else:
           
            for cid, task in list(self.tasks.items()):
                if not task.done():
                    task.cancel()
                    stopped += 1
                del self.tasks[cid]

            for cid in self.config:
                self.config[cid]["enabled"] = False
            self._save()

        await ctx.send(f"🛑 تم إيقاف `{stopped}` إرسال", delete_after=5)
    @commands.command(name="mestatus")
    async def mestatus(self, ctx):
        """!mestatus → حالة الإرسالات"""
        try:
            await ctx.message.delete()
        except:
            pass

        if not self.config:
            return await ctx.send("❌ ما فيه إرسالات محفوظة")

        lines = ["**💬 حالة الإرسالات:**\n"]
        running = 0

        for cid, cfg in self.config.items():
            is_running = cid in self.tasks and not self.tasks[cid].done()
            status = "🟢 شغال" if is_running else "🔴 متوقف"

            if is_running:
                running += 1

            channel = self.bot.get_channel(int(cid))
            ch_name = getattr(channel, "name", "DM") if channel else "❓"

            lines.append(
                f"{status} **{ch_name}** (`{cid}`)\n"
                f"   ⏱️ كل: `{self._human_time(cfg['interval'])}`\n"
                f"   💬 `{cfg['message'][:40]}`"
            )

        lines.append(f"\n**📌 الشغالين:** `{running}` / `{len(self.config)}`")

        text = "\n".join(lines)

        if len(text) > 1900:
            parts = [text[i:i+1900] for i in range(0, len(text), 1900)]
            for part in parts:
                await ctx.send(part)
                await asyncio.sleep(0.3)
        else:
            await ctx.send(text)


    @commands.command(name="medel")
    async def medel(self, ctx, channel_id: int = None, confirm: str = ""):
        """
        !medel <channel_id> yes → حذف إعداد
        !medel all yes → حذف الكل
        """
        if confirm.lower() != "yes":
            return await ctx.send(f"⚠️ للتأكيد: `!medel {channel_id or 'all'} yes`")

        try:
            await ctx.message.delete()
        except:
            pass

        if channel_id is None:
         
            for cid, task in list(self.tasks.items()):
                if not task.done():
                    task.cancel()
            self.tasks.clear()
            self.config.clear()
            self._save()
            return await ctx.send("✅ تم حذف كل الإعدادات")

        cid = str(channel_id)

        if cid in self.tasks and not self.tasks[cid].done():
            self.tasks[cid].cancel()
            del self.tasks[cid]

        if cid in self.config:
            del self.config[cid]
            self._save()

        await ctx.send(f"✅ تم حذف إعداد `{channel_id}`")

    @commands.command(name="mechange")
    async def mechange(self, ctx, channel_id: int, new_interval: str):
        """
        !mechange <channel_id> <وقت جديد>
        يغير وقت الإرسال
        """
        delay = self._parse_time(new_interval)
        if delay is None:
            return await ctx.send(f"❌ صيغة وقت غلط: `{new_interval}`")

        cid = str(channel_id)

        if cid not in self.config:
            return await ctx.send(f"❌ `{channel_id}` مو موجود")

        try:
            await ctx.message.delete()
        except:
            pass

        
        if channel_id in self.tasks and not self.tasks[channel_id].done():
            self.tasks[channel_id].cancel()

        
        self.config[cid]["interval"] = delay
        self._save()

        
        await self.mespam.callback(
            ctx,
            new_interval,
            channel_id,
            message=self.config[cid]["message"]
        )


async def setup(bot):
    await bot.add_cog(Spam(bot))