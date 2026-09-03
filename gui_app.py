# -*- coding: utf-8 -*-
"""
JWGLXT Auto Course - GUI (customtkinter)
=========================================
双击运行或 python gui_app.py。依赖: pip install customtkinter
逻辑层完全复用 grab.py，本文件只负责交互。
"""
import os
import queue
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import grab
from jw_cdp_client import (get_cdp_ws_url, cdp_get_cookies, build_session,
                           check_alive, JWClient, JW_BASE, JW_HOST)

try:
    import customtkinter as ctk
    ctk.set_appearance_mode("dark")
except Exception as e:  # 无显示环境/未安装时给出提示
    ctk = None

# 主题（红黑）
BG = "#0b0b0d"
CARD = "#141419"
CARD2 = "#1c1c23"
TEXT = "#e8e8ea"
DIM = "#8a8a93"
LINE = "#26262f"
ACCENT = "#ff2b2b"
OK = "#38d489"
WARN = "#ffb647"
ERR = "#ff5252"

LV_COLOR = {"info": DIM, "ok": OK, "warn": WARN, "err": ERR, "star": ACCENT}


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("JWGLXT Auto Course")
        self.geometry("1020x720")
        self.minsize(880, 600)
        self.configure(bg=BG)

        self.client = None
        self.worker = None
        self.stop_evt = None
        self.log_q = queue.Queue()
        self._running = False

        self._build()
        self.after(100, self._drain_log)

    # ---------------- UI ----------------
    def _card(self, parent, title):
        f = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=10,
                         border_width=1, border_color=LINE)
        f.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(f, text=title, font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=DIM).pack(anchor="w", padx=12, pady=(10, 2))
        return f

    def _btn(self, parent, text, cmd, color=None, height=34):
        fg = color or CARD2
        b = ctk.CTkButton(parent, text=text, command=cmd, height=height,
                          fg_color=fg, hover_color="#2a2a33",
                          border_width=0, corner_radius=8,
                          font=ctk.CTkFont(size=13))
        b.pack(fill="x", padx=12, pady=4)
        return b

    def _build(self):
        # 顶部
        head = ctk.CTkFrame(self, fg_color=CARD, corner_radius=0,
                            border_width=0, height=56)
        head.pack(fill="x", side="top")
        head.pack_propagate(False)
        ctk.CTkLabel(head, text="■", text_color=ACCENT,
                     font=ctk.CTkFont(size=20)).pack(side="left", padx=(16, 8))
        t = ctk.CTkLabel(head, text="JWGLXT AUTO",
                         font=ctk.CTkFont(size=16, weight="bold"))
        t.pack(side="left")
        ctk.CTkLabel(head, text="教务选课自动化", text_color=DIM,
                     font=ctk.CTkFont(size=11)).pack(side="left", padx=8)
        self.status_lbl = ctk.CTkLabel(head, text="●  未连接", text_color=DIM,
                                       font=ctk.CTkFont(size=12))
        self.status_lbl.pack(side="right", padx=16)

        body = ctk.CTkFrame(self, fg_color=BG, corner_radius=0, border_width=0)
        body.pack(fill="both", expand=True, padx=14, pady=12)

        # 左栏
        left = ctk.CTkFrame(body, fg_color=BG, width=330, corner_radius=0,
                            border_width=0)
        left.pack(side="left", fill="y", padx=(0, 12))
        left.pack_propagate(False)

        # 会话
        c1 = self._card(left, "会话")
        self.btn_conn = self._btn(c1, "连接浏览器", self.connect, ACCENT)
        self.btn_crawl = self._btn(c1, "抓取全表", self.crawl)
        self.btn_check = self._btn(c1, "链路自检", self.selfcheck)
        self.btn_verify = self._btn(c1, "CDP 验证", self.verify)

        # 目标
        c2 = self._card(left, "目标课程")
        ctk.CTkLabel(c2, text="关键词（空格分隔多个）", text_color=DIM,
                     font=ctk.CTkFont(size=11)).pack(anchor="w", padx=12, pady=(2, 2))
        self.kw = ctk.CTkEntry(c2, placeholder_text="例如: 敦煌 光影 算法",
                               height=36, fg_color=CARD2, border_color=LINE)
        self.kw.pack(fill="x", padx=12, pady=(0, 6))
        self.cat = {"10": True, "11": True, "01": False}
        self.cat_btns = {}
        row = ctk.CTkFrame(c2, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=(0, 6))
        for k, name in (("10", "通识选修"), ("11", "特殊课程"), ("01", "主修")):
            b = ctk.CTkButton(row, text=name, width=82, height=30,
                              fg_color=CARD2 if not self.cat[k] else "#3a1a1a",
                              text_color=TEXT if not self.cat[k] else ACCENT,
                              border_width=1, border_color=LINE,
                              hover_color="#2a2a33", corner_radius=15,
                              font=ctk.CTkFont(size=12),
                              command=lambda kk=k: self._toggle_cat(kk))
            b.pack(side="left", padx=(0, 6))
            self.cat_btns[k] = b

        # 参数
        c3 = self._card(left, "参数")
        pr = ctk.CTkFrame(c3, fg_color="transparent")
        pr.pack(fill="x", padx=12)
        ctk.CTkLabel(pr, text="轮询间隔(s)", text_color=DIM,
                     font=ctk.CTkFont(size=11)).pack(side="left")
        self.interval = ctk.CTkEntry(pr, width=60, height=30, fg_color=CARD2,
                                     border_color=LINE)
        self.interval.insert(0, "1.5")
        self.interval.pack(side="left", padx=(6, 18))
        ctk.CTkLabel(pr, text="超时(s)", text_color=DIM,
                     font=ctk.CTkFont(size=11)).pack(side="left")
        self.timeout = ctk.CTkEntry(pr, width=80, height=30, fg_color=CARD2,
                                    border_color=LINE)
        self.timeout.insert(0, "1800")
        self.timeout.pack(side="left", padx=6)

        self.dry_sw = ctk.CTkSwitch(c3, text="预演模式（只匹配不出手）",
                                    progress_color=ACCENT,
                                    font=ctk.CTkFont(size=12))
        self.dry_sw.pack(anchor="w", padx=12, pady=(8, 2))
        self.dry_sw.select()
        self.cpx_sw = ctk.CTkSwitch(c3, text="尝试组合实践班",
                                    progress_color=ACCENT,
                                    font=ctk.CTkFont(size=12))
        self.cpx_sw.pack(anchor="w", padx=12, pady=(0, 8))

        # 动作
        self.btn_start = ctk.CTkButton(left, text="开  始", height=44,
                                       fg_color=ACCENT, hover_color="#ff4747",
                                       corner_radius=8,
                                       font=ctk.CTkFont(size=15, weight="bold"),
                                       command=self.start)
        self.btn_start.pack(fill="x", padx=12, pady=(4, 4))
        self.btn_start.configure(state="disabled")
        self.btn_stop = ctk.CTkButton(left, text="停  止", height=36,
                                      fg_color="transparent",
                                      hover_color="#3a1a1a", border_width=1,
                                      border_color=ERR, text_color=ERR,
                                      corner_radius=8,
                                      font=ctk.CTkFont(size=13),
                                      command=self.stop)
        self.btn_stop.pack(fill="x", padx=12)
        self.btn_stop.configure(state="disabled")

        # 右栏日志
        self.log_box = ctk.CTkTextbox(body, fg_color="#0e0e12",
                                      border_color=LINE, border_width=1,
                                      corner_radius=10, wrap="none",
                                      font=ctk.CTkFont(family="Cascadia Mono",
                                                       size=12))
        self.log_box.pack(side="left", fill="both", expand=True)
        for tag, color in LV_COLOR.items():
            self.log_box.tag_config(tag, foreground=color)
        self.log_box.tag_config("t", foreground="#555555")
        self._log("等待操作。先「连接浏览器」，再「抓全表」，最后输入关键词开始。")

    def _toggle_cat(self, k):
        self.cat[k] = not self.cat[k]
        on = self.cat[k]
        self.cat_btns[k].configure(fg_color="#3a1a1a" if on else CARD2,
                                   text_color=ACCENT if on else TEXT)

    # ---------------- 日志 ----------------
    def _log(self, text, level="info"):
        self.log_q.put((text, level))

    def _drain_log(self):
        try:
            while True:
                text, level = self.log_q.get_nowait()
                ts = time.strftime("%H:%M:%S")
                self.log_box.insert("end", f"[{ts}] ", "t")
                self.log_box.insert("end", text + "\n", level)
                self.log_box.see("end")
        except queue.Empty:
            pass
        self.after(100, self._drain_log)

    def _status(self, text, color):
        self.status_lbl.configure(text=f"●  {text}", text_color=color)

    # ---------------- 会话 ----------------
    def connect(self):
        self._log("CDP cookie 注入 → 会话构建 → 页面上下文解析...")
        try:
            cookies = cdp_get_cookies(get_cdp_ws_url())
            session = build_session(cookies)
            if not check_alive(session):
                self._log("会话失效：请确认教务已登录且页面打开", "err")
                self._status("会话失效", ERR)
                return
            self.client = JWClient(session)
            if not self.client._h("rwlx"):
                self.client.cdp_refresh_hidden(get_cdp_ws_url())
            if not self.client._h("rwlx"):
                self._log(f"提示: 请确认浏览器中打开了选课页面 "
                          f"({JW_BASE}/xsxk/zzxkyzb_cxZzxkYzbIndex.html)", "warn")
            self._log(f"连接成功: tabs={list(self.client.tabs)} "
                      f"rwlx={self.client._h('rwlx') or '?'} "
                      f"xklc={self.client._h('xklc') or '?'}", "ok")
            self._status("已连接", OK)
            self.btn_start.configure(state="normal")
        except Exception as e:
            self._log(f"连接失败: {e}", "err")
            self._status("连接失败", ERR)

    def crawl(self):
        if not self.client:
            self._log("请先连接浏览器", "warn")
            return
        self._log("抓取课程全表...")
        try:
            snap = grab.fetch_full_snapshot(self.client, ["10", "11"], self._log)
            self._log(f"全表完成: {len(snap)} 门课程", "ok")
        except Exception as e:
            self._log(f"抓取失败: {e}", "err")

    def selfcheck(self):
        if not self.client:
            self._log("请先连接浏览器", "warn")
            return
        try:
            rows = self.client.get_choosed()
            self._log(f"链路自检: 已选 {len(rows)} 门课程", "ok")
            for r in rows[:8]:
                self._log(f"  已选: {r.get('kcmc')}")
            if len(rows) > 8:
                self._log(f"  ... 共 {len(rows)} 门", "info")
        except Exception as e:
            self._log(f"自检失败: {e}", "err")

    def verify(self):
        try:
            cookies = cdp_get_cookies(get_cdp_ws_url())
            jw = [c for c in cookies if JW_HOST in (c.get("domain") or "")]
            self._log(f"CDP 验证: 共 {len(cookies)} cookie, 教务域 {len(jw)} 个", "ok")
        except Exception as e:
            self._log(f"CDP 验证失败: {e}", "err")

    # ---------------- 抢课 ----------------
    def _opts(self):
        kw = self.kw.get().strip()
        if not kw:
            self._log("请先输入课程关键词", "warn")
            return None
        kklxdms = [k for k, on in self.cat.items() if on]
        try:
            interval = float(self.interval.get() or 1.5)
            timeout = int(self.timeout.get() or 1800)
        except ValueError:
            self._log("间隔/超时必须是数字", "err")
            return None
        return {"keywords": kw.split(), "kklxdms": kklxdms,
                "interval": interval, "timeout": timeout,
                "dry_run": bool(self.dry_sw.get()),
                "try_complex": bool(self.cpx_sw.get())}

    def start(self):
        if self._running:
            self._log("已有任务在运行", "warn")
            return
        opts = self._opts()
        if opts is None:
            return
        self._running = True
        self.stop_evt = threading.Event()
        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self._status("运行中", WARN)
        self.worker = threading.Thread(target=self._worker, args=(opts,),
                                       daemon=True)
        self.worker.start()

    def _worker(self, opts):
        try:
            mode = "预演" if opts["dry_run"] else "抢课"
            self._log(f"启动{mode}: 关键词 {opts['keywords']} "
                      f"类别 {opts['kklxdms']} 间隔 {opts['interval']}s")
            grab.run_grab(opts["keywords"], kklxdms=opts["kklxdms"],
                          interval=opts["interval"], timeout=opts["timeout"],
                          dry_run=opts["dry_run"], try_complex=opts["try_complex"],
                          log=self._log, stop_event=self.stop_evt)
        except Exception as e:
            self._log(f"任务异常: {e}", "err")
        finally:
            self._running = False
            if self.client:
                self.btn_start.configure(state="normal")
            self.btn_stop.configure(state="disabled")
            self._status("已连接" if self.client else "未连接",
                         OK if self.client else DIM)
            self._log("任务结束", "info")

    def stop(self):
        if self.stop_evt:
            self.stop_evt.set()
            self._log("停止信号已发送，将在本轮结束后退出", "warn")


def main():
    if ctk is None:
        print("缺少 customtkinter: pip install customtkinter")
        sys.exit(1)
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()