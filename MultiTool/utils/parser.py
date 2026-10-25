# ═════════════════════════════════════════
# 📄 utils/parser.py — تحليل البيانات
# ═════════════════════════════════════════

import re
import urllib.parse


# ═════════════════════════════════════════
# 🔗 تحليل Invite
# ═════════════════════════════════════════
def parse_invite(invite):
    """
    يحلل رابط أو كود invite
    - من https://discord.gg/abc123 → abc123
    - من https://discord.com/invite/abc123 → abc123
    - من abc123 → abc123
    """
    if not invite:
        return None

    invite = invite.strip()

    # رابط كامل
    patterns = [
        r"discord\.gg/([a-zA-Z0-9\-]+)",
        r"discord\.com/invite/([a-zA-Z0-9\-]+)",
        r"discordapp\.com/invite/([a-zA-Z0-9\-]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, invite)
        if match:
            return match.group(1)

    # كود فقط (بدون رابط)
    if re.match(r"^[a-zA-Z0-9\-]+$", invite):
        return invite

    return None


# ═════════════════════════════════════════
# 🔗 تحليل Message URL
# ═════════════════════════════════════════
def parse_message_url(url):
    """
    يحلل رابط رسالة ديسكورد
    - https://discord.com/channels/GUILD/CHANNEL/MESSAGE
    - يرجّع: {guild_id, channel_id, message_id}
    """
    if not url:
        return None

    url = url.strip()

    # نمط الرابط
    pattern = r"discord(?:app)?\.com/channels/(\d+)/(\d+)/(\d+)"
    match = re.search(pattern, url)

    if not match:
        return None

    return {
        "guild_id": match.group(1),
        "channel_id": match.group(2),
        "message_id": match.group(3),
    }


# ═════════════════════════════════════════
# 😀 تحليل Emoji
# ═════════════════════════════════════════
def parse_emoji(emoji):
    """
    يحلل الإيموجي
    - عادي: 👍 → {type: "unicode", value: "👍"}
    - مخصص: name:123 → {type: "custom", name: "name", id: "123"}
    """
    if not emoji:
        return {"type": "unicode", "value": "👍"}

    emoji = emoji.strip()

    # مخصص: name:id
    custom = re.match(r"^([a-zA-Z0-9_]+):(\d+)$", emoji)
    if custom:
        return {
            "type": "custom",
            "name": custom.group(1),
            "id": custom.group(2),
            "encoded": f"{custom.group(1)}:{custom.group(2)}",
        }

    # مخصص مع <>: <:name:id> أو <a:name:id>
    custom2 = re.match(r"^<(a?):([a-zA-Z0-9_]+):(\d+)>$", emoji)
    if custom2:
        animated = custom2.group(1) == "a"
        name = custom2.group(2)
        emoji_id = custom2.group(3)
        return {
            "type": "custom",
            "name": name,
            "id": emoji_id,
            "animated": animated,
            "encoded": f"{name}:{emoji_id}",
        }

    # عادي (unicode)
    return {
        "type": "unicode",
        "value": emoji,
        "encoded": urllib.parse.quote(emoji),
    }


# ═════════════════════════════════════════
# ✅ تحقق من Token
# ═════════════════════════════════════════
def validate_token(token):
    """
    يتحقق من شكل التوكن
    - طوله 59+ حرف
    - فيه نقطتين (.)
    """
    if not token:
        return False

    token = token.strip()

    # طول
    if len(token) < 50:
        return False

    # شكل: xxx.yyy.zzz
    parts = token.split(".")
    if len(parts) != 3:
        return False

    # الجزء الأول Base64
    try:
        import base64
        # نضيف padding
        padding = "=" * (4 - len(parts[0]) % 4)
        decoded = base64.b64decode(parts[0] + padding)
        # أول bytes = user id
        if not decoded.isdigit():
            return False
    except:
        return False

    return True


def extract_user_id_from_token(token):
    """
    يستخرج user_id من التوكن (بدون API call)
    """
    if not token:
        return None

    try:
        import base64
        first_part = token.split(".")[0]
        padding = "=" * (4 - len(first_part) % 4)
        decoded = base64.b64decode(first_part + padding)
        return decoded.decode('utf-8')
    except:
        return None


# ═════════════════════════════════════════
# 📋 تحليل Task
# ═════════════════════════════════════════
def parse_task(task):
    """
    يتحقق من مهمة ويرجع نسخة منظفة
    """
    if not isinstance(task, dict):
        return None

    task_type = task.get("type", "").lower().strip()

    # ─── join ───
    if task_type == "join":
        invite = parse_invite(task.get("invite", ""))
        if not invite:
            return None

        return {
            "type": "join",
            "invite_code": invite,
            "accounts": task.get("accounts", []),
        }

    # ─── react ───
    elif task_type == "react":
        url_data = parse_message_url(task.get("message_url", ""))
        if not url_data:
            return None

        emoji_data = parse_emoji(task.get("emoji", "👍"))

        return {
            "type": "react",
            "channel_id": url_data["channel_id"],
            "message_id": url_data["message_id"],
            "guild_id": url_data["guild_id"],
            "emoji": emoji_data["encoded"],
            "accounts": task.get("accounts", []),
        }

    return None


# ═════════════════════════════════════════
# 👤 تحليل Account
# ═════════════════════════════════════════
def parse_account(account):
    """
    يتحقق من حساب ويرجع نسخة منظفة
    """
    if not isinstance(account, dict):
        return None

    name = account.get("name", "").strip()
    token = account.get("token", "").strip()
    enabled = account.get("enabled", True)

    if not name or not token:
        return None

    return {
        "name": name,
        "token": token,
        "enabled": enabled,
    }


# ═════════════════════════════════════════
# 🌐 تحليل Header
# ═════════════════════════════════════════
def parse_rate_limit(headers):
    """
    يحلل rate limit headers
    """
    return {
        "limit": int(headers.get("x-ratelimit-limit", 0)),
        "remaining": int(headers.get("x-ratelimit-remaining", 0)),
        "reset_after": float(headers.get("x-ratelimit-reset-after", 0)),
        "global": headers.get("x-ratelimit-global", "false") == "true",
    }


# ═════════════════════════════════════════
# 🧪 اختبار
# ═════════════════════════════════════════
if __name__ == "__main__":
    # اختبار invite
    print("── Invite ──")
    print(parse_invite("https://discord.gg/abc123"))
    print(parse_invite("https://discord.com/invite/xyz789"))
    print(parse_invite("abc123"))
    print(parse_invite("رابط غلط"))

    # اختبار message URL
    print("\n── Message URL ──")
    print(parse_message_url("https://discord.com/channels/123/456/789"))
    print(parse_message_url("https://discordapp.com/channels/111/222/333"))

    # اختبار emoji
    print("\n── Emoji ──")
    print(parse_emoji("👍"))
    print(parse_emoji("cool:123456789"))
    print(parse_emoji("<:name:123456789>"))