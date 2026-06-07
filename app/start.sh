#!/bin/bash
pkill -f "main.py" 2>/dev/null
sleep 1
cd /opt/smart-manufacturing
/opt/smart-manufacturing/venv/bin/python3 app/main.py
