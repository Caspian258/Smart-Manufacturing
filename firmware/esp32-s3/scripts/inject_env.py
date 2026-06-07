#!/usr/bin/env python3
import os, sys
from pathlib import Path

def find_env():
    p = Path(__file__).resolve().parent
    for _ in range(5):
        c = p / ".env"
        if c.exists(): return c
        p = p.parent
    return None

VARS = ["WIFI_SSID","WIFI_PASSWORD","WIFI_BSSID","WIFI_CHANNEL","MQTT_BROKER","MQTT_PORT",
        "MQTT_USER","MQTT_PASSWORD","MACHINE_ID","OTA_PASSWORD"]

env_file = find_env()
if not env_file:
    print("-DENV_NOT_FOUND"); sys.exit(0)

env = {}
for line in env_file.read_text().splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line: continue
    k, _, v = line.partition("=")
    env[k.strip()] = v.strip().strip('"').strip("'")

for var in VARS:
    val = env.get(var, "")
    if not val: continue
    if var in ("MQTT_PORT", "WIFI_CHANNEL"): print(f"-D{var}={val}")
    else: print(f'-D{var}=\\"{val.replace(chr(34), chr(92)+chr(34))}\\"')
