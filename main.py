#!/usr/bin/env python3
"""
Tavily API Key 自动注册工具
支持多线程并行注册，带冷却间隔避免风控
"""
import sys
import time
import random
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from intelligent_tavily_automation import IntelligentTavilyAutomation
from config import EMAIL_PREFIX, CAPTCHA_SOLVER
import config

# 统计
lock = threading.Lock()
success_count = 0
fail_count = 0

# 全局速率控制：每次注册前必须等上一次启动后 N 秒
rate_lock = threading.Lock()
last_start_time = 0
COOLDOWN = 45  # 两次注册启动间隔（秒）


def detect_backends():
    """检测已配置的邮箱后端"""
    backends = []
    if getattr(config, 'EMAIL_DOMAIN', '') and getattr(config, 'EMAIL_API_URL', '') and getattr(config, 'EMAIL_API_TOKEN', ''):
        backends.append({
            'name': 'cloudflare',
            'label': f"Cloudflare ({config.EMAIL_DOMAIN})",
        })
    if getattr(config, 'DUCKMAIL_BEARER', '') and getattr(config, 'DUCKMAIL_DOMAIN', ''):
        backends.append({
            'name': 'duckmail',
            'label': f"DuckMail ({config.DUCKMAIL_DOMAIN})",
        })
    return backends


def choose_backend(backends):
    """选择邮箱后端"""
    if len(backends) == 0:
        print("❌ 未配置任何邮箱后端，请先编辑 config.py")
        sys.exit(1)
    if len(backends) == 1:
        print(f"📮 邮箱后端: {backends[0]['label']}")
        return backends[0]['name']

    print("📮 可用邮箱后端:")
    for i, b in enumerate(backends, 1):
        print(f"  {i}. {b['label']}")
    while True:
        choice = input(f"选择 (默认 1): ").strip()
        if choice == '':
            return backends[0]['name']
        if choice.isdigit() and 1 <= int(choice) <= len(backends):
            return backends[int(choice) - 1]['name']
        print("❌ 无效选择")


def wait_for_cooldown():
    """全局速率控制，确保两次注册启动间隔足够"""
    global last_start_time
    with rate_lock:
        now = time.time()
        wait = COOLDOWN - (now - last_start_time)
        if wait > 0:
            # 加点随机抖动
            wait += random.uniform(0, 10)
            time.sleep(wait)
        last_start_time = time.time()


def register_one(task_id, total, provider_name):
    """单个注册任务"""
    global success_count, fail_count

    # 等待冷却
    wait_for_cooldown()

    with lock:
        print(f"🔄 [{task_id}/{total}] 开始注册...")

    automation = None
    try:
        config.EMAIL_PROVIDER = provider_name
        automation = IntelligentTavilyAutomation()
        automation.email_prefix = EMAIL_PREFIX
        automation.start_browser(headless=True)

        start_time = time.time()
        api_key = automation.run_complete_automation()
        elapsed = time.time() - start_time

        with lock:
            if api_key:
                success_count += 1
                print(f"✅ [{task_id}/{total}] 成功 | {automation.email} | {api_key[:20]}... | {elapsed:.0f}s")
            else:
                fail_count += 1
                print(f"❌ [{task_id}/{total}] 失败 | {elapsed:.0f}s")

        return api_key

    except Exception as e:
        with lock:
            fail_count += 1
            print(f"❌ [{task_id}/{total}] 出错: {e}")
        return None
    finally:
        if automation:
            try:
                automation.close_browser()
            except:
                pass


def main():
    global success_count, fail_count

    print("🚀 Tavily API Key 自动注册工具")
    print("=" * 50)
    print(f"🔐 验证码: {CAPTCHA_SOLVER}")

    backends = detect_backends()
    provider_name = choose_backend(backends)

    count_input = input(f"\n📊 注册数量 (默认 10): ").strip()
    count = int(count_input) if count_input.isdigit() and int(count_input) > 0 else 10

    threads_input = input(f"🧵 并行线程 (默认 2): ").strip()
    threads = int(threads_input) if threads_input.isdigit() and int(threads_input) > 0 else 2
    threads = min(threads, count)

    print(f"\n📋 配置: {count} 个账户 / {threads} 线程 / 间隔 {COOLDOWN}s")
    print(f"🚀 开始注册...\n")

    success_count = 0
    fail_count = 0
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=threads) as executor:
        futures = [executor.submit(register_one, i, count, provider_name) for i in range(1, count + 1)]
        for future in as_completed(futures):
            pass

    elapsed = time.time() - start_time
    print(f"\n{'=' * 50}")
    print(f"🎉 全部完成! 耗时 {elapsed:.0f}s")
    print(f"📊 成功 {success_count}/{count} | 失败 {fail_count}/{count}")
    print(f"📄 API Key 已保存到 api_keys.md")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    main()
