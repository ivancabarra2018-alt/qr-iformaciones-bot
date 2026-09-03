#!/bin/bash
# Script que mantiene el Mac despierto mientras corre el bot QR
exec /usr/bin/caffeinate -si \
    /Users/ASUS/.gemini/antigravity/scratch/qr_bot/venv/bin/python \
    /Users/ASUS/.gemini/antigravity/scratch/qr_bot/bot.py
