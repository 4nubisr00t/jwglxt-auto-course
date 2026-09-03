#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
教务系统选课接口自动化客户端
=============================
CDP 自动拉 cookie + 直打接口。

方案 C 实现：
  1. 连 Chrome DevTools 协议 (CDP) 拉取浏览器里真实会话的 cookies
  2. 灌入 requests.Session，模拟浏览器请求头
  3. 封装选课接口：tab 解析 / 搜索 / 教学班查询 / 提交 / 退课

前置条件：
  - Chrome 已带 --remote-debugging-port=9222 启动（见 README / check_debug() 提示）
  - pip install requests websocket-client
"""
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

import requests
import websocket

DEBUG_HOST = "127.0.0.1"
DEBUG_PORT = 9222
JW_HOST = "jw.xtu.edu.cn"          # 教务系统域名（按需修改）
JW_BASE = f"https://{JW_HOST}/jwglxt"
DOMAIN_FILTER = JW_HOST            # 只带教务域 cookie
JW_INDEX = (f"{JW_BASE}/xsxk/zzxkyzb_cxZzxkYzbIndex.html?"
            "gnmkdm=N253512&layout=default")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36")


# ---------------------------------------------------------------- CDP 部分

CDP_PORT_FILE = os.path.join(
    os.environ.get("USERPROFILE") or os.path.expanduser("~"),
    "AppData", "Local", "Google", "Chrome", "User Data", "DevToolsActivePort",
)

# 托管 Chrome 实例的独立 profile（与用户日常 Chrome 隔离）
MANAGED_PROFILE = os.path.join(
    os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"),
    "jwglxt-auto", "chrome-profile",
)


def find_chrome() -> str:
    """定位 chrome.exe（常见安装路径）。"""
    cands = [
        os.environ.get("PROGRAMFILES", "") + r"\Google\Chrome\Application\chrome.exe",
        os.environ.get("PROGRAMFILES(X86)", "") + r"\Google\Chrome\Application\chrome.exe",
        os.environ.get("LOCALAPPDATA", "") + r"\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    ]
    for c in cands:
        if c and os.path.isfile(c):
            return c
    return None


def wait_devtools(profile_dir: str, timeout: float = 25.0):
    """轮询 profile 目录的 DevToolsActivePort，返回 ws 地址。"""
    port_file = os.path.join(profile_dir, "DevToolsActivePort")
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with open(port_file, "r", encoding="utf-8") as f:
                lines = [l.strip() for l in f if l.strip()]
            if len(lines) >= 2:
                return f"ws://{DEBUG_HOST}:{lines[0]}{lines[1]}"
        except Exception:
            pass
        time.sleep(0.4)
    return None


def spawn_chrome(url: str = None, profile_dir: str = MANAGED_PROFILE):
    """启动托管 Chrome（独立 profile + 随机调试端口），返回 ws 地址。

    - 若该 profile 已有实例运行，直接复用（登录态保留）
    - 不影响用户日常 Chrome
    """
    chrome = find_chrome()
    if not chrome:
        raise RuntimeError("未找到 Chrome，请先安装")
    os.makedirs(profile_dir, exist_ok=True)
    ws_url = wait_devtools(profile_dir, timeout=3)
    if ws_url:                      # 已在运行，复用
        return ws_url
    cmd = [chrome,
           f"--user-data-dir={profile_dir}",
           "--remote-debugging-port=0",   # 随机端口，写进 DevToolsActivePort
           "--no-first-run",
           "--no-default-browser-check",
           "--restore-last-session=false"]
    if url:
        cmd.append(url)
    subprocess.Popen(cmd)
    ws_url = wait_devtools(profile_dir, timeout=30)
    if not ws_url:
        raise RuntimeError("Chrome 启动超时（30s）")
    return ws_url


def get_cdp_ws_url() -> str:
    """返回 Chrome 的 browser WebSocket 端点。

    优先读 DevToolsActivePort 文件（HTTP 发现端点可能不可用，文件方式更可靠）；
    找不到文件时回退 HTTP /json/version。
    """
    try:
        with open(CDP_PORT_FILE, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]
        port, ws_path = lines[0], lines[1]
        return f"ws://{DEBUG_HOST}:{port}{ws_path}"
    except Exception:
        pass
    # fallback: 标准发现端点
    url = f"http://{DEBUG_HOST}:{DEBUG_PORT}/json/version"
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # 防止代理劫持 127.0.0.1
    try:
        with opener.open(url, timeout=3) as r:
            data = json.loads(r.read().decode("utf-8"))
        ws = data.get("webSocketDebuggerUrl")
        if not ws:
            raise RuntimeError("9222 有响应但不是 DevTools 端点（可能被别的程序占用）")
        return ws
    except Exception as e:
        raise RuntimeError(
            f"Chrome DevTools 连不上 ({e})。\n"
            "检查 DevToolsActivePort 文件是否存在，或 Chrome 是否带"
            " --remote-debugging-port=9222 启动（需完全退出后重开）"
        ) from e


def cdp_get_cookies(ws_url: str, timeout: int = 10, retries: int = 5) -> list:
    """CDP Storage.getCookies 返回浏览器全部 cookie。

    实现要点（兼容常见 Chrome 配置）：
      - 握手使用 suppress_origin=True，规避 ws 握手的来源校验
      - Storage.getCookies 是 browser 级命令，浏览器级连接可直接调用
      - browser 端点同一时间仅放行一个活跃客户端，连接竞争时自动重试
    """
    last_err = None
    for _ in range(retries):
        try:
            ws = websocket.create_connection(ws_url, timeout=timeout,
                                             suppress_origin=True)
            try:
                ws.send(json.dumps({"id": 1, "method": "Storage.getCookies"}))
                while True:
                    msg = json.loads(ws.recv())
                    if msg.get("id") == 1:
                        if "error" in msg:
                            raise RuntimeError(f"CDP error: {msg['error']}")
                        return msg["result"]["cookies"]
            finally:
                ws.close()
        except Exception as e:
            last_err = e
            time.sleep(0.8)
    raise RuntimeError(f"CDP 连不上（重试 {retries} 次）: {last_err}")


# ---------------------------------------------------------------- 会话构建

def build_session(raw_cookies: list) -> requests.Session:
    """过滤教务域 cookie 灌入 Session。requests 会自动按 domain/path 匹配发送。"""
    s = requests.Session()
    s.headers.update({
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    })
    picked = [c for c in raw_cookies if DOMAIN_FILTER in (c.get("domain") or "")]
    if not picked:
        raise RuntimeError(f"浏览器里没有 {DOMAIN_FILTER} 域的 cookie，确认已登录教务系统")
    for c in picked:
        s.cookies.set(
            c["name"], c["value"],
            domain=(c.get("domain") or "").lstrip("."),
            path=c.get("path") or "/",
        )
    n = len(picked)
    names = ",".join(c["name"] for c in picked[:6])
    print(f"[+] 注入 {n} 个 cookie: {names}")
    return s


def check_alive(s: requests.Session) -> bool:
    """探测会话是否存活：能拿到选课首页的 tab 结构就算活着。"""
    r = s.get(JW_INDEX, timeout=10)
    html = r.text
    if "queryCourse" in html and ("displayBox" in html or "nav_tab" in html):
        return True
    print(f"[!] 会话疑似失效，响应长度 {len(html)}，含 'queryCourse': {'queryCourse' in html}")
    return False


# ---------------------------------------------------------------- 接口封装

class JWClient:
    """基于已认证 Session 的教务直打客户端。"""

    def __init__(self, session: requests.Session):
        self.s = session
        self.base = JW_BASE
        self.gnmkdm = "N253512"   # 功能号：选课接口权限上下文，缺了会"无操作权限"
        self.index_url = JW_INDEX
        # 服务端校验来源：referer/origin 必须与页面一致
        self.s.headers.update({
            "Referer": JW_INDEX,
            "Origin": f"https://{JW_HOST}",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
        })
        self.hidden = {}        # 全局 hidden（index 页）
        self.tabs = {}          # kklxdm -> {xkkz_id, njdm_id, zyh_id, xkkz_xh}
        self.tab_hidden = {}    # kklxdm -> hidden（display.html 里的 rwlx/xklc/rlkz...）
        self._load_page_context()

    def _u(self, path: str) -> str:
        """接口 URL：统一附加功能号参数。"""
        sep = "&" if "?" in path else "?"
        return f"{self.base}{path}{sep}gnmkdm={self.gnmkdm}"

    @staticmethod
    def _extract_hidden(html: str) -> dict:
        """宽松解析所有 input 的 id/value（属性顺序不敏感）。"""
        out = {}
        for tag in re.finditer(r"<input[^>]*>", html, re.I):
            t = tag.group(0)
            m_id = re.search(r"\bid\s*=\s*[\"']([^\"']+)[\"']", t)
            m_val = re.search(r"\bvalue\s*=\s*[\"']([^\"']*)[\"']", t)
            if m_id and m_val:
                out[m_id.group(1)] = m_val.group(1)
        return out

    # -- 启动时解析页面上下文：tab 参数 + hidden 值 ----------------
    def _load_page_context(self):
        html = self.s.get(JW_INDEX, timeout=10).text
        # 每个 tab 一套参数，格式：
        # queryCourse(this,'10','<xkkz_id>','<njdm_id>','<zyh_id>','<xkkz_xh>')
        # 参数顺序: kklxdm, xkkz_id, njdm_id, zyh_id, xkkz_xh
        pat = re.compile(
            r"queryCourse\(this,'(\d+)','([0-9A-F]{32})','(\d{4})','(\d+)','([0-9a-f]+)'\)"
        )
        for m in pat.finditer(html):
            kklxdm, xkkz_id, njdm_id, zyh_id, xkkz_xh = m.groups()
            self.tabs[kklxdm] = {
                "kklxdm": kklxdm, "xkkz_id": xkkz_id,
                "njdm_id": njdm_id, "zyh_id": zyh_id, "xkkz_xh": xkkz_xh,
            }
        self.hidden = self._extract_hidden(html)
        if not self.tabs:
            raise RuntimeError("页面未解析到选课 tab（可能不在选课季或未登录）")

        # rwlx/xklc/rlkz 等参数在 display.html 里（index 页没有），逐 tab 拉取
        # 注意：jQuery $.load(url, {data}) 用 POST，必须保持一致
        for kklxdm, t in self.tabs.items():
            try:
                r = self.s.post(
                    self._u("/xsxk/zzxkyzb_cxZzxkYzbDisplay.html"),
                    data={
                        "xkkz_id": t["xkkz_id"], "kklxdm": kklxdm,
                        "njdm_id": t["njdm_id"], "zyh_id": t["zyh_id"],
                        "xszxzt": self.hidden.get("xszxzt", ""),
                        "kspage": 0, "jspage": 0,
                    },
                    timeout=10,
                )
                h = self._extract_hidden(r.text)
            except Exception:
                h = {}
            if h:
                self.tab_hidden[kklxdm] = h
        got = self._h("rwlx")
        if not got:
            print("[!] display.html 未取到 rwlx（后端可能维护中），"
                  "可用 cdp_refresh_hidden() 从浏览器 DOM 读实时值")
        print(f"[+] tabs: {list(self.tabs)} | "
              f"rwlx={got or '?'} xklc={self._h('xklc') or '?'} "
              f"{self._h('xkxnm')}-{self._h('xkxqm')}")

    def _h(self, key: str, kklxdm: str = None) -> str:
        """取 hidden 参数：优先该 tab 的 display 参数，回退全局。"""
        if kklxdm and kklxdm in self.tab_hidden and key in self.tab_hidden[kklxdm]:
            return self.tab_hidden[kklxdm][key]
        return self.hidden.get(key, "")

    def cdp_refresh_hidden(self, ws_url: str) -> dict:
        """兜底：连浏览器 page 端点在 DOM 里读 hidden 实时值
        （浏览器里的选课页开着时，$('#rwlx').val() 一定存在，比解析 HTML 可靠）
        返回 {key: value}，并合并进 self.tab_hidden/self.hidden。
        """
        import websocket as _ws
        keys = ["rwlx", "xklc", "xkxnm", "xkxqm", "rlkz", "cdrlkz", "rlzlkz",
                "xszxzt", "txbsfrl", "xkzgbj", "bbhzxjxb", "zxgbxkkg",
                "xkly", "bklx_id", "xqh_id", "sfkkjyxdxnxq", "kzkcgs", "tykczgxdcs",
                # 学籍上下文（get_jxbs 等接口要求带上）
                "jg_id", "jg_id_1", "zyfx_id", "bh_id", "xbm", "xslbdm", "mzm",
                "xz", "ccdm", "xsbj", "sfkknj", "gnjkxdnj", "sfkkzy", "kzybkxy",
                "sfznkx", "zdkxms", "sfkxq", "sfkcfx", "kkbk", "kkbkdj", "bklbkcj",
                "sfkgbcx", "sfrxtgkcxd", "jxbzcxskg", "xkxskcgskg"]
        expr = ("(function(){var ids=" + json.dumps(keys) +
                ";var o={};for(var i=0;i<ids.length;i++){var e=document.getElementById(ids[i]);"
                "o[ids[i]]=e?e.value:'';}return o;})()")
        # 1) browser 端点: 找 page target 并 attach 拿 sessionId
        ws = _ws.create_connection(ws_url, timeout=10, suppress_origin=True)
        ws.send(json.dumps({"id": 1, "method": "Target.getTargets"}))
        targets = None
        while True:
            msg = json.loads(ws.recv())
            if msg.get("id") == 1:
                targets = msg["result"]["targetInfos"]
                break
        page = next((t for t in targets
                     if t.get("type") == "page" and JW_HOST in t.get("url", "")),
                    None)
        if not page:
            page = next((t for t in targets if t.get("type") == "page"), None)
        if not page:
            ws.close()
            raise RuntimeError("没找到 page target")
        ws.send(json.dumps({"id": 2, "method": "Target.attachToTarget",
                            "params": {"targetId": page["targetId"],
                                        "flatten": True}}))
        session_id = None
        while True:
            msg = json.loads(ws.recv())
            if msg.get("id") == 2:
                if "error" in msg:
                    ws.close()
                    raise RuntimeError(f"attach error: {msg['error']}")
                session_id = msg["result"]["sessionId"]
                break
        # 2) 通过 session 在页面上下文执行 evaluate（只读取 DOM 值）
        try:
            ws.send(json.dumps({"id": 3, "sessionId": session_id,
                                "method": "Runtime.evaluate",
                                "params": {"expression": expr,
                                            "returnByValue": True}}))
            while True:
                msg = json.loads(ws.recv())
                if msg.get("id") == 3:
                    if "error" in msg:
                        raise RuntimeError(f"evaluate error: {msg['error']}")
                    vals = msg["result"]["result"]["value"]
                    break
        finally:
            ws.close()
        self.hidden.update(vals)
        for t in self.tabs:
            self.tab_hidden.setdefault(t, {}).update(vals)
        print(f"[+] CDP DOM 读取: rwlx={vals.get('rwlx')} xklc={vals.get('xklc')}")
        return vals

    def _tab_params(self, kklxdm: str) -> dict:
        return self.tabs[kklxdm]

    # -- 搜索课程（PartDisplay 分页，keyword 匹配课程名/课程号） ----------
    def search_courses(self, kklxdm="10", keyword=None, page=1, page_size=10, **filters):
        """filters 可选: jg_id(开课学院) kclbdm(课程类别) kcgsdm(课程归属)
        sksj(星期) skjc(节次) yl(有无余量1/0) cxbj(重修) xf(学分)"""
        t = self._tab_params(kklxdm)
        params = {
            "rwlx": self._h("rwlx", kklxdm), "xklc": self._h("xklc", kklxdm),
            "xkly": self._h("xkly", kklxdm), "bklx_id": self._h("bklx_id", kklxdm),
            "sfkkjyxdxnxq": self._h("sfkkjyxdxnxq", kklxdm), "kzkcgs": self._h("kzkcgs", kklxdm),
            "xqh_id": self._h("xqh_id", kklxdm), "jg_id": "",
            "zyh_id": t["zyh_id"], "njdm_id": t["njdm_id"], "bh_id": "",
            "xbm": "", "xslbdm": "", "mzm": "", "xz": "", "ccdm": "", "xsbj": "",
            "sfkknj": "", "sfkkzy": "", "kzybkxy": "", "sfznkx": "", "zdkxms": "",
            "sfkxq": "", "sfkcfx": "", "kkbk": "", "kkbkdj": "", "bklbkcj": "",
            "sfkgbcx": "", "sfrxtgkcxd": "", "xkkz_xh": t["xkkz_xh"], "tykczgxdcs": "",
            "xkxnm": self._h("xkxnm", kklxdm), "xkxqm": self._h("xkxqm", kklxdm),
            "kklxdm": kklxdm, "bbhzxjxb": self._h("bbhzxjxb", kklxdm),
            "zxgbxkkg": self._h("zxgbxkkg", kklxdm), "xkkz_id": t["xkkz_id"],
            "rlkz": self._h("rlkz", kklxdm), "xkzgbj": self._h("xkzgbj", kklxdm),
            "kspage": (page - 1) * page_size + 1, "jspage": page * page_size,
        }
        params.update({k: v for k, v in filters.items() if v is not None})
        if keyword:
            params["jxbmc"] = keyword          # 搜索框输入映射到 jxbmc
        r = self.s.post(self._u("/xsxk/zzxkyzb_cxZzxkYzbPartDisplay.html"),
                        data=params, timeout=10)
        data = r.json()
        if data == 0 or (isinstance(data, dict) and data.get("flag") == "0"):
            raise RuntimeError(f"PartDisplay 拒绝: {data}")
        return data["tmpList"], data.get("sfxsjc")

    # -- 按课程查全部教学班（含 do_jxb_id / 容量 / 教师 / 理论实践） ------
    def get_jxbs(self, kch_id: str, kklxdm="10", cxbj="0", fxbj="0"):
        t = self._tab_params(kklxdm)
        params = {
            "xkxnm": self._h("xkxnm", kklxdm), "xkxqm": self._h("xkxqm", kklxdm),
            "kklxdm": kklxdm, "kch_id": kch_id, "xkkz_id": t["xkkz_id"],
            "njdm_id": t["njdm_id"], "zyh_id": t["zyh_id"],
            "rwlx": self._h("rwlx", kklxdm), "xklc": self._h("xklc", kklxdm),
            "xqh_id": self._h("xqh_id", kklxdm), "rlkz": self._h("rlkz", kklxdm),
            "cdrlkz": self._h("cdrlkz", kklxdm), "rlzlkz": self._h("rlzlkz", kklxdm),
            "cxbj": cxbj, "fxbj": fxbj, "bnbj": "",
            "xszxzt": self._h("xszxzt", kklxdm), "txbsfrl": self._h("txbsfrl", kklxdm),
            "zxgbxkkg": self._h("zxgbxkkg", kklxdm), "bbhzxjxb": self._h("bbhzxjxb", kklxdm),
            # 学籍上下文（对齐浏览器真实请求）
            "xkly": self._h("xkly", kklxdm), "bklx_id": self._h("bklx_id", kklxdm),
            "sfkkjyxdxnxq": self._h("sfkkjyxdxnxq", kklxdm), "kzkcgs": self._h("kzkcgs", kklxdm),
            "jg_id": self._h("jg_id_1", kklxdm) or self._h("jg_id", kklxdm),
            "zyfx_id": self._h("zyfx_id", kklxdm), "bh_id": self._h("bh_id", kklxdm),
            "xbm": self._h("xbm", kklxdm), "xslbdm": self._h("xslbdm", kklxdm),
            "mzm": self._h("mzm", kklxdm), "xz": self._h("xz", kklxdm),
            "ccdm": self._h("ccdm", kklxdm), "xsbj": self._h("xsbj", kklxdm),
            "sfkknj": self._h("sfkknj", kklxdm), "gnjkxdnj": self._h("gnjkxdnj", kklxdm),
            "sfkkzy": self._h("sfkkzy", kklxdm), "kzybkxy": self._h("kzybkxy", kklxdm),
            "sfznkx": self._h("sfznkx", kklxdm), "zdkxms": self._h("zdkxms", kklxdm),
            "sfkxq": self._h("sfkxq", kklxdm), "sfkcfx": self._h("sfkcfx", kklxdm),
            "kkbk": self._h("kkbk", kklxdm), "kkbkdj": self._h("kkbkdj", kklxdm),
            "bklbkcj": self._h("bklbkcj", kklxdm), "jxbzcxskg": self._h("jxbzcxskg", kklxdm),
            "xkxskcgskg": self._h("xkxskcgskg", kklxdm),
        }
        r = self.s.post(self._u("/xsxk/zzxkyzbjk_cxJxbWithKchZzxkYzb.html"),
                        data=params, timeout=10)
        return r.json()

    # -- 选课提交（单班 / 理论+实践多班：jxb_ids 逗号拼接） ---------------
    def submit(self, kch_id: str, jxb_ids: list, kcmc: str, kklxdm="10",
               cxbj="0", xxkbj="0", qz="0", jcxx_id=""):
        t = self._tab_params(kklxdm)
        rlkz = self._h("rlkz", kklxdm)
        cdrlkz = self._h("cdrlkz", kklxdm)
        rlzlkz = self._h("rlzlkz", kklxdm)
        sxbj = "1" if (rlkz == "1" or cdrlkz == "1" or rlzlkz == "1") else "0"
        params = {
            "jxb_ids": ",".join(jxb_ids), "kch_id": kch_id, "kcmc": kcmc,
            "rwlx": self._h("rwlx", kklxdm), "rlkz": rlkz, "cdrlkz": cdrlkz,
            "rlzlkz": rlzlkz, "sxbj": sxbj, "xxkbj": xxkbj, "qz": qz, "cxbj": cxbj,
            "xkkz_id": t["xkkz_id"], "njdm_id": t["njdm_id"], "zyh_id": t["zyh_id"],
            "kklxdm": kklxdm, "xklc": self._h("xklc", kklxdm),
            "xkxnm": self._h("xkxnm", kklxdm), "xkxqm": self._h("xkxqm", kklxdm),
            "jcxx_id": jcxx_id,
        }
        r = self.s.post(self._u("/xsxk/zzxkyzbjk_xkBcZyZzxkYzb.html"),
                        data=params, timeout=10)
        return r.json()

    # -- 已选课程（ChoosedDisplay POST，对齐浏览器真实请求） ----------
    def get_choosed(self) -> list:
        """返回已选课程列表 [{kch_id, kcmc, jxb_id, do_jxb_id, kklxdm, ...}]。
        抢课前调用，避免对已选课重复提交。"""
        params = {
            "jg_id": self._h("jg_id_1") or self._h("jg_id"),
            "zyh_id": self._h("zyh_id"),
            "njdm_id": self._h("njdm_id"),
            "zyfx_id": self._h("zyfx_id"),
            "bh_id": self._h("bh_id"),
            "xz": self._h("xz"),
            "ccdm": self._h("ccdm"),
            "xqh_id": self._h("xqh_id"),
            "xkxnm": self._h("xkxnm"),
            "xkxqm": self._h("xkxqm"),
            "xkly": self._h("xkly"),
        }
        r = self.s.post(self._u("/xsxk/zzxkyzb_cxZzxkYzbChoosedDisplay.html"),
                        data=params, timeout=10)
        return r.json()

    # -- 退课 ------------------------------------------------------------
    def withdraw(self, kch_id: str, jxb_ids: list):
        params = {
            "kch_id": kch_id,
            "jxb_ids": ",".join(jxb_ids),
            "xkxnm": self._h("xkxnm"),
            "xkxqm": self._h("xkxqm"),
            "txbsfrl": self._h("txbsfrl"),
        }
        r = self.s.post(self._u("/xsxk/zzxkyzb_tuikBcZzxkYzb.html"),
                        data=params, timeout=10)
        return r.text


# ---------------------------------------------------------------- 入口

def main():
    demo = "--demo" in sys.argv
    ws = get_cdp_ws_url()
    print(f"[+] CDP: {ws}")
    cookies = cdp_get_cookies(ws)
    session = build_session(cookies)
    if not check_alive(session):
        sys.exit("会话已失效：重新登录教务并刷新页面后再跑。")

    client = JWClient(session)   # 只读: 解析 tabs + hidden 参数
    if not client._h("rwlx"):
        client.cdp_refresh_hidden(ws)   # 后端维护时用浏览器 DOM 兜底

    if demo:
        # ---- 演示：搜索通识选修第一页 ----------------
        rows, _ = client.search_courses("10", page=1, page_size=5)
        print(f"[查询] 第一页 {len(rows)} 行")
        for row in rows:
            print(f"  {row.get('kch')} {row.get('kcmc')} xf={row.get('xf')} "
                  f"jxbzls={row.get('jxbzls')} 已选={row.get('yxzrs')}")
        # ---- 演示：按课程查教学班（do_jxb_id 的唯一来源） ----
        if rows:
            kch_id = rows[0]["kch_id"]
            jxbs = client.get_jxbs(kch_id, "10")
            print(f"[教学班] {rows[0]['kcmc']}: {len(jxbs)} 个班")
            for jb in jxbs:
                yx = int(jb.get('yxzrs') or 0)
                rl = int(jb.get('jxbrl') or 0)
                print(f"  {jb.get('jxb_id','')[:8]}... 类别={jb.get('kclbmc')} "
                      f"余量={rl - yx}/{rl} {jb.get('sksj')} {jb.get('jxdd')} "
                      f"教师={jb.get('jsxx').split('/')[1] if jb.get('jsxx') else '?'} "
                      f"do_jxb={jb.get('do_jxb_id','')[:12]}...")


if __name__ == "__main__":
    main()