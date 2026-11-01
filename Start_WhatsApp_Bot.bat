@echo off
title Smart Kitchen AI - WhatsApp Bot Bridge
echo ========================================================
echo       🥘 SMART KITCHEN AI - WHATSAPP BOT BRIDGE
echo ========================================================
echo.
cd /d "C:\Users\shubh\OneDrive\Documents\Desktop\smartkitchenai"

call .venv\Scripts\python.exe bridge\whatsapp_bot.py %*

echo.
pause
