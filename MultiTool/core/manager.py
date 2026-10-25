# ═════════════════════════════════════════
# 📊 core/manager.py — إدارة الحسابات والمهام
# ═════════════════════════════════════════

import json
import os

from core.account import Account, account_from_dict


class Manager:
    """يدير الحسابات والمهام"""

    def __init__(self, accounts_file="accounts.json",
                 tasks_file="tasks.json"):
        self.accounts_file = accounts_file
        self.tasks_file = tasks_file

        self.accounts = []
        self.tasks = []

    # ═════════════════════════════════════════
    # 📂 تحميل
    # ═════════════════════════════════════════
    def load_accounts(self):
        """يحمّل الحسابات"""
        if not os.path.exists(self.accounts_file):
            return []

        try:
            with open(self.accounts_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"❌ {self.accounts_file} تالف: {e}")
            return []

        accounts = []
        for raw in data.get("accounts", []):
            acc = account_from_dict(raw)
            if acc.token:
                accounts.append(acc)

        self.accounts = accounts
        return accounts

    def load_tasks(self):
        """يحمّل المهام"""
        if not os.path.exists(self.tasks_file):
            return []

        try:
            with open(self.tasks_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"❌ {self.tasks_file} تالف: {e}")
            return []

        self.tasks = data.get("tasks", [])
        return self.tasks

    # ═════════════════════════════════════════
    # 🔍 فلترة
    # ═════════════════════════════════════════
    def get_enabled(self):
        """يرجع الحسابات المفعّلة"""
        return [a for a in self.accounts if a.enabled]

    def get_account_by_name(self, name):
        """يجيب حساب بالاسم"""
        for a in self.accounts:
            if a.name == name:
                return a
        return None

    # ═════════════════════════════════════════
    # 📊 عرض
    # ═════════════════════════════════════════
    def summary(self):
        """ملخص"""
        enabled = len([a for a in self.accounts if a.enabled])
        disabled = len(self.accounts) - enabled

        lines = [
            f"👥 الحسابات: {len(self.accounts)}",
            f"   ✅ مفعّلة: {enabled}",
            f"   ⏸️ معطّلة: {disabled}",
            "",
            f"📋 المهام: {len(self.tasks)}",
        ]

        for i, t in enumerate(self.tasks, 1):
            ttype = t.get("type", "?")
            lines.append(f"   {i}. {ttype}")

        return "\n".join(lines)