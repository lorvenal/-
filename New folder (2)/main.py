
import discord
from discord.ext import commands
import os
import sys
import asyncio


from config import TOKEN, PREFIX

os.makedirs("cherry_data", exist_ok=True)
os.makedirs("cogs", exist_ok=True)


client = commands.Bot(
    command_prefix=PREFIX,
    self_bot=True,
    help_command=None,   
)


@client.event
async def on_ready():
    print()
    print("═" * 55)
    print(f"  ✅ تم تسجيل الدخول: {client.user}")
    print(f"  👤 ID: {client.user.id}")
    print(f"  📁 الأوامر: {len(client.cogs)}")
    print("═" * 55)
    print("  💡 اكتب !cmds لعرض كل الأوامر")
    print("  💡 اكتب !help لعرض الأقسام")
    print("═" * 55)
    print()



async def load_cogs():
    cog_files = [
        "cogs.status",
        "cogs.purge",
        "cogs.block",
        "cogs.rooms",
        "cogs.spam",
        "cogs.webhooks",
        "cogs.logger",
        "cogs.autoreply",
        "cogs.ai",
        "cogs.help",
    ]

    print("─" * 55)
    print("  📂 تحميل الأوامر...")
    print("─" * 55)

    success = 0
    failed = 0

    for cog in cog_files:
        try:
            await client.load_extension(cog)
            print(f"  ✅ {cog}")
            success += 1
        except Exception as e:
            print(f"  ❌ {cog}: {e}")
            failed += 1

    print("─" * 55)
    print(f"  📊 نجح: {success} | فشل: {failed}")
    print("─" * 55)
    print()



@client.event
async def on_command_error(ctx, error):
   
    if isinstance(error, commands.CommandNotFound):
        return

    if isinstance(error, commands.MissingRequiredArgument):
        try:
            await ctx.send(f"❌ ناقص معامل: `{error.param.name}`")
        except:
            pass
        return

    if isinstance(error, commands.BadArgument):
        try:
            await ctx.send(f"❌ معامل غلط: `{error}`")
        except:
            pass
        return

    # Rate limit
    if isinstance(error, commands.CommandOnCooldown):
        try:
            await ctx.send(f"⏳ انتظر `{error.retry_after:.1f}s`")
        except:
            pass
        return


    print(f"\n⚠️ خطأ في الأمر {ctx.command}:")
    print(f"   {type(error).__name__}: {error}\n")



async def main():
    async with client:
        await load_cogs()
        await client.start(TOKEN)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n🛑 تم إيقاف البوت")
    except Exception as e:
        print(f"\n❌ خطأ: {type(e).__name__}: {e}\n")
        input("اضغط Enter للخروج...")