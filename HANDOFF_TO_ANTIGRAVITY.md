# JWGLXT AUTO · 前端交接文档（给 Antigravity）

> 目标：把现有的 customtkinter 前端重做成**浓厚的二次元风格**，功能一个都不能丢。
> 本文档由 Mako（主开发助手）撰写。项目已 git 初始化，**禁止 push**，改完本地跑通给主人看。

---

## 1. 项目一句话

湘潭大学正方教务系统选课自动化工具。Python 桌面程序：CDP 读浏览器登录态 → 直打教务接口 → 抢课，附带冲突检测与课程筛选。

## 2. 仓库位置与文件职责

路径：`D:\hanako\jwglxt-auto-course`

| 文件 | 职责 | 能否动 |
|---|---|---|
| `gui_app.py` | **你要改的前端**（customtkinter GUI） | ✅ 随便改 |
| `grab.py` | 核心抢课逻辑 + 全表抓取（API 给 GUI 用） | ❌ 只读调用 |
| `jw_cdp_client.py` | CDP 会话 / 教务接口封装（库） | ❌ 只读调用 |
| `schedule.py` | 排课时间引擎：sksj 解析 + 冲突判定 | ❌ 只读调用 |
| `crawl_all.py` / `test_*.py` / `verify_cdp.py` | 工具脚本 | 不用管 |
| `README.md` | 使用说明 | 可顺手同步 |

## 3. 运行方式

```bash
cd D:\hanako\jwglxt-auto-course
python gui_app.py        # 需要: customtkinter, requests, websocket-client, PIL
```

机器已装好依赖（Python 3.12.10）。启动即可，会弹出「JWGLXT AUTO · 教务选课自动化」窗口。

## 4. GUI 现有结构（重写前先读懂）

`gui_app.py` 只有一个主类 `App(ctk.CTk)`。当前架构：

```
App (customtkinter 主窗口 1060x740)
├── NightSky 类：tk.Canvas 铺满窗口作背景
│   ├── 程序化夜空：蓝紫渐变 / 星云光晕 / 52颗闪烁星星 / 26片飘落樱花
│   └── 右下角：黑长直少女背影剪影 + 一缕红眼微光（canvas 手绘）
├── head 标题栏（place 定位）：✦ JWGLXT(白) AUTO(粉) ✦ 教务选课自动化 ✦ + 状态灯 + 底部发光细线
├── left 左栏（place 定位，relwidth 0.345）：
│   ├── 会话卡：连接浏览器(粉) / 抓取全表 / 查看班次 / 时段筛课 / [链路自检+CDP验证 并排]
│   ├── 目标课程卡：关键词输入框 + canvas 彩绘选项卡（❀通识 ✦特殊 ♛主修）
│   ├── 参数卡：轮询间隔/超时输入 + 预演/组合实践开关（并排）
│   └── 开始(粉,大) / 停止(红描边)
└── 右栏日志：CTkTextbox（圆角深色卡片）
    └── 弹窗窗口 _mk_view_win：课程班次查看 / 时段筛课 结果展示
```

**关键坑（务必读）**：
1. `customtkinter` 的 `place()` 方法**不接受 width/height 参数**，尺寸必须传给构造函数（如 `CTkFrame(..., height=58)`）。这是上一轮崩溃的原因。
2. 左栏是 `place` 相对定位 + 内部 `pack` 流式排列。**内容总高曾多次超过可视高度**，导致「开始/停止」被裁掉、点不到。当前已压缩过，但窗口 resize 或改样式时极易复发——请保证左栏内容总高 < 可视高度（建议预留 ≥30px 富余）。
3. `tk.Canvas` 与 CTk 组件混用没问题，但 canvas 需要 `bg=CARD` 与卡片同色融合。
4. 选项卡是 `tk.Canvas` 手绘（`_draw_cat_tabs` / `_round_rect` / `_paint_tab_motif` / `_on_cat_click`），带樱花底纹和图标。**目前文字是 9 号字，主人反馈辨识度低**，可放大或改布局。
5. `after()` 定时重绘（星星/樱花动画、`_drain_log` 日志队列、`_draw_cat_tabs` 尺寸兜底）——关窗口时别让回调崩在已销毁的 canvas 上。

## 5. GUI 能用的全部数据/接口（逻辑层已封装好，直接调）

```python
# 连接（含自动拉起托管 Chrome → 门户登录 → 自动开选课页）
client, ws = grab.init_client(spawn=True, log=self._log)   # 返回须存 self.client

# 已选课程 + 时间槽（冲突基准）
rows = client.get_choosed()                 # [{kcmc, kch_id, jxb_id, sksj, ...}]
busy_slots = []                             # 对每行 parse_sksj(r['sksj']) 累加

# 抓全表（detail=True 会逐课补时间/地点/教师，503门约90秒，有进度日志回调）
snap = grab.fetch_full_snapshot(client, kklxdms, log, detail=True)
# 返回 {kch_id: {kch, kcmc, jxbzls, xf, kklxdm, classes:[{jxb_id,jxbmc,yxzrs,cxbj,sksj,jxdd,jsxx,jxbrl}]}}

# 关键词匹配 / 单课班次实时查
hits = grab.match_courses(snap, keywords)   # [(kch_id, course)]
jxbs = client.get_jxbs(kch_id, kklxdm)      # [jxb...] 完整班次

# 时间引擎
from schedule import parse_sksj, slots_str, any_conflict
slots = parse_sksj(sksj_str)                # sksj: '星期六第3-4节{2-4周,6-10周}' 可多段<br/>分隔
text  = slots_str(slots)                    # '周六 3-4节(2-4,6-10周)'
conf  = any_conflict(slots, busy_slots)     # 与已选课是否冲突

# 抢课开跑（GUI 里放线程 + stop_event）
stop_evt = threading.Event()
grab.run_grab(keywords, kklxdms=[...], interval=1.5, timeout=1800,
              dry_run=True, try_complex=False, log=self._log,
              stop_event=stop_evt)
```

窗口标题、按钮文本、日志文案可以自由改（主人喜欢二次元腔调），**但 `self.client / snapshot / choosed_rows / busy_slots / stop_evt / _running` 这些状态字段的语义别动**，逻辑层靠它们联动。

## 6. 主人审美需求（核心标准）

- **黑长直 + 红眼 + 暗黑系美少女**，少萝风格加分
- 暗色系：深蓝紫夜空（#0d0b18 附近），樱花粉（#ff77a9）+ 星辉紫（#b388ff）点缀
- 氛围感是灵魂：galgame / 深夜 / 结界 / 魔法阵那一挂，要"浓厚"不要"亮色小清新"
- 卡片式面板浮在星空背景上（像 galgame 对话框）
- 日志腔调可以二次元化（如"✨ 欢迎回来，主人""课程结界启动"）

## 7. 待改进方向（主人原话汇总）

1. 整体**二次元浓度还不够**，要更像"美少女插画风界面"（可考虑：PIL 预生成美少女立绘/插画背景 + 粒子动画叠加，比纯 canvas 手绘更出效果）
2. **选项卡**要更好看：二次元美少女描边彩绘风（背景插画/描边花纹），文字要大要清楚
3. 弹窗窗口（班次查看/时段筛课）也要统一二次元风格，目前只是纯色卡片
4. 布局禁止再"畸形"：任何界面元素（尤其按钮）必须完整可见、可点击
5. 保持暗色 + 粉紫主调，功能不变

## 8. 验证清单（改完自测）

- [ ] `python gui_app.py` 无报错启动
- [ ] 窗口 1060x740 下左栏所有元素完整可见可点（会话/目标/参数/开始/停止）
- [ ] 窗口缩到 900x620 不畸形
- [ ] 选项卡点击切换正常（红点跟随：选中态明显）
- [ ] 背景动画流畅不卡（星星/花瓣帧率）
- [ ] 弹窗（班次查看/时段筛课）风格统一、内容可读
- [ ] 日志滚动、状态灯无异常

## 9. 红线

- **不要改** grab / jw_cdp_client / schedule 三个逻辑文件的函数行为（前端只做展示与调用）
- **不要 git push**（主人明确要求：先本地改好、测好）
- 改完本地 commit 即可，交付主人实测

---

*交接人：Mako · 2026-09-04*