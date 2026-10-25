# ═════════════════════════════════════════
# 👤 core/account.py — كلاس الحساب
# ═════════════════════════════════════════

from utils.parser import validate_token, extract_user_id_from_token


class Account:
    """يمثل حساب ديسكورد واحد"""

    def __init__(self, name, token, enabled=True):
        self.name = name
        self.token = token
        self.enabled = enabled

        # ─── معلومات (تُجلب لاحقاً) ───
        self.user_id = None
        self.username = None
        self.avatar = None
        self.verified = False

        # ─── حالة ───
        self.valid = False
        self.checked = False

        # ─── إحصائيات ───
        self.success = 0
        self.failed = 0

        # ─── استخرج user_id من التوكن ───
        self.user_id = extract_user_id_from_token(token)

    def __repr__(self):
        return f"<Account {self.name} ({self.user_id})>"

    def set_info(self, data):
        """يحفظ معلومات من API"""
        self.username = data.get("username")
        self.avatar = data.get("avatar")
        self.verified = data.get("verified", False)
        self.user_id = data.get("id")
        self.valid = True
        self.checked = True

    def mark_invalid(self):
        """يعلّمه كـ غير صالح"""
        self.valid = False
        self.checked = True

    @property
    def display(self):
        """عرض قصير"""
        if self.username:
            return f"@{self.username}"
        return self.name

    @property
    def rate(self):
        """معدل النجاح"""
        total = self.success + self.failed
        if total == 0:
            return 0
        return (self.success / total) * 100


# ─── Factory function ───
def account_from_dict(data):
    """ينشئ Account من dict"""
    return Account(
        name=data.get("name", "?"),
        token=data.get("token", ""),
        enabled=data.get("enabled", True),
    )