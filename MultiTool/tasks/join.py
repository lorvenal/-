# ═════════════════════════════════════════
# 🚪 tasks/join.py — دخول سيرفر
# ═════════════════════════════════════════

import aiohttp
import asyncio

from utils.parser import parse_invite


API_BASE = "https://discord.com/api/v10"
TIMEOUT = 30


async def execute_join(session, token, invite, user_agent=None):
    """
    يدخل سيرفر عبر invite

    Args:
        session: aiohttp ClientSession
        token: توكن الحساب
        invite: رابط أو كود الـ invite
        user_agent: User-Agent (اختياري)

    Returns:
        dict: {ok: bool, guild: str, error: str}
    """

    # ─── تحليل invite ───
    code = parse_invite(invite)
    if not code:
        return {"ok": False, "error": "invite غلط"}

    # ─── Headers ───
    headers = {
        "Authorization": token,
        "Content-Type": "application/json",
    }

    if user_agent:
        headers["User-Agent"] = user_agent

    # ─── API Call ───
    url = f"{API_BASE}/invites/{code}"

    try:
        async with session.post(
            url,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=TIMEOUT)
        ) as resp:

            # ─── نجاح ───
            if resp.status == 200:
                data = await resp.json()
                guild = data.get("guild", {})
                guild_name = guild.get("name", "?")
                guild_id = guild.get("id", "?")
                return {
                    "ok": True,
                    "guild": guild_name,
                    "guild_id": guild_id,
                }

            # ─── 401: توكن غلط ───
            elif resp.status == 401:
                return {"ok": False, "error": "توكن غلط"}

            # ─── 403: محظور ───
            elif resp.status == 403:
                try:
                    err = await resp.json()
                    msg = err.get("message", "محظور")
                except:
                    msg = "محظور"
                return {"ok": False, "error": f"محظور: {msg}"}

            # ─── 404: invite غلط ───
            elif resp.status == 404:
                return {"ok": False, "error": "invite غلط أو منتهي"}

            # ─── 429: rate limit ───
            elif resp.status == 429:
                retry = resp.headers.get("retry-after", "5")
                try:
                    wait_time = float(retry)
                except:
                    wait_time = 5
                return {
                    "ok": False,
                    "error": f"Rate limit ({wait_time}s)",
                    "retry_after": wait_time,
                }

            # ─── أخرى ───
            else:
                try:
                    err = await resp.text()
                    err = err[:150]
                except:
                    err = "?"
                return {"ok": False, "error": f"HTTP {resp.status}: {err}"}

    except asyncio.TimeoutError:
        return {"ok": False, "error": "Timeout"}

    except aiohttp.ClientError as e:
        return {"ok": False, "error": f"اتصال: {type(e).__name__}"}

    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


# ─── للاختبار ───
if __name__ == "__main__":
    import asyncio

    async def test():
        async with aiohttp.ClientSession() as session:
            result = await execute_join(
                session,
                "YOUR_TOKEN_HERE",
                "https://discord.gg/xxx"
            )
            print(result)

    asyncio.run(test())