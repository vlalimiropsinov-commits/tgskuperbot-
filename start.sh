#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
[ -d venv ] || { python3 -m venv venv; venv/bin/pip install -U pip; venv/bin/pip install -r requirements.txt; }
exec venv/bin/python bot.py
