#!/usr/bin/env python3
"""
Cloudflare Email Worker 邮箱后端
"""

import random
import string
import requests
from config import EMAIL_API_URL, EMAIL_API_TOKEN, EMAIL_DOMAIN
from .base import EmailProvider


class CloudflareEmailProvider(EmailProvider):
    """基于 Cloudflare Email Worker 的邮箱服务"""

    def __init__(self):
        self.api_url = EMAIL_API_URL
        self.headers = {"Authorization": f"Bearer {EMAIL_API_TOKEN}"}

    def create_email(self, prefix=None):
        if prefix is None:
            prefix = "".join(random.choices(string.ascii_lowercase, k=6))
        suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
        return f"{prefix}-{suffix}@{EMAIL_DOMAIN}"

    def get_messages(self, address):
        """通过 Cloudflare Email Worker API 获取邮件"""
        try:
            resp = requests.get(
                f"{self.api_url}/messages",
                params={"address": address},
                headers=self.headers,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("messages", [])
        except Exception as e:
            print(f"❌ 获取邮件失败: {e}")
            return []

    def cleanup(self, address):
        """清理邮箱"""
        try:
            resp = requests.delete(
                f"{self.api_url}/messages",
                params={"address": address},
                headers=self.headers,
                timeout=15,
            )
            resp.raise_for_status()
            print(f"🗑️ 已清理 {address} 的邮件")
        except Exception as e:
            print(f"⚠️ 清理邮件失败: {e}")
