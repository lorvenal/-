# ═════════════════════════════════════════
# 😀 tasks/react.py — رد فعل على رسالة
# ═════════════════════════════════════════

import aiohttp
import asyncio
import urllib.parse

from utils.parser import parse_message_url, parse_emoji


API_BASE = "https://discord.com/api/v10"
TIMEOUT = 30


async def execute_react(session, token, message_url, emoji, user_agent=None):
    """
    يضيف رد فعل على رسالة

    Args:
        session: aiohttp ClientSession
        token: توكن الحساب
        message_url: رابط الرسالة الكامل
        emoji: الإيموجي (عادي أو مخصص)
        user_agent: User-Agent (اختياري)

    Returns:
        dict: {ok: bool, error: str}
    """

    # ─── تحليل الرابط ───
    url_data = parse_message_url(message_url)
    if not url_data:
        return {"ok": False, "error": "رابط رسالة غلط"}

    channel_id = url_data["channel_id"]
    message_id = url_data["message_id"]

    # ─── تحليل الإيموجي ───
    emoji_data = parse_emoji(emoji)
    emoji_encoded = urllib.parse.quote(
        emoji_data.get("encoded", "👍")
    )

    # ─── Headers ───
    headers = {
        "Authorization": token,
        "Content-Type": "application/json",
    }

    if user_agent:
        headers["User-Agent"] = user_agent

    # ─── API Call ───
    url = (
        f"{API_BASE}/channels/{channel_id}"
        f"/messages/{message_id}"
        f"/reactions/{emoji_encoded}/@me"
    )

    try:
        async with session.put(
            url,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=TIMEOUT)
        ) as resp:

            # ─── نجاح (200 أو 204) ───
            if resp.status in (200, 204):
                return {
                    "ok": True,
                    "emoji": emoji_data.get("value", emoji_data.get("name", "?")),
                }

            # ─── 401: توكن غلط ───
            elif resp.status == 401:
                return {"ok": False, "error": "توكن غلط"}

            # ─── 403: ما عنده صلاحية ───
            elif resp.status == 403:
                try:
                    err = await resp.json()
                    msg = err.get("message", "ما عنده صلاحية")
                except:
                    msg = "ما عنده صلاحية"
                return {"ok": False, "error": msg}

            # ─── 404: رسالة/قناة غلط ───
            elif resp.status == 404:
                return {"ok": False, "error": "الرسالة أو القناة مو موجودة"}

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
            result = await execute_react(
                session,
                "YOUR_TOKEN_HERE",
                "https://discord.com/channels/111/222/333",
                "👍"
            )
            print(result)

    asyncio.run(test())