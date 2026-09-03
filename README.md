# jwglxt-auto-course

正方教务系统（JWGLXT）选课接口的自动化工具，日常选课辅助。

> 定位：个人账号的选课操作自动化。使用前请确认符合本校教学管理规定，风险自负。

## 功能

- **会话复用**：通过 Chrome DevTools 协议从你的浏览器实时读取登录会话，
  无需手动维护 cookie
- **课程检索**：单次请求获取当前学期的全部可选课程，按关键词匹配目标
- **已选查重**：提交前自动过滤已选课程（只做加法，不做减法）
- **抢课循环**：实时获取操作参数 → 自动选班 → 提交 → 按返回状态分类处理，
  支持轮询间隔、超时控制、预演模式
- **图形界面**：内置 GUI，双击启动，无需命令行

## 环境要求

- Windows / Chrome（需以远程调试模式启动，见下方命令）
- Python 3.10+，`pip install -r requirements.txt`

Chrome 远程调试（已运行的 Chrome 需先完全退出）：

```powershell
chrome.exe --remote-debugging-port=9222 `
  --user-data-dir="C:\Users\<你的用户名>\AppData\Local\Google\Chrome\User Data"
```

启动后登录教务系统，打开选课页面。

## 使用

```bash
# 图形界面（推荐）
python gui.pyw

# 命令行
python grab.py "关键词" --dry-run     # 预演：只匹配查重，不提交
python grab.py "关键词"               # 正式执行
```

常用参数：

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
gui.pyw             # 图形界面
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