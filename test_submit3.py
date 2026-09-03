# -*- coding: utf-8 -*-
"""
提交测试 #3：目标 = 未选的满员通识课（大学实验室安全 200/200, jxbzls=1）
======================================================================
修复点：已选列表用 ChoosedDisplay POST（带学籍参数）解析，不再解析 HTML。
规则不变：只做加法，绝不做减法。
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jw_cdp_client import (get_cdp_ws_url, cdp_get_cookies, build_session,
                           check_alive, JWClient)

TARGET_KKLXDM = "10"


def fetch_choosed(client):
    """POST ChoosedDisplay 拿已选课程 JSON（对齐浏览器真实请求）。"""
    params = {
        "jg_id": client._h("jg_id_1") or client._h("jg_id"),
        "zyh_id": client._h("zyh_id"),
        "njdm_id": client._h("njdm_id"),
        "zyfx_id": client._h("zyfx_id"),
        "bh_id": client._h("bh_id"),
        "xz": client._h("xz"),
        "ccdm": client._h("ccdm"),
        "xqh_id": client._h("xqh_id"),
        "xkxnm": client._h("xkxnm"),
        "xkxqm": client._h("xkxqm"),
        "xkly": client._h("xkly"),
    }
    r = client.s.post(client._u("/xsxk/zzxkyzb_cxZzxkYzbChoosedDisplay.html"),
                      data=params, timeout=10)
    rows = r.json()
    return {row["kch_id"]: row.get("kcmc") for row in rows}, rows


def main():
    ws = get_cdp_ws_url()
    cookies = cdp_get_cookies(ws)
    session = build_session(cookies)
    if not check_alive(session):
        sys.exit("会话失效")
    client = JWClient(session)
    if not client._h("rwlx"):
        client.cdp_refresh_hidden(ws)

    # 0) 基线（真实已选）
    base_map, base_rows = fetch_choosed(client)
    print(f"[基线] 已选 {len(base_map)} 门:")
    for kch_id, kcmc in base_map.items():
        print(f"  {kcmc} ({kch_id[:8]}...)")

    # 1) 目标：大学实验室安全（jxbzls=1, 200/200 满员）
    data = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                       "data", "courses_10.json"), encoding="utf-8"))
    tgt = None
    for k, c in data["courses"].items():
        if c.get("kcmc") == "大学实验室安全":
            tgt = (k, c)
            break
    if not tgt:
        sys.exit("找不到靶子课程")
    kch_id, course = tgt
    print(f"[目标] {course['kch']} {course['kcmc']} (jxbzls={course['jxbzls']})")

    if kch_id in base_map:
        print("[!] 已选过该课程，换目标风险。中止。")
        return

    jxbs = client.get_jxbs(kch_id, TARGET_KKLXDM)
    print(f"[教学班] {len(jxbs)} 个")
    for jb in jxbs:
        print(f"  {jb.get('jxb_id','')[:8]}... 已选{jb.get('yxzrs')}/{jb.get('jxbrl')} "
              f"do_jxb={jb.get('do_jxb_id','')[:12]}...")
    target_jxb = jxbs[0]

    # 2) 提交（满员课，预期被业务拒绝）
    resp = client.submit(kch_id=kch_id, jxb_ids=[target_jxb["do_jxb_id"]],
                         kcmc=course["kcmc"], kklxdm=TARGET_KKLXDM,
                         cxbj="0", xxkbj="0", qz="0", jcxx_id="")
    print(f"[提交] -> {json.dumps(resp, ensure_ascii=False)}")

    # 3) 后检
    time.sleep(1)
    after_map, _ = fetch_choosed(client)
    print(f"[后检] 已选 {len(after_map)} 门")
    removed = set(base_map) - set(after_map)
    added = set(after_map) - set(base_map)
    print(f"[对比] 减少: {len(removed)} | 新增: {len(added)}")
    for k in removed:
        print(f"  - 被移除!!! {base_map[k]}")
    for k in added:
        print(f"  + 新增 {after_map[k]} (kch_id={k})")


if __name__ == "__main__":
    main()