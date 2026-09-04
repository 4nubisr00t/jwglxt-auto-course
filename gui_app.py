# -*- coding: utf-8 -*-
"""
JWGLXT Auto Course - GUI (customtkinter) 二次元主题版
=====================================================
双击运行或 python gui_app.py。依赖: pip install customtkinter
逻辑层完全复用 grab.py / jw_cdp_client.py / schedule.py，本文件只负责交互与氛围。
"""
import os
import queue
import random
import sys
import threading
import time
import math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import grab
from jw_cdp_client import (get_cdp_ws_url, cdp_get_cookies, build_session,
                           check_alive, JWClient, JW_BASE, JW_HOST)
from schedule import parse_sksj, any_conflict, slots_str

try:
    import customtkinter as ctk
    ctk.set_appearance_mode("dark")
except Exception as e:  # 无显示环境/未安装时给出提示
    ctk = None

try:
    import tkinter as tk
except Exception:
    tk = None

# ---------------- 二次元主题（暗夜紫 × 樱花粉 × 星辉） ----------------
BG = "#0d0b18"
CARD = "#161226"
CARD2 = "#221b36"
CARD3 = "#2c2344"
TEXT = "#f2eefb"
DIM = "#a79fc9"
LINE = "#3a3160"
ACCENT = "#ff77a9"      # 樱花粉
ACCENT2 = "#b388ff"     # 星辉紫
OK = "#7ce7b8"
WARN = "#ffc46b"
ERR = "#ff5c7a"
STAR_COLORS = ["#cfc4ff", "#ffffff", "#ffd7e8", "#b388ff", "#ffe9f2"]

LV_COLOR = {"info": DIM, "ok": OK, "warn": WARN, "err": ERR, "star": ACCENT2}
TAG_FONT = "Microsoft YaHei UI"
MONO_FONT = "Cascadia Mono"


class NightSky:
    """canvas 二次元夜空：渐变 + 星云 + 闪烁星星 + 飘落樱花 + 少女剪影"""

    def __init__(self, canvas):
        self.cv = canvas
        self.w = 0
        self.h = 0
        self.stars = []
        self.petals = []
        self._phase = 0

    def init(self, w, h):
        self.w = w
        self.h = h
        self.cv.delete("all")
        self._draw_gradient(w, h)
        self._draw_nebula(w, h)
        self._draw_silhouette(w, h)
        # 星星
        self.stars = []
        rnd = random.Random(42)
        for _ in range(52):
            x = rnd.uniform(0, w)
            y = rnd.uniform(0, h * 0.94)
            self.stars.append({
                "id": self.cv.create_oval(x - 1, y - 1, x + 1, y + 1,
                                          fill="#cfc4ff", outline=""),
                "x": x, "y": y, "r": rnd.choice([1.0, 1.2, 1.6]),
                "base": rnd.choice(STAR_COLORS),
                "phase": rnd.uniform(0, math.tau),
                "spd": rnd.uniform(1.2, 3.2),
            })
        # 樱花
        self.petals = []
        for _ in range(26):
            p = self._new_petal(rnd)
            p["id"] = self._petal_oval(p)
            self.petals.append(p)

    def _new_petal(self, rnd=None):
        rnd = rnd or random
        s = rnd.uniform(3.5, 6.5)
        return {
            "id": None,
            "x": rnd.uniform(0, self.w), "y": rnd.uniform(-20, self.h),
            "s": s, "v": rnd.uniform(0.6, 1.5),
            "sway": rnd.uniform(0.4, 1.2), "rot": rnd.uniform(0, math.tau),
            "col": rnd.choice(["#ff9ec4", "#ffb3d1", "#ff77a9", "#ffc9de"]),
        }

    def _petal_oval(self, p):
        return self.cv.create_oval(
            p["x"] - p["s"], p["y"] - p["s"] * 0.7,
            p["x"] + p["s"], p["y"] + p["s"] * 0.7,
            fill=p["col"], outline="")

    def _draw_gradient(self, w, h):
        top = (9, 8, 22)
        mid = (24, 16, 50)
        bot = (46, 26, 78)
        for i in range(0, h, 2):
            k = i / h
            if k < 0.55:
                kk = k / 0.55
                c = tuple(int(top[j] + (mid[j] - top[j]) * kk) for j in range(3))
            else:
                kk = (k - 0.55) / 0.45
                c = tuple(int(mid[j] + (bot[j] - mid[j]) * kk) for j in range(3))
            self.cv.create_line(0, i, w, i, fill="#%02x%02x%02x" % c)

    def _draw_nebula(self, w, h):
        # 几团朦胧的星云光晕（低对比叠色）
        blobs = [(0.72, 0.20, 0.34, "#3a2a66"), (0.28, 0.30, 0.26, "#2c2052"),
                 (0.55, 0.75, 0.30, "#402252"), (0.85, 0.62, 0.22, "#4a1f3f")]
        for rx, ry, rr, col in blobs:
            self.cv.create_oval(w * rx - w * rr, h * ry - h * rr,
                                w * rx + w * rr, h * ry + h * rr,
                                fill=col, outline="")
        # 樱花粉微光晕
        for rx, ry, rr in [(0.80, 0.18, 0.07)]:
            self.cv.create_oval(w * rx - w * rr, h * ry - h * rr,
                                w * rx + w * rr, h * ry + h * rr,
                                fill="#5c2a4a", outline="")

    def _draw_silhouette(self, w, h):
        """右下角：黑长直少女背影剪影 + 一缕红眼微光"""
        cx = w - w * 0.085
        base_y = h - 8
        body = "#0a0814"
        # 长发主体（垂落的曲线）
        strands = [
            (0.0, -198, 0.0, -74, 26, 0), (0.16, -184, 0.10, -60, 20, 0),
            (-0.14, -190, -0.10, -58, 18, 0), (-0.24, -172, -0.18, -40, 14, 0),
            (0.26, -170, 0.22, -40, 12, 0), (-0.05, -200, -0.03, -86, 10, 0),
        ]
        for dx1, dy1, dx2, dy2, width, _ in strands:
            self.cv.create_line(cx + dx1, base_y + dy1, cx + dx2, base_y + dy2,
                                fill=body, width=width, capstyle="round")
        # 身体（背影窄梯形）
        self.cv.create_polygon(cx - 15, base_y - 118, cx + 15, base_y - 118,
                               cx + 22, base_y - 6, cx - 22, base_y - 6,
                               fill=body, outline="")
        # 头
        self.cv.create_oval(cx - 13, base_y - 150, cx + 13, base_y - 124,
                            fill=body, outline="")
        # 一缕红眼微光（侧面）
        self.cv.create_oval(cx + 8, base_y - 140, cx + 11, base_y - 137,
                            fill="#ff2b5e", outline="")

    def tick(self):
        """动画帧：星星呼吸 + 樱花飘落"""
        t = self._phase
        self._phase += 0.04
        for s in self.stars:
            b = 0.45 + 0.55 * (0.5 + 0.5 * math.sin(t * s["spd"] + s["phase"]))
            col = s["base"]
            # 按亮度微调色值（取 base 各分量按 b 缩放近似）
            try:
                r, g, bl = int(col[1:3], 16), int(col[3:5], 16), int(col[5:7], 16)
                nr = min(255, int(120 + (r - 120) * b))
                ng = min(255, int(120 + (g - 120) * b))
                nb = min(255, int(150 + (bl - 150) * b))
                self.cv.itemconfig(s["id"], fill="#%02x%02x%02x" % (nr, ng, nb))
            except Exception:
                pass
        for p in self.petals:
            p["y"] += p["v"]
            p["rot"] += 0.03 * p["v"]
            p["x"] += math.sin(p["rot"]) * p["sway"]
            if p["y"] - p["s"] > self.h:
                self.petals.remove(p)
                self.cv.delete(p["id"])
                p["y"] = -6 - p["s"]
                p["x"] = random.uniform(0, self.w)
                p["id"] = self._petal_oval(p)
                self.petals.append(p)
                continue
            self.cv.coords(p["id"],
                           p["x"] - p["s"], p["y"] - p["s"] * 0.7,
                           p["x"] + p["s"], p["y"] + p["s"] * 0.7)
            self.cv.itemconfig(p["id"], fill=p["col"])
        self.cv.after(40, self.tick)


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("JWGLXT AUTO · 教务选课自动化")
        self.geometry("1060x740")
        self.minsize(900, 620)
        self.configure(bg=BG)

        self.client = None
        self.worker = None
        self.stop_evt = None
        self.log_q = queue.Queue()
        self._running = False
        self._running_connect = False
        self.snapshot = None       # 抓取的全表缓存
        self.choosed_rows = []     # 已选课程列表（含 sksj）
        self.busy_slots = []       # 已选课全部时间槽（冲突检测基准）

        self._build()
        self.after(100, self._drain_log)
        if tk is not None:
            self._sky = NightSky(self.sky)
            self._resize_sky()
            self.bind("<Configure>", self._on_resize)
            self.after(60, self._sky.tick)

    # ---------------- UI ----------------
    def _card(self, parent, title, icon="✦"):
        """二次元卡片：顶部粉色发光条 + 左侧小图标 + 右侧装饰星"""
        outer = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=16,
                             border_width=1, border_color=LINE)
        outer.pack(fill="x", pady=(0, 12))
        # 顶部发光条
        glow = ctk.CTkFrame(outer, fg_color=ACCENT, height=2, corner_radius=0,
                            width=1)
        glow.pack(fill="x", padx=12, pady=(8, 0))
        # 标题行
        head = ctk.CTkFrame(outer, fg_color="transparent")
        head.pack(fill="x", padx=14, pady=(4, 2))
        ctk.CTkLabel(head, text=icon, text_color=ACCENT,
                     font=ctk.CTkFont(size=13, weight="bold")
                     ).pack(side="left")
        ctk.CTkLabel(head, text=f"  {title}  ", text_color=ACCENT2,
                     font=ctk.CTkFont(family=TAG_FONT, size=12, weight="bold")
                     ).pack(side="left")
        ctk.CTkLabel(head, text="✦ · ✦", text_color="#3d3560",
                     font=ctk.CTkFont(size=10)
                     ).pack(side="right")
        return outer

    def _btn(self, parent, text, cmd, color=None, height=34, ghost=False,
             border=None):
        fg = color or CARD3
        hv = "#3d315c"
        b = ctk.CTkButton(parent, text=text, command=cmd, height=height,
                          fg_color=fg, hover_color=hv,
                          border_width=1 if border else 0,
                          border_color=border or LINE,
                          corner_radius=11,
                          text_color=TEXT if not color else "#2a1020",
                          font=ctk.CTkFont(family=TAG_FONT, size=12))
        b.pack(fill="x", padx=12, pady=4)
        return b

    def _build(self):
        # 底层夜空画布
        self.sky = tk.Canvas(self, bg=BG, highlightthickness=0)
        self.sky.pack(fill="both", expand=True)

        # 顶部标题栏
        head = ctk.CTkFrame(self, fg_color=CARD, corner_radius=0,
                            border_width=0, height=62)
        head.place(relx=0.02, rely=0.02, relwidth=0.96)
        ctk.CTkLabel(head, text="✦", text_color=ACCENT,
                     font=ctk.CTkFont(size=22, weight="bold")
                     ).place(relx=0.018, rely=0.5, anchor="w")
        ctk.CTkLabel(head, text="JWGLXT", text_color=TEXT,
                     font=ctk.CTkFont(family=TAG_FONT, size=18, weight="bold")
                     ).place(relx=0.055, rely=0.5, anchor="w")
        ctk.CTkLabel(head, text="AUTO", text_color=ACCENT,
                     font=ctk.CTkFont(family=TAG_FONT, size=18, weight="bold")
                     ).place(relx=0.205, rely=0.5, anchor="w")
        ctk.CTkLabel(head, text="— ✦ 教务选课自动化 ✦ —", text_color=DIM,
                     font=ctk.CTkFont(family=TAG_FONT, size=12)
                     ).place(relx=0.40, rely=0.5, anchor="center")
        self.status_lbl = ctk.CTkLabel(head, text="○ 未连接", text_color=DIM,
                                       font=ctk.CTkFont(family=TAG_FONT, size=13))
        self.status_lbl.place(relx=0.945, rely=0.5, anchor="e")
        ctk.CTkLabel(head, text="★", text_color=ACCENT2,
                     font=ctk.CTkFont(size=12)).place(relx=0.975, rely=0.5,
                                                      anchor="e")
        # 标题栏底部发光细线
        lline = ctk.CTkFrame(head, fg_color=ACCENT, height=2, width=1,
                             corner_radius=0)
        lline.place(relx=0, rely=1.0, relwidth=1.0, anchor="sw")

        # 左栏（浮于夜空之上）
        left = ctk.CTkFrame(self, fg_color=CARD, corner_radius=16,
                            border_width=1, border_color=LINE, height=1)
        left.place(relx=0.023, rely=0.13, relwidth=0.345, relheight=0.85)

        c1 = self._card(left, "会话", "✧")
        self.btn_conn = self._btn(c1, "连接浏览器", self.connect, ACCENT, 36)
        self.btn_crawl = self._btn(c1, "抓取全表", self.crawl)
        self.btn_view = self._btn(c1, "查看班次", self.open_class_view)
        self.btn_tfilter = self._btn(c1, "时段筛课", self.open_time_filter)
        self.btn_check = self._btn(c1, "链路自检", self.selfcheck)
        self.btn_verify = self._btn(c1, "CDP 验证", self.verify)

        c2 = self._card(left, "目标课程", "✦")
        ctk.CTkLabel(c2, text="关键词（空格分隔多个）", text_color=DIM,
                     font=ctk.CTkFont(family=TAG_FONT, size=11)
                     ).pack(anchor="w", padx=12, pady=(2, 2))
        self.kw = ctk.CTkEntry(c2, placeholder_text="例如: 敦煌 光影 算法",
                               height=36, fg_color=CARD2, border_color=LINE,
                               text_color=TEXT)
        self.kw.pack(fill="x", padx=12, pady=(0, 6))
        self.cat = {"10": True, "11": True, "01": False}
        self.cat_btns = {}
        row = ctk.CTkFrame(c2, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=(0, 6))
        for k, name in (("10", "通识选修"), ("11", "特殊课程"), ("01", "主修")):
            b = ctk.CTkButton(row, text=name, width=92, height=32,
                              fg_color="#3d2440" if self.cat[k] else CARD3,
                              text_color=ACCENT if self.cat[k] else DIM,
                              border_width=2 if self.cat[k] else 1,
                              border_color=ACCENT if self.cat[k] else LINE,
                              hover_color="#4a2a45", corner_radius=17,
                              font=ctk.CTkFont(family=TAG_FONT, size=12,
                                               weight="bold" if self.cat[k]
                                               else "normal"),
                              command=lambda kk=k: self._toggle_cat(kk))
            b.pack(side="left", padx=(0, 8))
            self.cat_btns[k] = b

        c3 = self._card(left, "参数", "◇")
        pr = ctk.CTkFrame(c3, fg_color="transparent")
        pr.pack(fill="x", padx=12)
        ctk.CTkLabel(pr, text="轮询间隔(s)", text_color=DIM,
                     font=ctk.CTkFont(family=TAG_FONT, size=11)).pack(side="left")
        self.interval = ctk.CTkEntry(pr, width=60, height=30, fg_color=CARD2,
                                     border_color=ACCENT2, text_color=TEXT,
                                     corner_radius=9)
        self.interval.insert(0, "1.5")
        self.interval.pack(side="left", padx=(6, 18))
        ctk.CTkLabel(pr, text="超时(s)", text_color=DIM,
                     font=ctk.CTkFont(family=TAG_FONT, size=11)).pack(side="left")
        self.timeout = ctk.CTkEntry(pr, width=80, height=30, fg_color=CARD2,
                                    border_color=ACCENT2, text_color=TEXT,
                                    corner_radius=9)
        self.timeout.insert(0, "1800")
        self.timeout.pack(side="left", padx=6)

        self.dry_sw = ctk.CTkSwitch(c3, text="预演模式（只匹配不出手）",
                                    progress_color=ACCENT,
                                    border_width=1, border_color=LINE,
                                    fg_color=CARD3, button_color=ACCENT,
                                    button_hover_color="#ff94bf",
                                    font=ctk.CTkFont(family=TAG_FONT, size=12))
        self.dry_sw.pack(anchor="w", padx=14, pady=(8, 2))
        self.dry_sw.select()
        self.cpx_sw = ctk.CTkSwitch(c3, text="尝试组合实践班",
                                    progress_color=ACCENT,
                                    border_width=1, border_color=LINE,
                                    fg_color=CARD3, button_color=ACCENT,
                                    button_hover_color="#ff94bf",
                                    font=ctk.CTkFont(family=TAG_FONT, size=12))
        self.cpx_sw.pack(anchor="w", padx=14, pady=(0, 8))

        self.btn_start = ctk.CTkButton(left, text="开  始", height=46,
                                       fg_color=ACCENT, hover_color="#ff94bf",
                                       corner_radius=13,
                                       border_width=2, border_color="#ffd7e8",
                                       font=ctk.CTkFont(family=TAG_FONT, size=16,
                                                        weight="bold"),
                                       command=self.start)
        self.btn_start.pack(fill="x", padx=14, pady=(4, 6))
        self.btn_start.configure(state="disabled")
        self.btn_stop = ctk.CTkButton(left, text="停  止", height=38,
                                      fg_color="transparent",
                                      hover_color="#3a2440", border_width=1,
                                      border_color=ERR, text_color=ERR,
                                      corner_radius=10,
                                      font=ctk.CTkFont(family=TAG_FONT, size=13),
                                      command=self.stop)
        self.btn_stop.pack(fill="x", padx=14)
        self.btn_stop.configure(state="disabled")

        # 右栏日志（浮于夜空之上）
        self.log_box = ctk.CTkTextbox(self, fg_color="#12101f",
                                      border_color=LINE, border_width=1,
                                      corner_radius=16, wrap="none",
                                      font=ctk.CTkFont(family=MONO_FONT, size=12),
                                      text_color=TEXT, width=1, height=1)
        self.log_box.place(relx=0.383, rely=0.13, relwidth=0.595, relheight=0.85)
        for tag, color in LV_COLOR.items():
            self.log_box.tag_config(tag, foreground=color)
        self.log_box.tag_config("t", foreground="#6a6390")
        self.log_box.insert("end",
                            "✧· ─────── ✦ 课 程 结 界 启 动 ✦ ─────── ·✧\n", "t")
        self._log("✦ 欢迎回来，主人。先「连接浏览器」，再「抓取全表」，"
                  "最后输入关键词，开始狙击心仪的课程吧。")

    def _on_resize(self, ev):
        if ev.widget is self and tk is not None:
            cur = (self.winfo_width(), self.winfo_height())
            if cur != (self._last_w, self._last_h):
                self._resize_sky()

    def _resize_sky(self):
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        self._last_w, self._last_h = w, h
        if w > 10 and h > 10:
            self._sky.init(w, h)

    def _toggle_cat(self, k):
        self.cat[k] = not self.cat[k]
        on = self.cat[k]
        self.cat_btns[k].configure(
            fg_color="#3d2440" if on else CARD3,
            text_color=ACCENT if on else DIM,
            border_width=2 if on else 1,
            border_color=ACCENT if on else LINE,
            font=ctk.CTkFont(family=TAG_FONT, size=12,
                             weight="bold" if on else "normal"))

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
        if self._running_connect:
            return
        self._running_connect = True
        self.btn_conn.configure(state="disabled")
        self._status("连接中", WARN)
        threading.Thread(target=self._connect_worker, daemon=True).start()

    def _connect_worker(self):
        try:
            self._log("检测调试实例，必要时自动启动托管 Chrome...")
            self.client, _ = grab.init_client(spawn=True, log=self._log)
            self._log(f"连接成功: tabs={list(self.client.tabs)} "
                      f"rwlx={self.client._h('rwlx') or '?'} "
                      f"xklc={self.client._h('xklc') or '?'}", "ok")
            try:
                rows = self.client.get_choosed()
                self.choosed_rows = rows
                self.busy_slots = []
                for r in rows:
                    self.busy_slots += parse_sksj(r.get("sksj") or "")
                self._log(f"已选 {len(rows)} 门，时间槽 {len(self.busy_slots)} 段"
                          f"（冲突检测基准）", "ok")
            except Exception as e:
                self._log(f"已选获取失败: {e}", "warn")
            self.btn_start.configure(state="normal")
            self._status("已连接", OK)
        except Exception as e:
            self._log(f"连接失败: {e}", "err")
            self._status("连接失败", ERR)
        finally:
            self._running_connect = False
            self.btn_conn.configure(state="normal")

    def crawl(self):
        if not self.client:
            self._log("请先连接浏览器", "warn")
            return
        self._log("抓取课程全表...")
        try:
            kklxdms = sorted(self.client.tabs.keys())
            snap = grab.fetch_full_snapshot(self.client, kklxdms, self._log,
                                            detail=True)
            self.snapshot = snap
            self._log(f"全表完成: {len(snap)} 门课程（类别 {kklxdms}）", "ok")
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

    # ---------------- 课程班次查看 ----------------
    def _conflict_with(self, slots):
        if not slots:
            return None
        for row in self.choosed_rows:
            rslots = parse_sksj(row.get("sksj") or "")
            if any_conflict(slots, rslots):
                return row.get("kcmc")
        return None

    def _mk_view_win(self, title):
        win = ctk.CTkToplevel(self)
        win.title(title)
        win.geometry("900x580")
        win.configure(fg_color=CARD)
        box = ctk.CTkTextbox(win, fg_color="#12101f", border_color=LINE,
                             border_width=1, corner_radius=14, wrap="none",
                             font=ctk.CTkFont(family=MONO_FONT, size=12),
                             text_color=TEXT)
        box.pack(fill="both", expand=True, padx=12, pady=12)
        box.tag_config("head", foreground=WARN)
        box.tag_config("conflict", foreground=ERR)
        box.tag_config("ok", foreground=OK)
        box.tag_config("dim", foreground=DIM)
        win._box = box
        return win

    def open_class_view(self):
        if self.client is None:
            self._log("请先连接浏览器", "warn")
            return
        if not self.snapshot:
            self._log("请先抓取全表，才能定位课程", "warn")
            return
        win = self._mk_view_win("课程班次查看")
        top = ctk.CTkFrame(win, fg_color="transparent")
        top.pack(fill="x", padx=12, pady=(12, 0))
        ctk.CTkLabel(top, text="课程关键词:", text_color=DIM,
                     font=ctk.CTkFont(family=TAG_FONT, size=12)).pack(side="left")
        kw = ctk.CTkEntry(top, width=280, height=30, fg_color=CARD2,
                          border_color=LINE, text_color=TEXT)
        kw.pack(side="left", padx=(8, 8))
        ctk.CTkButton(top, text="查询", width=80, height=30,
                      fg_color=ACCENT, hover_color="#ff94bf",
                      command=lambda: self._render_class_view(kw.get().strip(), win)
                      ).pack(side="left")
        kw.bind("<Return>",
                lambda e: self._render_class_view(kw.get().strip(), win))
        win._box.insert("end", "输入课程名/课程号，回车查询各班次（实时抓取，含冲突标记）\n", "dim")
        kw.focus_set()

    def _render_class_view(self, text, win):
        box = win._box
        box.delete("1.0", "end")
        if not text:
            box.insert("end", "输入课程名或课程号关键词后查询\n", "dim")
            return
        hits = grab.match_courses(self.snapshot, text.split())
        if not hits:
            box.insert("end", f"全表里没找到含「{text}」的课程\n", "conflict")
            return
        for kch_id, c in hits[:12]:
            box.insert("end", f"❖ {c['kcmc']}（{c['kch']}，{c['xf']}分）\n", "head")
            try:
                jxbs = self.client.get_jxbs(kch_id, c["kklxdm"])
            except Exception as e:
                box.insert("end", f"  班次获取失败: {e}\n", "conflict")
                continue
            for jb in jxbs:
                slots = parse_sksj(jb.get("sksj") or "")
                st = slots_str(slots)
                rl = int(jb.get("jxbrl") or 0)
                yx = int(jb.get("yxzrs") or 0)
                safe = rl - yx if rl else -1
                teacher = (jb.get("jsxx") or "").split("/")[-1] or "?"
                conf = self._conflict_with(slots)
                if conf:
                    tag = "conflict"
                    mark = f"✗ 与已选「{conf}」冲突"
                else:
                    tag = "ok"
                    mark = "✓ 时间不冲突"
                yl = f"{safe}" if safe >= 0 else "?"
                box.insert("end",
                           f"  [{jb.get('jxb_id','')[:8]}] {st} | "
                           f"{jb.get('jxdd') or '?'} | {teacher} | "
                           f"余量 {yl}/{rl or '?'} | {mark}\n", tag)
            box.insert("end", "\n")
        if len(hits) > 12:
            box.insert("end", f"... 还有 {len(hits) - 12} 门，请用更精确的关键词\n", "dim")

    # ---------------- 按时间段筛课 ----------------
    def open_time_filter(self):
        if self.client is None:
            self._log("请先连接浏览器", "warn")
            return
        if not self.snapshot:
            self._log("请先抓取全表，才能按时间筛课", "warn")
            return
        win = self._mk_view_win("按时间段筛选课程")
        top = ctk.CTkFrame(win, fg_color="transparent")
        top.pack(fill="x", padx=12, pady=(12, 0))
        ctk.CTkLabel(top, text="星期:", text_color=DIM,
                     font=ctk.CTkFont(family=TAG_FONT, size=12)).pack(side="left")
        days = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        day_menu = ctk.CTkOptionMenu(top, values=days, width=88, height=30,
                                     fg_color=CARD2, button_color=ACCENT,
                                     button_hover_color="#ff94bf",
                                     text_color=TEXT)
        day_menu.set("周一")
        day_menu.pack(side="left", padx=(6, 14))
        ctk.CTkLabel(top, text="节次:", text_color=DIM,
                     font=ctk.CTkFont(family=TAG_FONT, size=12)).pack(side="left")
        seg_menu = ctk.CTkOptionMenu(top, values=["1-2", "3-4", "5-6", "7-8",
                                                  "9-10", "11-12"],
                                     width=88, height=30, fg_color=CARD2,
                                     button_color=ACCENT,
                                     button_hover_color="#ff94bf",
                                     text_color=TEXT)
        seg_menu.set("3-4")
        seg_menu.pack(side="left", padx=(6, 14))
        ctk.CTkButton(top, text="筛选", width=80, height=30,
                      fg_color=ACCENT, hover_color="#ff94bf",
                      command=lambda: self._render_time_filter(
                          win, days.index(day_menu.get()) + 1,
                          *map(int, seg_menu.get().split("-")))
                      ).pack(side="left")
        win._box.insert("end", "选星期与节次后点「筛选」：顶部列出该时段你已在上的课，"
                                "下方列出未选的可用课程（含余量、冲突标记）\n", "dim")

    def _render_time_filter(self, win, day, a, b):
        box = win._box
        box.delete("1.0", "end")

        def in_slot(cls):
            for s in parse_sksj(cls.get("sksj") or ""):
                if s.day == day and max(s.start, a) <= min(s.end, b):
                    return True
            return False

        def mine_in_slot(r):
            for s in parse_sksj(r.get("sksj") or ""):
                if s.day == day and max(s.start, a) <= min(s.end, b):
                    return True
            return False

        mine = [r for r in self.choosed_rows if mine_in_slot(r)]
        if mine:
            box.insert("end", f"★ 该时段你已在上的课（{len(mine)} 门）：\n", "warn")
            for r in mine[:10]:
                box.insert("end", f"    {r.get('kcmc')} | "
                                   f"{slots_str(parse_sksj(r.get('sksj') or ''))}\n", "dim")
            box.insert("end", "\n")

        choosed_ids = {r.get("kch_id") for r in self.choosed_rows}
        count = 0
        for kch_id, c in self.snapshot.items():
            if kch_id in choosed_ids:
                continue
            matched = [cls for cls in c["classes"] if in_slot(cls)]
            if not matched:
                continue
            count += 1
            box.insert("end", f"❖ {c['kcmc']}（{c['kch']}，{c['xf']}分，"
                               f"{len(c['classes'])}个班）\n", "head")
            for cls in matched:
                slots = parse_sksj(cls.get("sksj") or "")
                st = slots_str(slots)
                rl = int(cls.get("jxbrl") or 0)
                yx = int(cls.get("yxzrs") or 0)
                safe = rl - yx if rl else -1
                conf = self._conflict_with(slots)
                if conf:
                    tag = "conflict"
                    mark = f"✗ 与「{conf}」冲突"
                else:
                    tag = "ok"
                    mark = "✓ 可抢"
                yl = f"{safe}" if safe >= 0 else "?"
                box.insert("end",
                           f"  {st} | {cls.get('jxdd') or '?'} | "
                           f"余量 {yl}/{rl or '?'} | {mark}\n", tag)
            box.insert("end", "\n")
        if count == 0:
            box.insert("end", "该时段没有找到课程\n", "dim")
        else:
            box.insert("end", f"共 {count} 门课在该时段有班\n", "info")

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