# jwglxt-auto-course

正方教务系统（JWGLXT）选课接口的自动化工具，日常选课辅助。

> 定位：个人账号的选课操作自动化。使用前请确认符合本校教学管理规定，风险自负。

## 功能

- **会话复用**：通过 Chrome DevTools 协议从你的浏览器实时读取登录会话，无需手动维护 cookie
- **课程检索**：单次请求获取当前学期的全部可选课程，按关键词匹配目标
- **已选查重**：提交前自动过滤已选课程（只做加法，不做减法）
- **抢课循环**：实时获取操作参数 → 自动选班 → 提交 → 按返回状态分类处理，支持轮询间隔、超时控制、预演模式
- **图形界面**：内置 GUI（customtkinter），打包为 exe 后可双击开界面

## 快速开始（三选一）

### A. 直接下载 exe（无需安装 Python）

1. 从 Releases 下载 `jwglxt-gui.exe`（图形版）或 `jwglxt-cli.exe`（命令行版）
2. 运行 exe，点击「连接浏览器」
3. 程序会自动拉起一个独立的 Chrome 窗口（不影响你日常使用的 Chrome），
   在窗口中登录教务系统并打开选课页即可
4. 程序检测到登录态后自动继续，输入关键词开始选课

### B. 源码运行

```bash
pip install -r requirements.txt
python gui_app.py              # 图形界面
python grab.py "关键词" --dry-run   # 命令行（预演）
```

### C. 自己打包 exe

```bash
pip install pyinstaller
pyinstaller --onefile --name jwglxt-cli grab.py
pyinstaller --onefile --windowed --name jwglxt-gui --collect-data customtkinter gui_app.py
```

## 界面操作流程

「连接浏览器」→ 程序自动拉起独立 Chrome 并等待登录（或复用已有的托管实例，
登录态保留）→ 检测成功后状态变绿 → 抓取全表 → 输入关键词、
勾选类别、调参数（预演模式默认开启，确认无误后取消勾选）→ 开始。
日志面板实时显示进程，`停止` 可在本轮结束后退出。

## 常用参数

| 参数 | 说明 |
|---|---|
| `--interval` | 轮询间隔（默认 1.5s） |
| `--timeout` | 总超时（默认 1800s） |
| `--kklxdm` | 目标类别，逗号分隔（默认 10,11） |
| `--try-complex` | 尝试组合含实践学时的父子教学班 |
| `--dry-run` | 预演模式，不提交 |

## 目录结构

```
jw_cdp_client.py    # 会话复用 + 接口封装（库）
grab.py             # 核心逻辑（CLI + GUI 共用）
gui_app.py          # 图形界面（customtkinter）
crawl_all.py        # 课程全表抓取 → data/ 快照
test_submit.py      # 提交链路最小验证
test_submit3.py     # 提交链路完整验证（含前后对比，零减法检查）
verify_cdp.py       # 会话链路最小验证
data/               # 课程快照（gitignore，不入库）
```

## 注意事项

- **只做加法**：工具不会发起任何退课/删除操作，退课请手动进行
- 使用前请打开教务选课页面，工具需要从浏览器中读取选课环境参数
- 自动化选课可能违反部分学校的管理规定，请自行评估风险

## License

MIT