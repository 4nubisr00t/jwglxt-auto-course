# -*- coding: utf-8 -*-
"""验证: DevToolsActivePort -> CDP Storage.getCookies 链路"""
import json
import os
import sys
import websocket

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jw_cdp_client import DOMAIN_FILTER

PORT_FILE = os.path.join(
    os.environ.get("USERPROFILE") or os.path.expanduser("~"),
    "AppData", "Local", "Google", "Chrome", "User Data", "DevToolsActivePort",
)

with open(PORT_FILE, "r") as f:
    lines = [l.strip() for l in f if l.strip()]
port, ws_path = lines[0], lines[1]
ws_url = f"ws://127.0.0.1:{port}{ws_path}"
print(f"[+] ws url: {ws_url}")

ws = websocket.create_connection(ws_url, timeout=5, suppress_origin=True)
ws.send(json.dumps({"id": 1, "method": "Storage.getCookies"}))
while True:
    msg = json.loads(ws.recv())
    if msg.get("id") == 1:
        if "error" in msg:
            print(f"[-] CDP error: {msg['error']}")
        else:
            cookies = msg["result"]["cookies"]
            jw = [c for c in cookies if DOMAIN_FILTER in (c.get("domain") or "")]
            print(f"[+] total cookies: {len(cookies)}")
            print(f"[+] {DOMAIN_FILTER} cookies: {len(jw)}")
            for c in jw[:10]:
                print(f"    {c['name']} = {c['value'][:40]}... (domain={c['domain']}, httpOnly={c.get('httpOnly')})")
        break
ws.close()