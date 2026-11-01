"""WhatsApp Web Bridge for Smart Kitchen AI.

Runs a real WhatsApp Web browser session with persistent login, sends 6:00 PM evening options
to your flat group, and handles voting and grocery ordering in real time.
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
from pathlib import Path

# Fix Windows console UTF-8 encoding
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import httpx

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

PROFILE_DIR = DATA_DIR / "whatsapp_profile"
PROFILE_DIR.mkdir(parents=True, exist_ok=True)

QR_PATH = DATA_DIR / "whatsapp_qr.png"
STATUS_FILE = DATA_DIR / "whatsapp_bridge_status.json"


def _get_api_url() -> str:
    """Check local backend first, fallback to live cloud backend."""
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        if s.connect_ex(("127.0.0.1", 8000)) == 0:
            return "http://127.0.0.1:8000"
    return "https://smartkitchenai-qyqvl8jpqgvr5zilv2itjz.streamlit.app"


API_URL = os.environ.get("SMARTKITCHEN_API") or _get_api_url()


def _set_status(status: str, detail: str = "") -> None:
    import json
    try:
        STATUS_FILE.write_text(json.dumps({"status": status, "detail": detail, "updated_at": time.time()}), encoding="utf-8")
    except Exception:
        pass


async def send_group_message(page, text: str) -> bool:
    """Type and send a message into the currently open WhatsApp chat."""
    try:
        input_box = page.locator('footer div[contenteditable="true"][data-tab="10"]')
        await input_box.wait_for(timeout=5000)
        await input_box.click()

        lines = text.strip().split("\n")
        for i, line in enumerate(lines):
            await page.keyboard.insert_text(line)
            if i < len(lines) - 1:
                await page.keyboard.down("Shift")
                await page.keyboard.press("Enter")
                await page.keyboard.up("Shift")
        await page.keyboard.press("Enter")
        await asyncio.sleep(1.0)
        return True
    except Exception as exc:
        print(f"⚠️ Error sending message: {exc}", flush=True)
        return False


async def open_group(page, group_name: str) -> bool:
    """Search and click the flat WhatsApp group."""
    print(f"🔍 Searching for group: '{group_name}'...", flush=True)
    try:
        search_box = page.locator('div[contenteditable="true"][data-tab="3"]')
        await search_box.wait_for(timeout=15000)
        await search_box.click()
        await search_box.fill("")
        await page.keyboard.insert_text(group_name)
        await asyncio.sleep(2.0)

        # Look for chat matching name case-insensitively
        group_item = page.locator(f'span[title*="{group_name}" i]').first
        await group_item.wait_for(timeout=10000)
        await group_item.click()
        print(f"✅ Successfully opened group: '{group_name}'", flush=True)
        _set_status("connected", f"Actively monitoring group: {group_name}")
        await asyncio.sleep(2.0)
        return True
    except Exception as exc:
        print(f"❌ Could not find group '{group_name}'. Please click into your group manually in WhatsApp Web. ({exc})", flush=True)
        _set_status("connected", f"Please select '{group_name}' in WhatsApp Web window.")
        return False


async def run_bridge(group_name: str):
    from playwright.async_api import async_playwright

    print(f"🚀 Starting Smart Kitchen WhatsApp Bridge...", flush=True)
    print(f"🔗 Connected to API: {API_URL}", flush=True)
    print(f"📁 Session stored at: {PROFILE_DIR}", flush=True)
    _set_status("starting", "Launching browser...")

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=False,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--start-maximized",
            ],
            viewport=None,
        )
        page = context.pages[0] if context.pages else await context.new_page()

        print("🌐 Opening WhatsApp Web...", flush=True)
        await page.goto("https://web.whatsapp.com")

        print("\n" + "=" * 60, flush=True)
        print("📲 SCAN THE QR CODE ON SCREEN USING YOUR PHONE WHATSAPP:", flush=True)
        print("   WhatsApp ➔ Three Dots (or Settings) ➔ Linked Devices ➔ Link a Device", flush=True)
        print("   (Or click 'Link with phone number' below the QR code on screen!)", flush=True)
        print("=" * 60 + "\n", flush=True)

        logged_in = False

        # Wait up to 15 minutes for user to link
        for step in range(450):
            try:
                pane = page.locator("#pane-side")
                if await pane.is_visible(timeout=1000):
                    logged_in = True
                    break
            except Exception:
                pass

            # Auto-click QR reload button if it expired so it's always live!
            try:
                reload_locator = page.locator('span[data-icon="refresh"], button:has-text("reload")').first
                if await reload_locator.is_visible(timeout=500):
                    await reload_locator.click()
                    print("🔄 QR Code refreshed automatically.", flush=True)
                    await asyncio.sleep(1.0)
            except Exception:
                pass

            # Take/update screenshot
            try:
                canvas = page.locator("canvas").first
                if await canvas.is_visible(timeout=500):
                    await page.screenshot(path=str(QR_PATH))
                    _set_status("waiting_qr", "QR code is ready to scan")
            except Exception:
                pass

            await asyncio.sleep(2.0)

        if not logged_in:
            print("⏱️ Login timed out. Please run the script again to link WhatsApp.", flush=True)
            _set_status("timeout", "Login timed out")
            return

        print("🎉 Login successful! WhatsApp Web is ready.", flush=True)
        if QR_PATH.is_file():
            try:
                QR_PATH.unlink()
            except Exception:
                pass

        await asyncio.sleep(3.0)
        await open_group(page, group_name)

        last_seen_message = ""
        last_nudge_hour = -1

        print(f"\n🟢 Bot is now actively monitoring '{group_name}'!", flush=True)
        print("   - Flatmates can vote (e.g. 'Option 2', 'Paneer')", flush=True)
        print("   - Flatmates can change choices anytime", flush=True)
        print("   - Say 'Ordered' to trigger confirmation", flush=True)
        print("   - Say 'Yes' to lock and schedule cook call\n", flush=True)

        while True:
            try:
                # 1. Check for incoming messages
                msg_elements = page.locator('div.message-in div.copyable-text')
                count = await msg_elements.count()
                if count > 0:
                    last_msg_el = msg_elements.nth(count - 1)
                    raw_text = await last_msg_el.inner_text()
                    raw_text = raw_text.strip()

                    if raw_text and raw_text != last_seen_message:
                        last_seen_message = raw_text
                        print(f"📩 New message from flat: {raw_text}", flush=True)

                        try:
                            async with httpx.AsyncClient(timeout=15.0) as client:
                                res = await client.post(
                                    f"{API_URL}/api/flat-chat/message",
                                    json={"sender": "Flatmate", "text": raw_text},
                                )
                                if res.status_code == 200:
                                    data = res.json()
                                    reply = data.get("reply_text")
                                    if reply:
                                        print(f"🤖 Bot responding: {reply[:60]}...", flush=True)
                                        await send_group_message(page, reply)
                        except Exception as api_err:
                            print(f"⚠️ API error: {api_err}", flush=True)

                # 2. Check scheduled 6:00 PM kickoff
                now = time.localtime()
                if now.tm_hour == 18 and now.tm_min < 10 and last_nudge_hour != 18:
                    try:
                        async with httpx.AsyncClient(timeout=10.0) as client:
                            res = await client.get(f"{API_URL}/api/flat-chat/session/today")
                            if res.status_code == 200:
                                sdata = res.json()
                                if sdata.get("stage") == "choosing_meal" and sdata.get("nudge_count") == 0:
                                    print("📢 6:00 PM Evening Kickoff firing!", flush=True)
                                    await send_group_message(page, sdata["kickoff_text"])
                                    last_nudge_hour = 18
                    except Exception as exc:
                        print(f"⚠️ Kickoff check error: {exc}", flush=True)

            except Exception:
                pass

            await asyncio.sleep(2.0)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Smart Kitchen WhatsApp Web Bridge")
    parser.add_argument(
        "--group",
        "-g",
        type=str,
        default=os.environ.get("WHATSAPP_GROUP_NAME", "kitchen crew"),
        help="Exact WhatsApp Group Name",
    )
    args = parser.parse_args()

    group_name = args.group.strip() or "kitchen crew"
    asyncio.run(run_bridge(group_name))


if __name__ == "__main__":
    main()
