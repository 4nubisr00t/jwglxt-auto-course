# -*- coding: utf-8 -*-
"""
提交链路测试（只测到服务端业务响应，不改变任何选课状态）
==========================================================
策略：选一门 100% 满员的通识课（jxbzls=1 单班）做靶子，
选课季已过/满员 → 服务端必然业务拒绝。只要响应是业务层
（flag 语义，而非认证/参数错误），提交链路即验证通过。

红线：不调用 withdraw，不碰已选课程。
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jw_cdp_client import (get_cdp_ws_url, cdp_get_cookies, build_session,
                           check_alive, JWClient)

# 靶子课程：大学实验室安全（jxbzls=1, 200/200 满员，全表数据确认过）
TARGET_KCH_ID = None   # 动态取
TARGET_KKLXDM = "10"


def load_target():
    import json
    d = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "data", "courses_10.json"), encoding="utf-8"))
    for k, c in d["courses"].items():
        if c.get("kcmc") == "大学实验室安全" and c.get("jxbzls") == "1":
            return k, c
    return None, None


def main():
    ws = get_cdp_ws_url()
    cookies = cdp_get_cookies(ws)
    session = build_session(cookies)
    if not check_alive(session):
        sys.exit("会话失效")
    client = JWClient(session)
    if not client._h("rwlx"):
        client.cdp_refresh_hidden(ws)

    kch_id, course = load_target()
    if not kch_id:
        sys.exit("数据文件里没找到靶子课程")
    print(f"[靶子] {course['kch']} {course['kcmc']} 班数={len(course['classes'])}")

    # 1) 实时拿 do_jxb_id（动态，现取现用）
    jxbs = client.get_jxbs(kch_id, TARGET_KKLXDM)
    print(f"[get_jxbs] {len(jxbs)} 个班")
    target_jxb = None
    for jb in jxbs:
        yx, rl = int(jb.get("yxzrs") or 0), int(jb.get("jxbrl") or 0)
        print(f"  {jb.get('jxb_id','')[:8]}... 余量={rl-yx}/{rl} sksj={jb.get('sksj')} "
              f"do_jxb={jb.get('do_jxb_id','')[:12]}...")
        if rl > 0 and rl - yx <= 0:      # 容量>0 且已满：理想靶子
            target_jxb = jb
    if not target_jxb:
        print("[!] 没有找到已满班级，选第一个")
        target_jxb = jxbs[0]

    # 2) 提交（预期被服务端业务拒绝）
    print()
    print(f"[提交] kch_id={kch_id} jxb_ids={target_jxb['do_jxb_id'][:16]}... "
          f"后期 {time.strftime('%H:%M:%S')}")
    t0 = time.time()
    resp = client.submit(
        kch_id=kch_id,
        jxb_ids=[target_jxb["do_jxb_id"]],
        kcmc=course["kcmc"],
        kklxdm=TARGET_KKLXDM,
        cxbj=course["classes"][0].get("cxbj", "0"),
        xxkbj="0",
        qz="0",
        jcxx_id="",
    )
    dt = time.time() - t0
    print(f"[响应] 耗时 {dt*1000:.0f}ms")
    import json as _json
    print(_json.dumps(resp, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()