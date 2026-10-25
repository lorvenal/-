# ═════════════════════════════════════════
# 🎯 core/executor.py — منفذ المهام
# ═════════════════════════════════════════

import aiohttp
import asyncio
import urllib.parse

from utils.parser import parse_invite, parse_message_url, parse_emoji
from tasks.join import execute_join
from tasks.react import execute_react


API_BASE = "https://discord.com/api/v10"
TIMEOUT = 30

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "discord/1.0.9175 Chrome/128.0.6613.186 "
    "Electron/32.2.7 Safari/537.36"
)


class Executor:
    """ينفذ المهام على الحسابات + عميل HTTP"""

    def __init__(self, delay_func=None, logger=None):
        self.delay_func = delay_func
        self.logger = logger
        self.session = None

        # ─── إحصائيات ───
        self.total_success = 0
        self.total_failed = 0

    # ═════════════════════════════════════════
    # 🌐 إدارة الجلسة
    # ═════════════════════════════════════════
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()

    def _headers(self, token):
        """Headers موحدة"""
        return {
            "Authorization": token,
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        }

    # ═════════════════════════════════════════
    # 👤 معلومات الحساب
    # ═════════════════════════════════════════
    async def get_me(self, token):
        """يجيب معلومات الحساب"""
        try:
            async with self.session.get(
                f"{API_BASE}/users/@me",
                headers=self._headers(token),
                timeout=aiohttp.ClientTimeout(total=TIMEOUT)
            ) as resp:
                if resp.status == 200:
                    return {"ok": True, "data": await resp.json()}
                elif resp.status == 401:
                    return {"ok": False, "error": "توكن غلط"}
                else:
                    return {"ok": False, "error": f"HTTP {resp.status}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ═════════════════════════════════════════
    # 🚀 تنفيذ المهام
    # ═════════════════════════════════════════
    async def execute(self, accounts, tasks):
        """
        ينفذ كل المهام على كل الحسابات

        Args:
            accounts: قائمة Account
            tasks: قائمة dicts

        Returns:
            dict: {success, failed, details}
        """
        details = []

        for task_idx, task in enumerate(tasks, 1):
            task_type = task.get("type", "?")

            if self.logger:
                self.logger(f"\n┌─ المهمة #{task_idx}: {task_type}")

            # ─── الحسابات المعنية ───
            target_names = task.get("accounts", [])

            if target_names:
                target_accounts = [
                    a for a in accounts if a.name in target_names
                ]
            else:
                target_accounts = accounts

            # ─── لكل حساب ───
            for acc_idx, account in enumerate(target_accounts, 1):

                if self.logger:
                    self.logger(
                        f"├─ [{acc_idx}/{len(target_accounts)}] {account.name}"
                    )

                # ─── تحقق من التوكن ───
                me = await self.get_me(account.token)

                if not me["ok"]:
                    self.total_failed += 1
                    account.failed += 1
                    details.append({
                        "task": task_type,
                        "account": account.name,
                        "success": False,
                        "message": me["error"],
                    })

                    if self.logger:
                        self.logger(f"│  ❌ {me['error']}")

                    if acc_idx < len(target_accounts) and self.delay_func:
                        await self.delay_func()
                    continue

                # ─── حفظ معلومات الحساب ───
                account.set_info(me["data"])

                # ─── نفذ ───
                success, message = await self._run_one(account, task)

                if success:
                    self.total_success += 1
                    account.success += 1
                else:
                    self.total_failed += 1
                    account.failed += 1

                details.append({
                    "task": task_type,
                    "account": account.name,
                    "success": success,
                    "message": message,
                })

                if self.logger:
                    icon = "✅" if success else "❌"
                    self.logger(f"│  {icon} {message}")

                # ─── تأخير ───
                if acc_idx < len(target_accounts) and self.delay_func:
                    await self.delay_func()

            if self.logger:
                self.logger(f"└─ انتهت المهمة #{task_idx}")

            # ─── تأخير بين المهام ───
            if task_idx < len(tasks) and self.delay_func:
                await self.delay_func()

        return {
            "success": self.total_success,
            "failed": self.total_failed,
            "details": details,
        }

    # ═════════════════════════════════════════
    # 🎯 مهمة واحدة
    # ═════════════════════════════════════════
    async def _run_one(self, account, task):
        """ينفذ مهمة على حساب واحد"""
        task_type = task.get("type", "").lower()

        # ═══ join ═══
        if task_type == "join":
            result = await execute_join(
                self.session,
                account.token,
                task.get("invite", ""),
                USER_AGENT,
            )
            if result["ok"]:
                return True, f"دخل {result.get('guild', '?')}"
            return False, result.get("error", "?")

        # ═══ react ═══
        elif task_type == "react":
            result = await execute_react(
                self.session,
                account.token,
                task.get("message_url", ""),
                task.get("emoji", "👍"),
                USER_AGENT,
            )
            if result["ok"]:
                return True, f"رد {result.get('emoji', '?')}"
            return False, result.get("error", "?")

        # ═══ غير معروف ═══
        else:
            return False, f"نوع غير معروف: {task_type}"