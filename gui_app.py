# -*- coding: utf-8 -*-
"""
JWGLXT Auto Course - GUI (customtkinter) 二次元主题版 · 漆黑结界
=============================================================
双击运行或 python gui_app.py。依赖: pip install customtkinter pillow
逻辑层完全复用 grab.py / jw_cdp_client.py / schedule.py，本文件只负责交互与氛围。
"""
import os
import queue
import random
import sys
import threading
import time
import math

from PIL import Image, ImageTk

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import grab
from jw_cdp_client import (get_cdp_ws_url, cdp_get_cookies, build_session,
                           check_alive, JWClient, JW_BASE, JW_HOST)
from schedule import parse_sksj, any_conflict, slots_str

try:
    import customtkinter as ctk
    ctk.set_appearance_mode("dark")
except Exception as e:
    ctk = None

try:
    import tkinter as tk
except Exception:
    tk = None

# ---------------- 路径配置 ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
ASSET_BG = os.path.join(ASSETS_DIR, "bg_anime.jpg")
ASSET_CHAR = os.path.join(ASSETS_DIR, "char_full.jpg")

# ---------------- 二次元主题（深渊暗夜紫 × 绯红魔眼 × 樱花粉 × 星辉紫） ----------------
BG = "#0c0a17"          # 深渊暗夜黑紫
CARD = "#141024"        # 卡片深色底板（Galgame对话框质感）
CARD2 = "#1d1733"       # 内部输入框/容器
CARD3 = "#261f3e"       # 按钮次级底色
CARD_HOVER = "#382c5e"  # 悬停亮紫
TEXT = "#f6f2ff"        # 主文字（冷白高亮）
DIM = "#9d93bf"         # 次要文字（紫灰）
LINE = "#382d5a"        # 结界分割线
LINE_GLOW = "#7048a0"   # 发光线
ACCENT = "#ff77a9"      # 霓虹樱花粉
ACCENT_HOVER = "#ff9ec4"# 樱花粉高亮
ACCENT2 = "#b388ff"     # 星辉浅紫
CRIMSON = "#ff2b5e"     # 绯红魔眼/血月红
OK = "#7ce7b8"          # 结界生机绿
WARN = "#ffb86c"        # 警惕琥珀金
ERR = "#ff5577"         # 咒文冲突红
STAR_COLORS = ["#cfc4ff", "#ffffff", "#ffd7e8", "#b388ff", "#ffe9f2"]

LV_COLOR = {
    "info": TEXT,
    "ok": OK,
    "warn": WARN,
    "err": ERR,
    "star": ACCENT2,
    "magic": ACCENT,
    "dim": DIM,
    "head": "#ffa8c9",
}
TAG_FONT = "Microsoft YaHei UI"
MONO_FONT = "Cascadia Mono"


class NightSky:
    """二次元夜空背景画布：PIL 插画背景 + 飘落樱花 + 闪烁星辰 + 结界微光"""

    def __init__(self, canvas):
        self.cv = canvas
        self.w = 0
        self.h = 0
        self.stars = []
        self.petals = []
        self._phase = 0
        self.destroyed = False
        self.bg_photo = None
        self.orig_bg = None

        if os.path.exists(ASSET_BG):
            try:
                self.orig_bg = Image.open(ASSET_BG).convert("RGB")
            except Exception:
                self.orig_bg = None

    def init(self, w, h):
        if self.destroyed or w <= 10 or h <= 10:
            return
        self.w = w
        self.h = h
        self.cv.delete("all")

        # 1. 插画背景或程序化降级
        if self.orig_bg:
            try:
                resized = self.orig_bg.resize((w, h), Image.Resampling.BILINEAR)
                self.bg_photo = ImageTk.PhotoImage(resized)
                self.cv.create_image(0, 0, image=self.bg_photo, anchor="nw", tags="bg")
            except Exception:
                self._draw_procedural_bg(w, h)
        else:
            self._draw_procedural_bg(w, h)

        # 2. 星星粒子（上部 70% 区域闪烁）
        self.stars = []
        rnd = random.Random(77)
        for _ in range(45):
            x = rnd.uniform(0, w)
            y = rnd.uniform(0, h * 0.72)
            base_col = rnd.choice(STAR_COLORS)
            s_id = self.cv.create_oval(x - 1.2, y - 1.2, x + 1.2, y + 1.2,
                                      fill=base_col, outline="")
            self.stars.append({
                "id": s_id,
                "x": x, "y": y,
                "base": base_col,
                "phase": rnd.uniform(0, math.tau),
                "spd": rnd.uniform(1.2, 3.0),
            })

        # 3. 飘落樱花花瓣
        self.petals = []
        for _ in range(28):
            p = self._new_petal(rnd)
            p["id"] = self._petal_oval(p)
            self.petals.append(p)

    def _new_petal(self, rnd=None):
        rnd = rnd or random
        s = rnd.uniform(3.5, 6.0)
        return {
            "id": None,
            "x": rnd.uniform(0, max(self.w, 400)),
            "y": rnd.uniform(-30, max(self.h, 400)),
            "s": s,
            "v": rnd.uniform(0.7, 1.6),
            "sway": rnd.uniform(0.5, 1.4),
            "rot": rnd.uniform(0, math.tau),
            "col": rnd.choice(["#ff77a9", "#ff9ec4", "#ffb3d1", "#ffd8e8"]),
        }

    def _petal_oval(self, p):
        return self.cv.create_oval(
            p["x"] - p["s"], p["y"] - p["s"] * 0.65,
            p["x"] + p["s"], p["y"] + p["s"] * 0.65,
            fill=p["col"], outline=""
        )

    def _draw_procedural_bg(self, w, h):
        """降级纯代码手绘：蓝紫渐变 + 星云 + 剪影"""
        top = (12, 10, 23)
        mid = (26, 18, 52)
        bot = (48, 28, 80)
        for i in range(0, h, 3):
            k = i / max(h, 1)
            if k < 0.55:
                kk = k / 0.55
                c = tuple(int(top[j] + (mid[j] - top[j]) * kk) for j in range(3))
            else:
                kk = (k - 0.55) / 0.45
                c = tuple(int(mid[j] + (bot[j] - mid[j]) * kk) for j in range(3))
            self.cv.create_line(0, i, w, i, fill="#%02x%02x%02x" % c)

        # 星云光晕
        blobs = [(0.72, 0.20, 0.35, "#382566"), (0.28, 0.30, 0.28, "#2d1e56"),
                 (0.60, 0.70, 0.32, "#422358")]
        for rx, ry, rr, col in blobs:
            self.cv.create_oval(w * rx - w * rr, h * ry - h * rr,
                                w * rx + w * rr, h * ry + h * rr,
                                fill=col, outline="")

    def tick(self):
        """粒子动画循环"""
        if self.destroyed:
            return
        t = self._phase
        self._phase += 0.045

        # 星星闪烁呼吸
        for s in self.stars:
            b = 0.4 + 0.6 * (0.5 + 0.5 * math.sin(t * s["spd"] + s["phase"]))
            col = s["base"]
            try:
                r = int(col[1:3], 16)
                g = int(col[3:5], 16)
                bl = int(col[5:7], 16)
                nr = min(255, int(110 + (r - 110) * b))
                ng = min(255, int(110 + (g - 110) * b))
                nb = min(255, int(140 + (bl - 140) * b))
                self.cv.itemconfig(s["id"], fill="#%02x%02x%02x" % (nr, ng, nb))
            except Exception:
                pass

        # 樱花飘落
        for p in list(self.petals):
            p["y"] += p["v"]
            p["rot"] += 0.035 * p["v"]
            p["x"] += math.sin(p["rot"]) * p["sway"]
            if p["y"] - p["s"] > self.h:
                try:
                    self.cv.delete(p["id"])
                except Exception:
                    pass
                self.petals.remove(p)
                p["y"] = -8 - p["s"]
                p["x"] = random.uniform(0, max(self.w, 400))
                p["id"] = self._petal_oval(p)
                self.petals.append(p)
                continue
            try:
                self.cv.coords(p["id"],
                               p["x"] - p["s"], p["y"] - p["s"] * 0.65,
                               p["x"] + p["s"], p["y"] + p["s"] * 0.65)
            except Exception:
                pass

        if not self.destroyed:
            self.cv.after(40, self.tick)


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("JWGLXT AUTO · 湘潭大学教务选课自动化 (漆黑结界版)")
        self.geometry("1060x740")
        self.minsize(900, 620)
        self.configure(bg=BG)

        # 核心逻辑状态（必须完整保留）
        self.client = None
        self.worker = None
        self.stop_evt = None
        self.log_q = queue.Queue()
        self._running = False
        self._running_connect = False
        self.snapshot = None       # 抓取的全表缓存
        self.choosed_rows = []     # 已选课程列表（含 sksj）
        self.busy_slots = []       # 已选课全部时间槽（冲突检测基准）

        # 内部界面状态
        self._destroyed = False
        self._last_w = 0
        self._last_h = 0
        self._char_visible = True
        self._char_photo = None

        self.protocol("WM_DELETE_WINDOW", self._on_closing)
        self._build()
        self.after(100, self._drain_log)

        if tk is not None:
            self._sky = NightSky(self.sky)
            self._resize_sky()
            self.bind("<Configure>", self._on_resize)
            self.after(80, self._sky.tick)

    def _on_closing(self):
        self._destroyed = True
        if hasattr(self, "_sky"):
            self._sky.destroyed = True
        if self.stop_evt:
            self.stop_evt.set()
        self.destroy()

    # ---------------- UI 构建 ----------------
    def _card(self, parent, title, icon="✦"):
        """Galgame 风格卡片：顶部霓虹粉发光条 + 左侧星标 + 标题"""
        outer = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=14,
                             border_width=1, border_color=LINE)
        outer.pack(fill="x", pady=(0, 6))

        # 顶部霓虹光条
        glow = ctk.CTkFrame(outer, fg_color=ACCENT, height=2, corner_radius=0, width=1)
        glow.pack(fill="x", padx=10, pady=(4, 0))

        # 标题栏
        head = ctk.CTkFrame(outer, fg_color="transparent")
        head.pack(fill="x", padx=12, pady=(2, 2))
        ctk.CTkLabel(head, text=icon, text_color=ACCENT,
                     font=ctk.CTkFont(size=12, weight="bold")).pack(side="left")
        ctk.CTkLabel(head, text=f" {title}", text_color=TEXT,
                     font=ctk.CTkFont(family=TAG_FONT, size=11, weight="bold")).pack(side="left")
        ctk.CTkLabel(head, text="✧ · ✧", text_color=LINE_GLOW,
                     font=ctk.CTkFont(size=9)).pack(side="right")
        return outer

    def _btn(self, parent, text, cmd, color=None, height=30, border=None, bold=False):
        fg = color or CARD3
        hv = ACCENT_HOVER if color == ACCENT else CARD_HOVER
        tc = "#1c0915" if color == ACCENT else TEXT
        b = ctk.CTkButton(parent, text=text, command=cmd, height=height,
                          fg_color=fg, hover_color=hv,
                          border_width=1 if border else 0,
                          border_color=border or LINE,
                          corner_radius=9,
                          text_color=tc,
                          font=ctk.CTkFont(family=TAG_FONT, size=11,
                                           weight="bold" if bold else "normal"))
        b.pack(fill="x", padx=10, pady=2)
        return b

    def _build(self):
        # 1. 最底层全屏夜空与动态粒子画布
        self.sky = tk.Canvas(self, bg=BG, highlightthickness=0)
        self.sky.pack(fill="both", expand=True)

        # 2. 顶部主标题栏（高度 52px）
        head = ctk.CTkFrame(self, fg_color=CARD, corner_radius=12,
                            border_width=1, border_color=LINE, height=52)
        head.place(relx=0.015, rely=0.012, relwidth=0.97)

        # 左侧 LOGO 与徽章
        ctk.CTkLabel(head, text="❖", text_color=CRIMSON,
                     font=ctk.CTkFont(size=18, weight="bold")
                     ).place(relx=0.015, rely=0.5, anchor="w")
        ctk.CTkLabel(head, text="JWGLXT", text_color=TEXT,
                     font=ctk.CTkFont(family=TAG_FONT, size=16, weight="bold")
                     ).place(relx=0.042, rely=0.5, anchor="w")
        ctk.CTkLabel(head, text="AUTO", text_color=ACCENT,
                     font=ctk.CTkFont(family=TAG_FONT, size=16, weight="bold")
                     ).place(relx=0.145, rely=0.5, anchor="w")
        ctk.CTkLabel(head, text="「 湘大选课 · 漆黑结界 」", text_color=ACCENT2,
                     font=ctk.CTkFont(family=TAG_FONT, size=11)
                     ).place(relx=0.22, rely=0.5, anchor="w")

        # 中部副标
        ctk.CTkLabel(head, text="— ✧ 漆黑之誓 · 自动选课系统 ✧ —", text_color=DIM,
                     font=ctk.CTkFont(family=TAG_FONT, size=11)
                     ).place(relx=0.53, rely=0.5, anchor="center")

        # 右侧立绘折叠开关 + 状态指示灯
        self.btn_toggle_char = ctk.CTkButton(
            head, text="✦ 立绘", width=62, height=26,
            fg_color=CARD2, hover_color=CARD_HOVER,
            border_width=1, border_color=LINE,
            corner_radius=8, text_color=ACCENT,
            font=ctk.CTkFont(family=TAG_FONT, size=10),
            command=self._toggle_char_stage
        )
        self.btn_toggle_char.place(relx=0.825, rely=0.5, anchor="e")

        self.status_lbl = ctk.CTkLabel(
            head, text="○ [结界休眠 · 未连接]", text_color=DIM,
            font=ctk.CTkFont(family=TAG_FONT, size=12, weight="bold")
        )
        self.status_lbl.place(relx=0.98, rely=0.5, anchor="e")

        # 标题栏底部粉色发光细线
        head_line = ctk.CTkFrame(head, fg_color=ACCENT, height=2, width=1, corner_radius=0)
        head_line.place(relx=0, rely=1.0, relwidth=1.0, anchor="sw")

        # 3. 左栏控制核心（浮动卡片式面板，严格控制高度防止溢出）
        self.left_frame = ctk.CTkFrame(self, fg_color=CARD, corner_radius=14,
                                       border_width=1, border_color=LINE)
        self.left_frame.place(relx=0.015, rely=0.095, relwidth=0.34, relheight=0.885)

        # ---- 卡片 1: 契约回路 ----
        c1 = self._card(self.left_frame, "契约链路", "✧")
        self.btn_conn = self._btn(c1, "❖ 连接教务系统", self.connect, ACCENT, 32, bold=True)

        # 并排行 1: 抓取全表 + 班次透镜
        r1 = ctk.CTkFrame(c1, fg_color="transparent")
        r1.pack(fill="x", padx=10, pady=2)
        self.btn_crawl = ctk.CTkButton(
            r1, text="📜 抓取全表", command=self.crawl, height=28,
            fg_color=CARD3, hover_color=CARD_HOVER, corner_radius=8,
            text_color=TEXT, font=ctk.CTkFont(family=TAG_FONT, size=11)
        )
        self.btn_crawl.pack(side="left", fill="x", expand=True, padx=(0, 4))

        self.btn_view = ctk.CTkButton(
            r1, text="🔍 班次透镜", command=self.open_class_view, height=28,
            fg_color=CARD3, hover_color=CARD_HOVER, corner_radius=8,
            text_color=TEXT, font=ctk.CTkFont(family=TAG_FONT, size=11)
        )
        self.btn_view.pack(side="left", fill="x", expand=True, padx=(4, 0))

        # 并排行 2: 时段筛课 + 链路自检 + CDP验证 (紧凑 3 列)
        r2 = ctk.CTkFrame(c1, fg_color="transparent")
        r2.pack(fill="x", padx=10, pady=(2, 4))
        self.btn_tfilter = ctk.CTkButton(
            r2, text="⏳ 时段筛课", command=self.open_time_filter, height=28,
            fg_color=CARD3, hover_color=CARD_HOVER, corner_radius=8,
            text_color=TEXT, font=ctk.CTkFont(family=TAG_FONT, size=11)
        )
        self.btn_tfilter.pack(side="left", fill="x", expand=True, padx=(0, 3))

        self.btn_check = ctk.CTkButton(
            r2, text="⚡ 自检", command=self.selfcheck, height=28,
            fg_color=CARD3, hover_color=CARD_HOVER, corner_radius=8,
            text_color=DIM, font=ctk.CTkFont(family=TAG_FONT, size=10)
        )
        self.btn_check.pack(side="left", padx=2)

        self.btn_verify = ctk.CTkButton(
            r2, text="🗝 CDP", command=self.verify, height=28,
            fg_color=CARD3, hover_color=CARD_HOVER, corner_radius=8,
            text_color=DIM, font=ctk.CTkFont(family=TAG_FONT, size=10)
        )
        self.btn_verify.pack(side="left", padx=(3, 0))

        # ---- 卡片 2: 目标课程 ----
        c2 = self._card(self.left_frame, "捕获目标", "✦")
        self.kw = ctk.CTkEntry(
            c2, placeholder_text="关键词 (空格分隔) 例: 敦煌 光影 算法",
            height=30, fg_color=CARD2, border_color=LINE, text_color=TEXT,
            font=ctk.CTkFont(family=TAG_FONT, size=11)
        )
        self.kw.pack(fill="x", padx=10, pady=(2, 4))

        self.cat = {"10": True, "11": True, "01": False}
        self.cat_names = {"10": "通识选修", "11": "特殊课程", "01": "主修课程"}
        self.cat_icons = {"10": "❀", "11": "✦", "01": "♛"}

        # 选项卡 Canvas（高清晰度 44px 描边彩绘）
        self.cat_cv = tk.Canvas(c2, height=44, bg=CARD, highlightthickness=0)
        self.cat_cv.pack(fill="x", padx=10, pady=(0, 4))
        self.cat_cv.bind("<Button-1>", self._on_cat_click)
        self.cat_cv.bind("<Configure>", lambda e: self._draw_cat_tabs())
        self.after(150, self._draw_cat_tabs)

        # ---- 卡片 3: 咒术参数 ----
        c3 = self._card(self.left_frame, "运行参数", "◇")
        pr = ctk.CTkFrame(c3, fg_color="transparent")
        pr.pack(fill="x", padx=10, pady=(1, 2))

        ctk.CTkLabel(pr, text="轮询(s)", text_color=DIM,
                     font=ctk.CTkFont(family=TAG_FONT, size=11)).pack(side="left")
        self.interval = ctk.CTkEntry(
            pr, width=54, height=26, fg_color=CARD2, border_color=LINE,
            text_color=TEXT, corner_radius=7, font=ctk.CTkFont(size=11)
        )
        self.interval.insert(0, "1.5")
        self.interval.pack(side="left", padx=(4, 12))

        ctk.CTkLabel(pr, text="超时(s)", text_color=DIM,
                     font=ctk.CTkFont(family=TAG_FONT, size=11)).pack(side="left")
        self.timeout = ctk.CTkEntry(
            pr, width=64, height=26, fg_color=CARD2, border_color=LINE,
            text_color=TEXT, corner_radius=7, font=ctk.CTkFont(size=11)
        )
        self.timeout.insert(0, "1800")
        self.timeout.pack(side="left", padx=4)

        swrow = ctk.CTkFrame(c3, fg_color="transparent")
        swrow.pack(fill="x", padx=10, pady=(3, 5))
        self.dry_sw = ctk.CTkSwitch(
            swrow, text="预演模式", progress_color=ACCENT, border_width=1,
            border_color=LINE, fg_color=CARD3, button_color=ACCENT,
            button_hover_color=ACCENT_HOVER, font=ctk.CTkFont(family=TAG_FONT, size=11)
        )
        self.dry_sw.pack(side="left")
        self.dry_sw.select()

        self.cpx_sw = ctk.CTkSwitch(
            swrow, text="组合实践", progress_color=ACCENT, border_width=1,
            border_color=LINE, fg_color=CARD3, button_color=ACCENT,
            button_hover_color=ACCENT_HOVER, font=ctk.CTkFont(family=TAG_FONT, size=11)
        )
        self.cpx_sw.pack(side="left", padx=(14, 0))

        # ---- 操作主按钮（高亮大按钮 + 停止按钮） ----
        self.btn_start = ctk.CTkButton(
            self.left_frame, text="✦ 展开结界 · 启动抢课 ✦", height=40,
            fg_color=ACCENT, hover_color=ACCENT_HOVER, corner_radius=11,
            border_width=1, border_color="#ffe0ec",
            text_color="#200a16",
            font=ctk.CTkFont(family=TAG_FONT, size=14, weight="bold"),
            command=self.start
        )
        self.btn_start.pack(fill="x", padx=12, pady=(4, 4))
        self.btn_start.configure(state="disabled")

        self.btn_stop = ctk.CTkButton(
            self.left_frame, text="✧ 撤除结界 · 停止 ✧", height=32,
            fg_color="transparent", hover_color="#361726",
            border_width=1, border_color=ERR, text_color=ERR,
            corner_radius=9,
            font=ctk.CTkFont(family=TAG_FONT, size=12, weight="bold"),
            command=self.stop
        )
        self.btn_stop.pack(fill="x", padx=12, pady=(0, 6))
        self.btn_stop.configure(state="disabled")

        # 4. 中栏/右栏：Galgame 对话框风格日志终端
        self.log_frame = ctk.CTkFrame(self, fg_color=CARD, corner_radius=14,
                                      border_width=1, border_color=LINE)

        # 终端卡片顶部工具条
        log_head = ctk.CTkFrame(self.log_frame, fg_color="transparent")
        log_head.pack(fill="x", padx=12, pady=(6, 4))
        ctk.CTkLabel(
            log_head, text="✧ 魂之回响 · 实时结界日志 ✧", text_color=ACCENT2,
            font=ctk.CTkFont(family=TAG_FONT, size=11, weight="bold")
        ).pack(side="left")

        self.btn_clear_log = ctk.CTkButton(
            log_head, text="清空", width=46, height=22,
            fg_color=CARD2, hover_color=CARD_HOVER, corner_radius=6,
            text_color=DIM, font=ctk.CTkFont(family=TAG_FONT, size=10),
            command=self._clear_log
        )
        self.btn_clear_log.pack(side="right")

        self.log_box = ctk.CTkTextbox(
            self.log_frame, fg_color="#100c1e", border_color=LINE,
            border_width=1, corner_radius=10, wrap="none",
            font=ctk.CTkFont(family=MONO_FONT, size=11),
            text_color=TEXT
        )
        self.log_box.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        for tag, color in LV_COLOR.items():
            self.log_box.tag_config(tag, foreground=color)
        self.log_box.tag_config("t", foreground="#786c99")
        self.log_box.tag_config("ruby", foreground=CRIMSON)

        # 5. 右栏：美少女立绘展台（Stage）
        self.char_stage = ctk.CTkFrame(self, fg_color=CARD, corner_radius=14,
                                       border_width=1, border_color=LINE)

        # 立绘卡片顶部发光条
        cglow = ctk.CTkFrame(self.char_stage, fg_color=CRIMSON, height=2, width=1, corner_radius=0)
        cglow.pack(fill="x", padx=10, pady=(4, 0))

        char_head = ctk.CTkFrame(self.char_stage, fg_color="transparent")
        char_head.pack(fill="x", padx=10, pady=(2, 2))
        ctk.CTkLabel(
            char_head, text="✦ 影华", text_color=ACCENT,
            font=ctk.CTkFont(family=TAG_FONT, size=11, weight="bold")
        ).pack(side="left")
        ctk.CTkLabel(
            char_head, text="结界守护者", text_color=DIM,
            font=ctk.CTkFont(family=TAG_FONT, size=10)
        ).pack(side="right")

        # 立绘 Canvas（可交互点击）
        self.char_cv = tk.Canvas(self.char_stage, bg=CARD, highlightthickness=0)
        self.char_cv.pack(fill="both", expand=True, padx=6, pady=(0, 4))
        self.char_cv.bind("<Button-1>", self._on_char_click)
        self.char_cv.bind("<Configure>", lambda e: self._render_char_portrait())

        char_foot = ctk.CTkFrame(self.char_stage, fg_color=CARD2, corner_radius=6, height=22)
        char_foot.pack(fill="x", padx=8, pady=(0, 6))
        ctk.CTkLabel(
            char_foot, text="● 契约连通 · 点击互动", text_color=OK,
            font=ctk.CTkFont(family=TAG_FONT, size=9)
        ).pack(expand=True)

        self._update_panel_layout()

        # 初始欢迎辞
        welcome_banner = "✧· ──────────────── ✦ 漆 黑 课 程 结 界 启 动 ✦ ──────────────── ·✧\n"
        self.log_box.insert("end", welcome_banner, "t")
        self._log("✨ 欢迎回来，主人。湘潭大学自动化选课结界已就绪。", "ok")
        self._log("🔮 请先点击「❖ 连接教务系统」，随后「📜 抓取全表」，输入目标关键词开始狙击吧。")

    def _update_panel_layout(self):
        """根据是否展开立绘展台动态调整日志与立绘布局"""
        if self._char_visible:
            self.log_frame.place(relx=0.365, rely=0.095, relwidth=0.395, relheight=0.885)
            self.char_stage.place(relx=0.77, rely=0.095, relwidth=0.215, relheight=0.885)
            self.btn_toggle_char.configure(text="✕ 收起立绘")
            self.after(60, self._render_char_portrait)
        else:
            self.char_stage.place_forget()
            self.log_frame.place(relx=0.365, rely=0.095, relwidth=0.62, relheight=0.885)
            self.btn_toggle_char.configure(text="✦ 展开立绘")

    def _toggle_char_stage(self):
        self._char_visible = not self._char_visible
        self._update_panel_layout()

    def _render_char_portrait(self):
        """在立绘 Canvas 中高质量平滑渲染美少女插画"""
        if not self._char_visible or self._destroyed:
            return
        cw = self.char_cv.winfo_width()
        ch = self.char_cv.winfo_height()
        if cw < 30 or ch < 30:
            return

        src_path = ASSET_CHAR if os.path.exists(ASSET_CHAR) else ASSET_BG
        if not os.path.exists(src_path):
            return

        try:
            im = Image.open(src_path).convert("RGBA")
            im_ratio = im.width / im.height
            target_ratio = cw / ch

            if im_ratio > target_ratio:
                new_w = int(im.height * target_ratio)
                crop_x = int((im.width - new_w) * 0.5)
                im = im.crop((crop_x, 0, crop_x + new_w, im.height))
            else:
                new_h = int(im.width / target_ratio)
                im = im.crop((0, 0, im.width, new_h))

            im = im.resize((cw, ch), Image.Resampling.LANCZOS)
            self._char_photo = ImageTk.PhotoImage(im)
            self.char_cv.delete("all")
            self.char_cv.create_image(0, 0, image=self._char_photo, anchor="nw")
        except Exception:
            pass

    def _on_char_click(self, ev):
        """点击立绘触发二次元专属互动语音台词"""
        quotes = [
            "✨ 影华：「主人，今天的选课战场，就交由我为您扫清障碍吧！」",
            "🔮 影华：「时刻注视着湘大教务系统的魔力流向，任何漏网之课都逃不过我的眼睛。」",
            "⚔️ 影华：「无论是多么热门的通识选修，我都会替主人狠狠拿下的！」",
            "🌙 影华：「夜深了，主人辛苦了……请放心地把选课任务交给我吧。」",
            "🌸 影华：「已为您展开命运避冲结界，时间冲突的课程已被隔绝在外。」",
        ]
        self._log(random.choice(quotes), "star")

    def _clear_log(self):
        self.log_box.delete("1.0", "end")
        self.log_box.insert("end", "✧ 日志已清空 ✧\n", "t")

    def _on_resize(self, ev):
        if ev.widget is self and tk is not None and not self._destroyed:
            cur = (self.winfo_width(), self.winfo_height())
            if cur != (self._last_w, self._last_h):
                self._resize_sky()

    def _resize_sky(self):
        if self._destroyed:
            return
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        self._last_w, self._last_h = w, h
        if w > 10 and h > 10 and hasattr(self, "_sky"):
            self._sky.init(w, h)

    # ---------------- 彩绘选项卡（canvas） ----------------
    def _round_rect(self, cv, x0, y0, x1, y1, r, **kw):
        pts = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1,
               x1 - r, y1, x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]
        return cv.create_polygon(pts, smooth=True, **kw)

    def _draw_cat_tabs(self):
        """重构彩绘描边选项卡：11pt 加粗字体、右上角绯红灵魂宝石红点、高辨识度"""
        if self._destroyed:
            return
        cv = self.cat_cv
        cv.delete("all")
        w = cv.winfo_width()
        h = cv.winfo_height()
        if w < 40 or h < 20:
            return

        n = len(self.cat_names)
        gap = 6
        tw = (w - gap * (n - 1) - 4) / n
        self.cat_geo = []

        for i, (k, name) in enumerate(self.cat_names.items()):
            x0 = 2 + i * (tw + gap)
            y0 = 3
            x1 = x0 + tw
            y1 = h - 3
            on = self.cat[k]

            bg = "#351b3f" if on else "#19142c"
            bd = ACCENT if on else "#322752"
            self._round_rect(cv, x0, y0, x1, y1, 10, fill=bg, outline=bd,
                             width=2 if on else 1)

            cx = (x0 + x1) / 2
            cy = (y0 + y1) / 2

            if on:
                # 选中态：右上角绯红灵魂宝石红点（●）
                gem_x = x1 - 9
                gem_y = y0 + 8
                cv.create_oval(gem_x - 4, gem_y - 4, gem_x + 4, gem_y + 4,
                               fill=CRIMSON, outline="#ffa0ba", width=1.5)
                cv.create_oval(gem_x - 2, gem_y - 2, gem_x, gem_y,
                               fill="#ffffff", outline="")

                # 左下角星光点缀
                sx = x0 + 8
                sy = y1 - 8
                cv.create_line(sx - 3, sy, sx + 3, sy, fill=ACCENT2, width=1)
                cv.create_line(sx, sy - 3, sx, sy + 3, fill=ACCENT2, width=1)

                # 图标与文字：大字号、高对比
                cv.create_text(cx, cy - 8, text=self.cat_icons[k],
                               fill=ACCENT,
                               font=("Microsoft YaHei UI", 12, "bold"))
                cv.create_text(cx, cy + 9, text=name,
                               fill="#ffffff",
                               font=("Microsoft YaHei UI", 10, "bold"))
            else:
                # 未选中态：熄灭暗孔
                gem_x = x1 - 9
                gem_y = y0 + 8
                cv.create_oval(gem_x - 3, gem_y - 3, gem_x + 3, gem_y + 3,
                               fill="#1d1630", outline="#3c3258")

                cv.create_text(cx, cy - 8, text=self.cat_icons[k],
                               fill="#7f759e",
                               font=("Microsoft YaHei UI", 11))
                cv.create_text(cx, cy + 9, text=name,
                               fill="#8f84af",
                               font=("Microsoft YaHei UI", 10))

            self.cat_geo.append((x0, y0, x1, y1, k))

    def _on_cat_click(self, ev):
        for x0, y0, x1, y1, k in getattr(self, "cat_geo", []):
            if x0 <= ev.x <= x1 and y0 <= ev.y <= y1:
                self.cat[k] = not self.cat[k]
                self._draw_cat_tabs()
                return

    # ---------------- 日志系统 ----------------
    def _log(self, text, level="info"):
        self.log_q.put((text, level))

    def _drain_log(self):
        if self._destroyed:
            return
        try:
            while True:
                text, level = self.log_q.get_nowait()
                ts = time.strftime("%H:%M:%S")
                self.log_box.insert("end", f"[{ts}] ", "t")
                self.log_box.insert("end", text + "\n", level)
                self.log_box.see("end")
        except queue.Empty:
            pass
        if not self._destroyed:
            self.after(100, self._drain_log)

    def _status(self, text, color):
        self.status_lbl.configure(text=f"● [{text}]", text_color=color)

    # ---------------- 会话与连接 ----------------
    def connect(self):
        if self._running_connect:
            return
        self._running_connect = True
        self.btn_conn.configure(state="disabled")
        self._status("回路同步中...", WARN)
        threading.Thread(target=self._connect_worker, daemon=True).start()

    def _connect_worker(self):
        try:
            self._log("✦ 正在侦测 Chrome 调试会话，必要时自动召唤托管实例...", "star")
            self.client, _ = grab.init_client(spawn=True, log=self._log)
            self._log(f"✨ 教务回路连接成功: tabs={list(self.client.tabs)} "
                      f"rwlx={self.client._h('rwlx') or '?'} "
                      f"xklc={self.client._h('xklc') or '?'}", "ok")
            try:
                rows = self.client.get_choosed()
                self.choosed_rows = rows
                self.busy_slots = []
                for r in rows:
                    self.busy_slots += parse_sksj(r.get("sksj") or "")
                self._log(f"📚 已选课捕获: 共 {len(rows)} 门，占用时间槽 {len(self.busy_slots)} 段 "
                          f"（作为避冲基准）", "ok")
            except Exception as e:
                self._log(f"⚠️ 已选课获取遇到轻微阻碍: {e}", "warn")
            self.btn_start.configure(state="normal")
            self._status("结界展开 · 已连接", OK)
        except Exception as e:
            self._log(f"❌ 连接失败: {e}", "err")
            self._status("回路阻断 · 失败", ERR)
        finally:
            self._running_connect = False
            self.btn_conn.configure(state="normal")

    def crawl(self):
        if not self.client:
            self._log("⚠️ 请先点击「连接教务系统」", "warn")
            return
        self._log("📜 正在全面扫描教务课程全表（获取班次/时间/地点/余量）...", "star")
        try:
            kklxdms = sorted(self.client.tabs.keys())
            snap = grab.fetch_full_snapshot(self.client, kklxdms, self._log, detail=True)
            self.snapshot = snap
            self._log(f"✨ 全表解析完成: 共捕获 {len(snap)} 门课程（类别 {kklxdms}）", "ok")
        except Exception as e:
            self._log(f"❌ 抓取失败: {e}", "err")

    def selfcheck(self):
        if not self.client:
            self._log("⚠️ 请先连接教务系统", "warn")
            return
        try:
            rows = self.client.get_choosed()
            self._log(f"⚡ 链路自检通过: 当前已选 {len(rows)} 门课程", "ok")
            for r in rows[:8]:
                self._log(f"   已选: {r.get('kcmc')}", "dim")
            if len(rows) > 8:
                self._log(f"   ... 共 {len(rows)} 门", "dim")
        except Exception as e:
            self._log(f"❌ 自检失败: {e}", "err")

    def verify(self):
        try:
            cookies = cdp_get_cookies(get_cdp_ws_url())
            jw = [c for c in cookies if JW_HOST in (c.get("domain") or "")]
            self._log(f"🗝 CDP 会话验证: 共 {len(cookies)} 个 Cookie，教务域凭据 {len(jw)} 枚", "ok")
        except Exception as e:
            self._log(f"❌ CDP 验证失败: {e}", "err")

    # ---------------- 弹窗窗口统一二次元美学 ----------------
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
        win.title(f"✦ {title} · 漆黑结界 ✦")
        win.geometry("920x600")
        win.configure(fg_color=BG)

        # 顶部渐变标题卡
        top_bar = ctk.CTkFrame(win, fg_color=CARD, corner_radius=10,
                              border_width=1, border_color=LINE)
        top_bar.pack(fill="x", padx=12, pady=(12, 6))

        glow = ctk.CTkFrame(top_bar, fg_color=ACCENT, height=2, corner_radius=0, width=1)
        glow.pack(fill="x", padx=10, pady=(3, 0))

        bar_inner = ctk.CTkFrame(top_bar, fg_color="transparent")
        bar_inner.pack(fill="x", padx=12, pady=6)
        ctk.CTkLabel(
            bar_inner, text=f"❖ {title}", text_color=TEXT,
            font=ctk.CTkFont(family=TAG_FONT, size=13, weight="bold")
        ).pack(side="left")
        ctk.CTkLabel(
            bar_inner, text="✧ 命运观测仪 ✧", text_color=ACCENT2,
            font=ctk.CTkFont(family=TAG_FONT, size=11)
        ).pack(side="right")

        # 结果内容框
        box = ctk.CTkTextbox(
            win, fg_color="#100c1e", border_color=LINE,
            border_width=1, corner_radius=12, wrap="none",
            font=ctk.CTkFont(family=MONO_FONT, size=12),
            text_color=TEXT
        )
        box.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        box.tag_config("head", foreground="#ffa8c9")
        box.tag_config("conflict", foreground=ERR)
        box.tag_config("ok", foreground=OK)
        box.tag_config("dim", foreground=DIM)
        box.tag_config("info", foreground=ACCENT2)
        box.tag_config("warn", foreground=WARN)

        win._box = box
        win._top_bar = bar_inner
        return win

    def open_class_view(self):
        if self.client is None:
            self._log("⚠️ 请先连接教务系统", "warn")
            return
        if not self.snapshot:
            self._log("⚠️ 请先抓取全表，才能透镜定位课程", "warn")
            return

        win = self._mk_view_win("课程班次透镜")
        tool = ctk.CTkFrame(win, fg_color="transparent")
        tool.pack(fill="x", padx=12, pady=(0, 8), before=win._box)

        ctk.CTkLabel(tool, text="课程关键词:", text_color=TEXT,
                     font=ctk.CTkFont(family=TAG_FONT, size=12)).pack(side="left")
        kw = ctk.CTkEntry(tool, width=280, height=30, fg_color=CARD2,
                          border_color=LINE, text_color=TEXT)
        kw.pack(side="left", padx=(8, 8))

        ctk.CTkButton(
            tool, text="🔍 查询", width=80, height=30,
            fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color="#200a16",
            font=ctk.CTkFont(family=TAG_FONT, size=11, weight="bold"),
            command=lambda: self._render_class_view(kw.get().strip(), win)
        ).pack(side="left")

        kw.bind("<Return>", lambda e: self._render_class_view(kw.get().strip(), win))
        win._box.insert("end", "🔮 输入课程名或课程号关键词，按回车进行实时班次透析（含冲突避让标记）\n", "dim")
        kw.focus_set()

    def _render_class_view(self, text, win):
        box = win._box
        box.delete("1.0", "end")
        if not text:
            box.insert("end", "⚠️ 请输入课程名或课程号关键词后查询\n", "dim")
            return
        hits = grab.match_courses(self.snapshot, text.split())
        if not hits:
            box.insert("end", f"✗ 全表魔力范围内未检索到包含「{text}」的课程\n", "conflict")
            return

        for kch_id, c in hits[:12]:
            box.insert("end", f"❖ {c['kcmc']}（{c['kch']} · {c['xf']}学分）\n", "head")
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
                    mark = f"✗ 冲突: 与已选「{conf}」重叠"
                else:
                    tag = "ok"
                    mark = "✓ 结界通畅 · 可抢"
                yl = f"{safe}" if safe >= 0 else "?"
                box.insert("end",
                           f"  [{jb.get('jxb_id','')[:8]}] {st} | "
                           f"{jb.get('jxdd') or '?'} | {teacher} | "
                           f"余量 {yl}/{rl or '?'} | {mark}\n", tag)
            box.insert("end", "\n")

        if len(hits) > 12:
            box.insert("end", f"... 还有 {len(hits) - 12} 门课程未展开，请使用更精确的关键词\n", "dim")

    def open_time_filter(self):
        if self.client is None:
            self._log("⚠️ 请先连接教务系统", "warn")
            return
        if not self.snapshot:
            self._log("⚠️ 请先抓取全表，才能按时空筛课", "warn")
            return

        win = self._mk_view_win("时空相位筛课")
        tool = ctk.CTkFrame(win, fg_color="transparent")
        tool.pack(fill="x", padx=12, pady=(0, 8), before=win._box)

        ctk.CTkLabel(tool, text="星期:", text_color=TEXT,
                     font=ctk.CTkFont(family=TAG_FONT, size=12)).pack(side="left")
        days = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        day_menu = ctk.CTkOptionMenu(
            tool, values=days, width=86, height=28,
            fg_color=CARD2, button_color=ACCENT, button_hover_color=ACCENT_HOVER,
            text_color=TEXT
        )
        day_menu.set("周一")
        day_menu.pack(side="left", padx=(6, 12))

        ctk.CTkLabel(tool, text="节次:", text_color=TEXT,
                     font=ctk.CTkFont(family=TAG_FONT, size=12)).pack(side="left")
        seg_menu = ctk.CTkOptionMenu(
            tool, values=["1-2", "3-4", "5-6", "7-8", "9-10", "11-12"],
            width=86, height=28, fg_color=CARD2,
            button_color=ACCENT, button_hover_color=ACCENT_HOVER,
            text_color=TEXT
        )
        seg_menu.set("3-4")
        seg_menu.pack(side="left", padx=(6, 12))

        ctk.CTkButton(
            tool, text="🔮 相位筛选", width=90, height=28,
            fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color="#200a16",
            font=ctk.CTkFont(family=TAG_FONT, size=11, weight="bold"),
            command=lambda: self._render_time_filter(
                win, days.index(day_menu.get()) + 1,
                *map(int, seg_menu.get().split("-"))
            )
        ).pack(side="left")

        win._box.insert("end", "选定星期与节次后点击「相位筛选」：顶部列出主人该时段已有课程，下方列出可支配课程\n", "dim")

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
            box.insert("end", f"★ 该时段主人已选课程（{len(mine)} 门）：\n", "warn")
            for r in mine[:10]:
                box.insert("end", f"    {r.get('kcmc')} | {slots_str(parse_sksj(r.get('sksj') or ''))}\n", "dim")
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
            box.insert("end", f"❖ {c['kcmc']}（{c['kch']} · {c['xf']}分 · {len(c['classes'])}个班）\n", "head")

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
                    mark = "✓ 结界通畅 · 可抢"
                yl = f"{safe}" if safe >= 0 else "?"
                box.insert("end",
                           f"  {st} | {cls.get('jxdd') or '?'} | "
                           f"余量 {yl}/{rl or '?'} | {mark}\n", tag)
            box.insert("end", "\n")

        if count == 0:
            box.insert("end", "该时段未观测到可用课程\n", "dim")
        else:
            box.insert("end", f"共检索到 {count} 门课程在该时段开放\n", "info")

    # ---------------- 抢课核心任务 ----------------
    def _opts(self):
        kw = self.kw.get().strip()
        if not kw:
            self._log("⚠️ 请先输入目标课程关键词", "warn")
            return None
        kklxdms = [k for k, on in self.cat.items() if on]
        if not kklxdms:
            self._log("⚠️ 请至少选择一种课程类别（通识/特殊/主修）", "warn")
            return None
        try:
            interval = float(self.interval.get() or 1.5)
            timeout = int(self.timeout.get() or 1800)
        except ValueError:
            self._log("❌ 轮询间隔与超时必须是有效数字", "err")
            return None
        return {
            "keywords": kw.split(),
            "kklxdms": kklxdms,
            "interval": interval,
            "timeout": timeout,
            "dry_run": bool(self.dry_sw.get()),
            "try_complex": bool(self.cpx_sw.get())
        }

    def start(self):
        if self._running:
            self._log("⚠️ 已有结界抢课任务正在执行中", "warn")
            return
        opts = self._opts()
        if opts is None:
            return
        self._running = True
        self.stop_evt = threading.Event()
        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self._status("魔力全开 · 抢课中", ACCENT)

        self.worker = threading.Thread(target=self._worker, args=(opts,), daemon=True)
        self.worker.start()

    def _worker(self, opts):
        try:
            mode = "预演演练" if opts["dry_run"] else "实战抢课"
            self._log(f"⚔️ 抢课结界启动 [{mode}]: 目标={opts['keywords']} "
                      f"类别={opts['kklxdms']} 间隔={opts['interval']}s", "star")
            grab.run_grab(
                opts["keywords"], kklxdms=opts["kklxdms"],
                interval=opts["interval"], timeout=opts["timeout"],
                dry_run=opts["dry_run"], try_complex=opts["try_complex"],
                log=self._log, stop_event=self.stop_evt
            )
        except Exception as e:
            self._log(f"❌ 任务发生异常: {e}", "err")
        finally:
            self._running = False
            if self.client:
                self.btn_start.configure(state="normal")
            self.btn_stop.configure(state="disabled")
            self._status("结界展开 · 已连接" if self.client else "结界休眠 · 未连接",
                         OK if self.client else DIM)
            self._log("✧ 抢课结界任务平息 ✧", "info")

    def stop(self):
        if self.stop_evt:
            self.stop_evt.set()
            self._log("🛑 已发送停止信号，将在本轮回路结束后退出", "warn")


def main():
    if ctk is None:
        print("缺少 customtkinter: pip install customtkinter pillow")
        sys.exit(1)
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
