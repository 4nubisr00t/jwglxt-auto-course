# -*- coding: utf-8 -*-
"""
通识选修课（kklxdm=10）全量抓取
====================================
实测：单次大分页即可拿到全量（200+ 行 / 0.2s）。

用法:
  python crawl_all.py              # 拉全量并保存 data/tongshi_full.json
  python crawl_all.py --kklxdm 01  # 换课程类型: 01主修 10通识 11特殊
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jw_cdp_client import (get_cdp_ws_url, cdp_get_cookies, build_session,
                           check_alive, JWClient)

KKLXDM = "10"
BIG_PAGE = 100000            # 大分页一次拉全
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

KKLX_NAME = {"01": "主修", "10": "通识选修", "11": "其他特殊"}


def main():
    kklxdm = KKLXDM
    if "--kklxdm" in sys.argv:
        kklxdm = sys.argv[sys.argv.index("--kklxdm") + 1]

    ws = get_cdp_ws_url()
    cookies = cdp_get_cookies(ws)
    session = build_session(cookies)
    if not check_alive(session):
        sys.exit("会话失效")
    client = JWClient(session)
    if not client._h("rwlx"):
        client.cdp_refresh_hidden(ws)

    t0 = time.time()
    rows, _ = client.search_courses(kklxdm, page=1, page_size=BIG_PAGE)
    dt = time.time() - t0
    print(f"[抓取] kklxdm={kklxdm}({KKLX_NAME.get(kklxdm, '?')}) "
          f"-> {len(rows)} 行, 耗时 {dt:.1f}s")

    courses = {}
    for r in rows:
        courses.setdefault(r["kch_id"], []).append(r)

    full = sum(1 for r in rows if r.get("yxzrs"))
    multi = sum(1 for c in courses.values() if len(c) > 1)
    print(f"[统计] 教学班行 {len(rows)} | 课程 {len(courses)} | "
          f"多教学班课程 {multi} | 已满行 {full}")

    out = {
        "meta": {
            "kklxdm": kklxdm, "kklxmc": KKLX_NAME.get(kklxdm),
            "xkxnm": client._h("xkxnm"), "xkxqm": client._h("xkxqm"),
            "rwlx": client._h("rwlx"), "xklc": client._h("xklc"),
            "fetched_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_rows": len(rows), "total_courses": len(courses),
        },
        "courses": {
            kch_id: {
                "kch": c[0].get("kch"), "kcmc": c[0].get("kcmc"),
                "jxbzls": c[0].get("jxbzls"), "xf": c[0].get("xf"),
                "kzmc": c[0].get("kzmc"),
                "classes": [
                    {"jxb_id": r.get("jxb_id"), "jxbmc": r.get("jxbmc"),
                     "yxzrs": r.get("yxzrs"), "cxbj": r.get("cxbj"),
                     "kch_id": r.get("kch_id")}
                    for r in c
                ],
            }
            for kch_id, c in courses.items()
        },
    }
    os.makedirs(OUT_DIR, exist_ok=True)
    out_path = os.path.join(OUT_DIR, f"courses_{kklxdm}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"[保存] {out_path} ({os.path.getsize(out_path)} bytes)")


if __name__ == "__main__":
    main()