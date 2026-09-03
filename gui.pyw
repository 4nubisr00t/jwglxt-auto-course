# -*- coding: utf-8 -*-
"""
JWGLXT Auto Course - 教务选课自动化 GUI
========================================
双击运行（.pyw 无控制台窗口）。依赖: pip install pywebview requests websocket-client
用法:
  python gui.pyw          # 启动窗口
  python gui.pyw --test   # 无窗口模式：仅测试后端逻辑（用于无显示环境）
"""
import json
import os
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import grab
from jw_cdp_client import (get_cdp_ws_url, cdp_get_cookies, build_session,
                           check_alive, JWClient, JW_BASE, JW_HOST)

HTML = """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<style>
  :root {
    --bg: #0b0b0d; --card: #141419; --card2: #1a1a21;
    --line: #23232c; --text: #e8e8ea; --dim: #8a8a93;
    --accent: #ff2b2b; --ok: #38d489; --warn: #ffb647; --err: #ff5252;
    --mono: "Cascadia Mono", Consolas, "JetBrains Mono", monospace;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { background: var(--bg); color: var(--text);
         font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
         display: flex; height: 100vh; overflow: hidden; }
  /* ---------- header ---------- */
  .header { position: fixed; top: 0; left: 0; right: 0; height: 52px;
            background: linear-gradient(90deg, #101014, #141419);
            border-bottom: 1px solid var(--line); display: flex;
            align-items: center; padding: 0 16px; z-index: 10; }
  .logo { width: 26px; height: 26px; background: var(--accent);
          clip-path: polygon(0 0, 100% 0, 100% 25%, 0 25%, 0 50%, 100% 50%,
          100% 75%, 0 75%, 0 100%, 100% 100%, 100% 88%, 0 88%);
          margin-right: 12px; filter: drop-shadow(0 0 6px #ff2b2b55); }
  .title { font-weight: 700; letter-spacing: 1px; font-size: 15px; }
  .title span { color: var(--accent); }
  .sub { color: var(--dim); font-size: 11px; margin-left: 10px; }
  .status { margin-left: auto; display: flex; align-items: center; gap: 6px;
            font-size: 12px; color: var(--dim); }
  .dot { width: 9px; height: 9px; border-radius: 50%; background: #555;
         transition: all .3s; }
  .dot.on { background: var(--ok); box-shadow: 0 0 8px var(--ok); animation: pulse 1.6s infinite; }
  .dot.busy { background: var(--warn); box-shadow: 0 0 8px var(--warn); animation: pulse .8s infinite; }
  .dot.err { background: var(--err); box-shadow: 0 0 8px var(--err); }
  @keyframes pulse { 50% { opacity: .35; } }
  /* ---------- layout ---------- */
  .left { width: 340px; padding: 68px 14px 14px; overflow-y: auto;
          border-right: 1px solid var(--line); }
  .right { flex: 1; padding: 68px 14px 14px; display: flex; flex-direction: column; }
  .card { background: var(--card); border: 1px solid var(--line);
          border-radius: 10px; padding: 12px; margin-bottom: 12px; }
  .card h3 { font-size: 12px; color: var(--dim); text-transform: uppercase;
             letter-spacing: 1.5px; margin-bottom: 10px;
             display: flex; align-items: center; gap: 6px; }
  .card h3::before { content: ""; width: 3px; height: 12px; background: var(--accent); }
  /* ---------- form ---------- */
  label.f { display: block; font-size: 12px; color: var(--dim); margin: 8px 0 4px; }
  input[type=text], textarea, input[type=number] {
    width: 100%; background: var(--card2); border: 1px solid var(--line);
    color: var(--text); border-radius: 6px; padding: 8px 10px;
    font-family: var(--mono); font-size: 13px; outline: none;
    transition: border .2s; }
  textarea { height: 58px; resize: vertical; line-height: 1.5; }
  input:focus, textarea:focus { border-color: var(--accent); }
  .row { display: flex; gap: 8px; }
  .row > div { flex: 1; }
  .chips { display: flex; gap: 6px; margin-top: 4px; flex-wrap: wrap; }
  .chip { padding: 5px 12px; border-radius: 20px; border: 1px solid var(--line);
          font-size: 12px; cursor: pointer; user-select: none; transition: all .2s;
          background: var(--card2); color: var(--dim); }
  .chip.on { background: #ff2b2b22; border-color: var(--accent); color: var(--accent); }
  .sw { display: flex; align-items: center; justify-content: space-between;
        padding: 7px 0; font-size: 13px; color: var(--text); cursor: pointer; }
  .sw input { display: none; }
  .sw .track { width: 38px; height: 20px; border-radius: 12px; background: #2a2a33;
               position: relative; transition: background .2s; }
  .sw .track::after { content: ""; position: absolute; top: 2px; left: 2px;
                      width: 16px; height: 16px; border-radius: 50%;
                      background: #777; transition: all .2s; }
  .sw input:checked + .track { background: var(--accent); }
  .sw input:checked + .track::after { left: 20px; background: #fff; }
  /* ---------- buttons ---------- */
  .btn { width: 100%; padding: 10px; border: none; border-radius: 8px;
         font-size: 13px; font-weight: 600; cursor: pointer; transition: all .15s;
         background: var(--card2); color: var(--text); border: 1px solid var(--line); }
  .btn:hover { border-color: var(--accent); color: var(--accent); }
  .btn.go { background: var(--accent); color: #fff; border: none; font-size: 14px;
            letter-spacing: 2px; margin-top: 10px; }
  .btn.go:hover { background: #ff4747; box-shadow: 0 0 14px #ff2b2b66; }
  .btn.go:disabled { background: #553; color: #997; cursor: not-allowed; box-shadow: none; }
  .btn.stop { background: transparent; color: var(--err); border-color: var(--err);
              margin-top: 6px; }
  .btns { display: flex; gap: 8px; }
  .btns .btn { flex: 1; }
  /* ---------- log ---------- */
  .log { flex: 1; background: #0e0e12; border: 1px solid var(--line);
         border-radius: 10px; padding: 10px; overflow-y: auto;
         font-family: var(--mono); font-size: 12px; line-height: 1.7; }
  .log .t { color: #555; }
  .log .info { color: var(--dim); }
  .log .ok { color: var(--ok); }
  .log .warn { color: var(--warn); }
  .log .err { color: var(--err); }
  .log .star { color: var(--accent); font-weight: 700; }
</style>
</head>
<body>
<div class="header">
  <div class="logo"></div>
  <div class="title">JWGLXT <span>AUTO</span></div>
  <div class="sub">正方教务选课自动化</div>
  <div class="status"><span id="stText">未连接</span><div class="dot" id="stDot"></div></div>
</div>

<div class="left">
  <div class="card">
    <h3>会话</h3>
    <div class="btns">
      <button class="btn" id="btnConnect" onclick="api.doConnect()">连接浏览器</button>
      <button class="btn" id="btnCrawl" onclick="api.doCrawl()" disabled>抓全表</button>
    </div>
    <div class="btns" style="margin-top:6px">
      <button class="btn" id="btnCheck" onclick="api.doCheck()" disabled>链路自检</button>
      <button class="btn" id="btnVerify" onclick="api.doVerify()" disabled>CDP 验证</button>
    </div>
  </div>

  <div class="card">
    <h3>目标课程</h3>
    <label class="f">关键词（空格分隔多个）</label>
    <textarea id="kw" placeholder="例如: 敦煌 光影 算法"></textarea>
    <label class="f">课程类别</label>
    <div class="chips">
      <div class="chip on" data-k="10" onclick="api.toggleChip(this)">通识选修</div>
      <div class="chip on" data-k="11" onclick="api.toggleChip(this)">特殊课程</div>
      <div class="chip" data-k="01" onclick="api.toggleChip(this)">主修(不推荐)</div>
    </div>
  </div>

  <div class="card">
    <h3>参数</h3>
    <div class="row">
      <div><label class="f">轮询间隔(s)</label>
        <input type="number" id="interval" value="1.5" min="0.3" step="0.1"></div>
      <div><label class="f">总超时(s)</label>
        <input type="number" id="timeout" value="1800" min="60" step="60"></div>
    </div>
    <label class="sw"><span>预演模式 (只匹配不出手)</span><input type="checkbox" id="dry" checked><div class="track"></div></label>
    <label class="sw"><span>尝试组合实践班</span><input type="checkbox" id="cpx"><div class="track"></div></label>
  </div>

  <button class="btn go" id="btnStart" onclick="api.doStart()" disabled>开 始</button>
  <button class="btn stop" id="btnStop" onclick="api.doStop()" style="display:none">停 止</button>
</div>

<div class="right">
  <div class="log" id="log"><span class="t">[--:--:--]</span> <span class="info">等待操作。先「连接浏览器」，再「抓全表」，最后设置关键词开始。</span></div>
</div>

<script>
  const logEl = document.getElementById("log");
  function __log(txt, lv) {
    const d = new Date();
    const ts = d.toTimeString().slice(0, 8);
    const div = document.createElement("div");
    div.innerHTML = `<span class="t">[${ts}]</span> <span class="${lv||'info'}">${
      txt.replace(/&/g,'&amp;').replace(/</g,'&lt;')}</span>`;
    logEl.appendChild(div);
    logEl.scrollTop = logEl.scrollHeight;
  }
  function __status(txt, cls) {
    document.getElementById("stText").textContent = txt;
    document.getElementById("stDot").className = "dot " + (cls || "");
  }
  const api = {
    toggleChip(el) { el.classList.toggle("on"); },
    async doConnect() { __status("连接中", "busy"); await window.pywebview.api.connect(); },
    async doCrawl()   { await window.pywebview.api.crawl(); },
    async doCheck()   { await window.pywebview.api.selfcheck(); },
    async doVerify()  { await window.pywebview.api.verify(); },
    async doStart()   { await window.pywebview.api.start(); },
    async doStop()    { await window.pywebview.api.stop(); },
  };
  window.__log = __log;
  window.__status = __status;
  window.api = api;
</script>
</body>
</html>"""


class Api:
    """pywebview 暴露给前端的方法。"""

    def __init__(self):
        self.client = None
        self.thread = None
        self.stop_evt = None

    # -- 前端日志/状态推送（可跨线程调用） --
    def log(self, text, level="info"):
        win = webview.windows[0] if webview.windows else None
        if win is None:
            print(f"[log] {text}")
            return
        try:
            win.evaluate_js(f"window.__log({json.dumps(text, ensure_ascii=False)}, "
                            f"{json.dumps(level)})")
        except Exception:
            pass

    def status(self, text, cls=""):
        win = webview.windows[0] if webview.windows else None
        if win is None:
            return
        try:
            win.evaluate_js(f"window.__status({json.dumps(text)}, {json.dumps(cls)})")
        except Exception:
            pass

    def _set_btn(self, btn_id, disabled, hidden=False):
        win = webview.windows[0] if webview.windows else None
        if win is None:
            return
        disp = "none" if hidden else ""
        win.evaluate_js(
            f"document.getElementById('{btn_id}').disabled={json.dumps(bool(disabled))};"
            f"document.getElementById('{btn_id}').style.display={json.dumps(disp)};")

    # -- 会话 --
    def connect(self):
        try:
            self.log("CDP cookie 注入 → 会话构建 → 页面上下文解析...")
            cookies = cdp_get_cookies(get_cdp_ws_url())
            session = build_session(cookies)
            if not check_alive(session):
                self.log("会话失效：请确认教务已登录且页面打开", "err")
                self.status("会话失效", "err")
                return {"ok": False, "msg": "会话失效"}
            self.client = JWClient(session)
            if not self.client._h("rwlx"):
                self.client.cdp_refresh_hidden(get_cdp_ws_url())
            if not self.client._h("rwlx"):
                self.log("提示: 未取到选课参数，请确认浏览器里打开了选课页面 "
                         f"({JW_BASE}/xsxk/zzxkyzb_cxZzxkYzbIndex.html)", "warn")
            tabs = list(self.client.tabs)
            self.log(f"连接成功: tabs={tabs} rwlx={self.client._h('rwlx')} "
                     f"xklc={self.client._h('xklc')}", "ok")
            self.status("已连接", "on")
            self._set_btn("btnConnect", True)
            self._set_btn("btnCrawl", False)
            self._set_btn("btnCheck", False)
            self._set_btn("btnVerify", False)
            self._set_btn("btnStart", False)
            return {"ok": True}
        except Exception as e:
            self.log(f"连接失败: {e}", "err")
            self.status("连接失败", "err")
            return {"ok": False, "msg": str(e)}

    # -- 全表 --
    def crawl(self):
        if not self.client:
            return self.connect()
        try:
            self.log("抓取课程全表...")
            snap = grab.fetch_full_snapshot(self.client, ["10", "11"], self.log)
            self.log(f"全表完成: {len(snap)} 门课程。可用关键词搜索。", "ok")
            return {"ok": True, "count": len(snap)}
        except Exception as e:
            self.log(f"抓取失败: {e}", "err")
            return {"ok": False, "msg": str(e)}

    # -- 链路自检 --
    def selfcheck(self):
        try:
            rows = self.client.get_choosed()
            self.log(f"链路自检: 已选 {len(rows)} 门课程", "ok")
            for r in rows[:8]:
                self.log(f"  已选: {r.get('kcmc')}", "info")
            if len(rows) > 8:
                self.log(f"  ... 等 {len(rows) - 8} 门", "info")
            return {"ok": True, "count": len(rows)}
        except Exception as e:
            self.log(f"自检失败: {e}", "err")
            return {"ok": False, "msg": str(e)}

    # -- CDP verify --
    def verify(self):
        try:
            cookies = cdp_get_cookies(get_cdp_ws_url())
            jw = [c for c in cookies if JW_HOST in (c.get("domain") or "")]
            self.log(f"CDP 验证: 共 {len(cookies)} cookie, 教务域 {len(jw)} 个", "ok")
            return {"ok": True, "total": len(cookies), "jw": len(jw)}
        except Exception as e:
            self.log(f"CDP 验证失败: {e}", "err")
            return {"ok": False, "msg": str(e)}

    # -- 抢课 --
    def _grab_opts(self):
        kw = self._js_val("kw")
        if not kw.strip():
            self.log("请先输入课程关键词", "err")
            return None
        chips = self._js_val("chipsOn", True)
        kklxdms = chips.split(",") if chips else ["10"]
        return {
            "keywords": kw.split(),
            "kklxdms": [k for k in kklxdms if k],
            "interval": float(self._js_val("interval") or 1.5),
            "timeout": int(self._js_val("timeout") or 1800),
            "dry_run": self._js_bool("dry"),
            "try_complex": self._js_bool("cpx"),
        }

    def _js_val(self, el_id, multi=False):
        win = webview.windows[0] if webview.windows else None
        if win is None:
            return ""
        try:
            if multi:
                expr = (f"Array.from(document.querySelectorAll('.chip.on'))"
                        f".map(e=>e.dataset.k).join(',')")
            else:
                expr = f"document.getElementById('{el_id}').value"
            return win.evaluate_js(expr)
        except Exception:
            return ""

    def _js_bool(self, el_id):
        win = webview.windows[0] if webview.windows else None
        if win is None:
            return False
        try:
            return bool(win.evaluate_js(
                f"document.getElementById('{el_id}').checked"))
        except Exception:
            return False

    def start(self):
        if self.thread and self.thread.is_alive():
            self.log("已有任务在运行", "warn")
            return {"ok": False, "msg": "busy"}
        opts = self._grab_opts()
        if opts is None:
            return {"ok": False, "msg": "no keywords"}
        self.stop_evt = threading.Event()
        self.thread = threading.Thread(target=self._worker, args=(opts,),
                                       daemon=True)
        self._set_btn("btnStart", True)
        self._set_btn("btnStop", False, hidden=False)
        self.status("运行中", "busy")
        self.thread.start()
        return {"ok": True}

    def _worker(self, opts):
        try:
            self.log(f"启动: 关键词 {opts['keywords']} 类别 {opts['kklxdms']} "
                     f"间隔 {opts['interval']}s" + (" [预演]" if opts["dry_run"] else ""))
            grab.run_grab(opts["keywords"], kklxdms=opts["kklxdms"],
                          interval=opts["interval"], timeout=opts["timeout"],
                          dry_run=opts["dry_run"], try_complex=opts["try_complex"],
                          log=self.log, stop_event=self.stop_evt)
        except Exception as e:
            self.log(f"任务异常: {e}", "err")
        finally:
            self.status("已连接", "on")
            self._set_btn("btnStart", False)
            self._set_btn("btnStop", True, hidden=True)
            self.log("任务结束", "info")

    def stop(self):
        if self.stop_evt:
            self.stop_evt.set()
            self.log("停止信号已发送，将在本轮结束后退出", "warn")
        return {"ok": True}


def main():
    api = Api()
    webview.create_window(
        "JWGLXT Auto Course",
        html=HTML,
        js_api=api,
        width=1020, height=720,
        min_size=(860, 600),
        background_color="#0b0b0d",
    )
    webview.start()


if __name__ == "__main__":
    try:
        import webview
    except ImportError:
        print("缺少 pywebview: pip install pywebview")
        sys.exit(1)
    if "--test" in sys.argv:
        # 无窗口模式：验证后端链路（无显示环境用，只读请求）
        print("[headless] 验证初始化链路...")
        client, ws = grab.init_client()
        print(f"[headless] tabs={list(client.tabs)} rwlx={client._h('rwlx')}")
        rows, _ = client.search_courses("10", page=1, page_size=3)
        print(f"[headless] 搜索 OK: {len(rows)} 行")
        ch = client.get_choosed()
        print(f"[headless] 已选 OK: {len(ch)} 门")
        print("[headless] 全部通过")
        sys.exit(0)
    main()