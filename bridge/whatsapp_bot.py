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

import httpx

ROOT = Path(__file__).resolve().parent.parent
PROFILE_DIR = ROOT / "data" / "whatsapp_profile"
PROFILE_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_API = "http://127.0.0.1:8000"


def _get_api_url() -> str:
    """Check local backend first, fallback to live cloud backend."""
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        if s.connect_ex(("127.0.0.1", 8000)) == 0:
            return "http://127.0.0.1:8000"
    return "https://smartkitchenai-qyqvl8jpqgvr5zilv2itjz.streamlit.app"


API_URL = os.environ.get("SMARTKITCHEN_API") or _get_api_url()


async def send_group_message(page, text: str) -> bool:
    """Type and send a message into the currently open WhatsApp chat."""
    try:
        # WhatsApp message input box selector
        input_box = page.locator('footer div[contenteditable="true"][data-tab="10"]')
        await input_box.wait_for(timeout=5000)
        await input_box.click()

        # Handle multiline text: shift+enter for newlines
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
        print(f"⚠️ Error sending message: {exc}")
        return False


async def open_group(page, group_name: str) -> bool:
    """Search and click the flat WhatsApp group."""
    print(f"🔍 Searching for group: '{group_name}'...")
    try:
        search_box = page.locator('div[contenteditable="true"][data-tab="3"]')
        await search_box.wait_for(timeout=15000)
        await search_box.click()
        await search_box.fill("")
        await page.keyboard.insert_text(group_name)
        await asyncio.sleep(2.0)

        # Click the chat matching title
        group_item = page.locator(f'span[title="{group_name}"]').first
        await group_item.wait_for(timeout=10000)
        await group_item.click()
        print(f"✅ Successfully opened group: '{group_name}'")
        await asyncio.sleep(2.0)
        return True
    except Exception as exc:
        print(f"❌ Could not find group '{group_name}'. Please click into your group manually in WhatsApp Web. ({exc})")
        return False


async def run_bridge(group_name: str):
    from playwright.async_api import async_playwright

    print(f"🚀 Starting Smart Kitchen WhatsApp Bridge...")
    print(f"🔗 Connected to API: {API_URL}")
    print(f"📁 Session stored at: {PROFILE_DIR}")

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

        print("🌐 Opening WhatsApp Web...")
        await page.goto("https://web.whatsapp.com")

        print("\n" + "=" * 60)
        print("📲 SCAN THE QR CODE ON SCREEN USING YOUR PHONE WHATSAPP:")
        print("   WhatsApp ➔ Three Dots (or Settings) ➔ Linked Devices ➔ Link a Device")
        print("=" * 60 + "\n")

        # Wait until chat list pane loads (indicates successful login)
        while True:
            try:
                pane = page.locator("#pane-side")
                if await pane.is_visible(timeout=3000):
                    print("🎉 Login successful! WhatsApp Web is ready.")
                    break
            except Exception:
                pass
            await asyncio.sleep(2.0)

        await asyncio.sleep(3.0)
        await open_group(page, group_name)

        last_seen_message = ""
        last_nudge_hour = -1

        print(f"\n🟢 Bot is now actively monitoring '{group_name}'!")
        print("   - Flatmates can vote (e.g. 'Option 2', 'Paneer')")
        print("   - Flatmates can change choices anytime")
        print("   - Say 'Ordered' to trigger confirmation")
        print("   - Say 'Yes' to lock and schedule cook call\n")

        while True:
            try:
                # 1. Check for incoming messages
                # Read last message in chat
                msg_elements = page.locator('div.message-in div.copyable-text')
                count = await msg_elements.count()
                if count > 0:
                    last_msg_el = msg_elements.nth(count - 1)
                    raw_text = await last_msg_el.inner_text()
                    raw_text = raw_text.strip()

                    if raw_text and raw_text != last_seen_message:
                        last_seen_message = raw_text
                        print(f"📩 New message from flat: {raw_text}")

                        # Forward to Smart Kitchen Decision API
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
                                        print(f"🤖 Bot responding: {reply[:60]}...")
                                        await send_group_message(page, reply)
                        except Exception as api_err:
                            print(f"⚠️ API error: {api_err}")

                # 2. Check scheduled 6:00 PM kickoff and hourly nudges
                now = time.localtime()
                # 6 PM kickoff check (between 18:00 and 18:05)
                if now.tm_hour == 18 and now.tm_min < 5 and last_nudge_hour != 18:
                    try:
                        async with httpx.AsyncClient(timeout=10.0) as client:
                            res = await client.get(f"{API_URL}/api/flat-chat/session/today")
                            if res.status_code == 200:
                                sdata = res.json()
                                if sdata.get("stage") == "choosing_meal" and sdata.get("nudge_count") == 0:
                                    print("📢 6:00 PM Evening Kickoff firing!")
                                    await send_group_message(page, sdata["kickoff_text"])
                                    last_nudge_hour = 18
                    except Exception as exc:
                        print(f"⚠️ Kickoff check error: {exc}")

            except Exception as loop_err:
                pass

            await asyncio.sleep(2.0)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Smart Kitchen WhatsApp Web Bridge")
    parser.add_argument(
        "--group",
        "-g",
        type=str,
        default=os.environ.get("WHATSAPP_GROUP_NAME", ""),
        help="Exact WhatsApp Group Name",
    )
    args = parser.parse_args()

    group_name = args.group.strip()
    if not group_name:
        print("=" * 60)
        print("🥘 Smart Kitchen AI - WhatsApp Web Bridge")
        print("=" * 60)
        group_name = input("Enter your flat's WhatsApp Group Name (e.g. Flat 302): ").strip()

    if not group_name:
        print("❌ Group name cannot be empty. Exiting.")
        return

    asyncio.run(run_bridge(group_name))


if __name__ == "__main__":
    main()
