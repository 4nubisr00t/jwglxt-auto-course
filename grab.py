#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
教务选课核心逻辑（CLI + GUI 共用）
======================================
用法:
  python grab.py "敦煌"                     # 匹配并进入抢课循环
  python grab.py "光影 敦煌" --kklxdm 11,10  # 多关键词 + 多类别
  python grab.py "算法" --dry-run            # 预演：只匹配查重，不提交

规则：只做加法（用户可退），绝不做减法。
"""
import argparse
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jw_cdp_client import (get_cdp_ws_url, cdp_get_cookies, build_session,
                           check_alive, JWClient)

BIG_PAGE = 100000          # 大分页一次拉全
SUCCESS_FLAGS = ("1", "3", "6")


def now():
    return time.strftime("%H:%M:%S")


def fetch_full_snapshot(client, kklxdms, log=print):
    """单次拉全表，返回 {kch_id: {kch, kcmc, jxbzls, xf, kklxdm, classes:[...]}}"""
    out = {}
    for kklxdm in kklxdms:
        rows, _ = client.search_courses(kklxdm, page=1, page_size=BIG_PAGE)
        for r in rows:
            c = out.setdefault(r["kch_id"], {
                "kch": r.get("kch"), "kcmc": r.get("kcmc"),
                "jxbzls": r.get("jxbzls"), "xf": r.get("xf"),
                "kklxdm": kklxdm,
                "classes": [],
            })
            c["classes"].append({
                "jxb_id": r.get("jxb_id"), "jxbmc": r.get("jxbmc"),
                "yxzrs": r.get("yxzrs"), "cxbj": r.get("cxbj"),
            })
        log(f"[{now()}] 类别 {kklxdm} 抓取完成: {len(rows)} 行")
    return out


def match_courses(snapshot, keywords):
    """关键词（空格分隔，任一命中）正则匹配课程名/课程号。"""
    pats = [re.compile(re.escape(kw)) for kw in keywords if kw]
    hits = []
    for kch_id, c in snapshot.items():
        if any(p.search(c["kcmc"]) or p.search(c["kch"] or "") for p in pats):
            hits.append((kch_id, c))
    return hits


def pick_class(client, kch_id, course, class_idx=None):
    """get_jxbs 现取教学班 + 依据类别选目标班。返回 (jxb, note)。"""
    jxbs = client.get_jxbs(kch_id, course["kklxdm"])
    if not jxbs:
        return None, "无教学班"
    if class_idx is not None:
        if 0 <= class_idx < len(jxbs):
            return jxbs[class_idx], f"指定第{class_idx + 1}班"
        return None, f"class-idx 越界({len(jxbs)}个班)"
    max_yx = max((int(jb.get("yxzrs") or 0) for jb in jxbs), default=0)

    def surplus(jb):
        yx = int(jb.get("yxzrs") or 0)
        rl = int(jb.get("jxbrl") or 0)
        if rl == 0:                       # 网课软上限
            return max_yx - yx, yx
        return rl - yx, yx

    best = sorted(jxbs, key=surplus, reverse=True)[0]
    yx, rl = int(best.get("yxzrs") or 0), int(best.get("jxbrl") or 0)
    note = f"余量={max(0, rl - yx) if rl else max(0, max_yx - yx)}/{rl or max_yx}"
    return best, note


def try_fetch_subclasses(client, jxb, kklxdm):
    """尝试拉取实践子班（jxbzls>1 组合）。窗口外返回错误页时 gracefully 失败。"""
    r = client.s.post(client._u("/xsxk/zzxkyzb_xkZyZzxkYzbZjxb.html"), data={
        "jxb_id": jxb["jxb_id"], "do_jxb_id": jxb.get("do_jxb_id", ""),
        "jxbzls": jxb.get("jxbzls", "2"),
        "rwlx": client._h("rwlx", kklxdm), "fxbj": "0", "cxbj": "0",
        "rlkz": client._h("rlkz", kklxdm), "cdrlkz": client._h("cdrlkz", kklxdm),
        "rlzlkz": client._h("rlzlkz", kklxdm), "zcongbj": "0", "syqz": "100",
    }, timeout=10)
    html = r.text
    if "出错啦" in html or len(html) < 500:
        return None
    subs = []
    for m in re.finditer(r"<li[^>]*>([\s\S]*?)</li>", html):
        seg = m.group(1)
        doj = re.search(r"name=['\"]select_do_jxb['\"][^>]*value=['\"]([^'\"]+)", seg)
        if doj and doj.group(1):
            subs.append({"do_jxb_id": doj.group(1)})
    return subs


def submit_course(client, course, jxb, sub_ids=None):
    jxb_ids = [jxb["do_jxb_id"]] + (sub_ids or [])
    return client.submit(
        kch_id=course["kch_id"], jxb_ids=jxb_ids, kcmc=course["kcmc"],
        kklxdm=course["kklxdm"], cxbj="0", xxkbj="0", qz="0", jcxx_id="",
    )


def init_client(log=print):
    """CDP cookie -> 会话 -> 页面上下文。返回 (client, ws)。"""
    ws = get_cdp_ws_url()
    cookies = cdp_get_cookies(ws)
    session = build_session(cookies)
    if not check_alive(session):
        raise RuntimeError("会话失效，请重新登录教务并刷新页面")
    client = JWClient(session)
    if not client._h("rwlx"):
        client.cdp_refresh_hidden(ws)
    return client, ws


def run_grab(keywords, kklxdms=("10", "11"), interval=1.5, timeout=1800,
             class_idx=None, try_complex=False, dry_run=False,
             log=print, stop_event=None):
    """完整抢课流程。可用 stop_event(threading.Event) 中途停止。"""
    log(f"[{now()}] 初始化会话...")
    client, _ = init_client(log)
    log(f"[{now()}] 拉取全表: 类别 {list(kklxdms)}")
    snapshot = fetch_full_snapshot(client, kklxdms, log)

    hits = match_courses(snapshot, keywords)
    if not hits:
        log(f"[{now()}] 没有匹配到任何课程")
        return "no-match"
    log(f"[{now()}] 匹配到 {len(hits)} 门:")
    for kch_id, c in hits:
        log(f"  {c['kch']} {c['kcmc']} (类别{c['kklxdm']} xf={c['xf']} "
            f"jxbzls={c['jxbzls']} 班数={len(c['classes'])})")

    choosed = client.get_choosed()
    choosed_ids = {row["kch_id"] for row in choosed}
    targets = []
    for kch_id, c in hits:
        if kch_id in choosed_ids:
            log(f"[{now()}] 跳过已选: {c['kcmc']}")
            continue
        if str(c.get("jxbzls", "1")) != "1" and not try_complex:
            log(f"[{now()}] 跳过实践班课程(--try-complex 可组合): {c['kcmc']}")
            continue
        targets.append({**c, "kch_id": kch_id})
    if not targets:
        log(f"[{now()}] 没有可抢的目标")
        return "no-target"
    log(f"[{now()}] 待抢目标 {len(targets)} 门")

    if dry_run:
        for t in targets:
            jxb, note = pick_class(client, t["kch_id"], t)
            if jxb:
                log(f"  [预演] {t['kcmc']}: jxb={jxb.get('jxb_id','')[:8]} "
                    f"do_jxb={jxb.get('do_jxb_id','')[:12]}... {note}")
        log(f"[{now()}] dry-run 结束，未提交任何请求")
        return "dry-run"

    deadline = time.time() + timeout
    pending = targets
    log(f"[{now()}] 进入抢课循环 (interval={interval}s, timeout={timeout}s)")
    while pending and time.time() < deadline:
        if stop_event is not None and stop_event.is_set():
            log(f"[{now()}] 收到停止信号")
            break
        for t in list(pending):
            if stop_event is not None and stop_event.is_set():
                break
            jxb, note = pick_class(client, t["kch_id"], t)
            if not jxb:
                log(f"[{now()}] {t['kcmc']}: {note}")
                continue
            sub_ids = None
            if str(t.get("jxbzls", "1")) != "1":
                subs = try_fetch_subclasses(client, jxb, t["kklxdm"])
                if not subs:
                    log(f"[{now()}] {t['kcmc']}: 实践子班拉取失败，跳过本轮")
                    continue
                sub_ids = [s["do_jxb_id"] for s in subs]
            resp = submit_course(client, t, jxb, sub_ids)
            flag = str(resp.get("flag"))
            msg = resp.get("msg", "")
            if flag in SUCCESS_FLAGS:
                log(f"[{now()}] ★ 成功: {t['kcmc']} ({msg})")
                pending.remove(t)
            elif flag == "-1":
                log(f"[{now()}] {t['kcmc']}: 容量不足 ({msg[:40]})")
            elif flag == "2":
                log(f"[{now()}] {t['kcmc']}: 时间冲突")
            elif "门次" in msg or "上限" in msg:
                log(f"[{now()}] {t['kcmc']}: 永久失败 ({msg})，移除")
                pending.remove(t)
            elif "只能选一个教学班" in msg:
                log(f"[{now()}] {t['kcmc']}: 已选过该课程，移除")
                pending.remove(t)
            elif "无操作权限" in msg:
                log(f"[{now()}] {t['kcmc']}: 权限异常，稍后重试")
            else:
                log(f"[{now()}] {t['kcmc']}: flag={flag} msg={msg[:60]}")
        time.sleep(interval)
    remaining = [t["kcmc"] for t in pending]
    log(f"[{now()}] 结束。剩余未成功: {remaining if remaining else '无'}")
    log("红线提醒：只做加法，退课请手动操作。")
    return "done" if not remaining else "timeout"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("keywords", nargs="+")
    ap.add_argument("--interval", type=float, default=1.5)
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--kklxdm", default="10,11")
    ap.add_argument("--class-idx", type=int)
    ap.add_argument("--try-complex", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    kklxdms = [s.strip() for s in args.kklxdm.split(",") if s.strip()]
    run_grab(args.keywords, kklxdms=kklxdms, interval=args.interval,
             timeout=args.timeout, class_idx=args.class_idx,
             try_complex=args.try_complex, dry_run=args.dry_run)


if __name__ == "__main__":
    main()