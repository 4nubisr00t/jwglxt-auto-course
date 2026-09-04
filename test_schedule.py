# -*- coding: utf-8 -*-
"""schedule.py 单元测试（基于湘大实测 sksj 格式）"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from schedule import (parse_sksj, slots_str, any_conflict, conflict_detail,
                      format_weeks, TimeSlot)

fails = 0
def check(name, cond):
    global fails
    tag = "PASS" if cond else "FAIL"
    if not cond:
        fails += 1
    print(f"[{tag}] {name}")

# ---- 解析：单时段 ----
s = parse_sksj('星期六第3-4节{2周}')
check("单时段 1 个槽", len(s) == 1)
check("周六=6", s[0].day == 6)
check("3-4节", (s[0].start, s[0].end) == (3, 4))
check("周{2}", s[0].weeks == frozenset({2}))

# ---- 解析：多周区间 ----
s = parse_sksj('星期六第5-6节{2-4周,6-10周}')
check("多区间周次", s[0].weeks == frozenset({2, 3, 4, 6, 7, 8, 9, 10}))

# ---- 解析：多时段 <br/> ----
raw = ('星期三第1-2节{2-5周,7-17周}<br/>星期四第1-2节{2-4周,6-17周}'
       '<br/>星期五第3-4节{2-3周}')
s = parse_sksj(raw)
check("多时段 3 个槽", len(s) == 3)
check("槽1 周三1-2", (s[0].day, s[0].start, s[0].end) == (3, 1, 2))
check("槽1 周次", s[0].weeks == frozenset({2, 3, 4, 5, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17}))
check("槽3 周五3-4", (s[2].day, s[2].start, s[2].end) == (5, 3, 4))

# ---- 解析：无排课 ----
check("'--' 空槽", parse_sksj('--') == [])
check("空串 空槽", parse_sksj('') == [])

# ---- 冲突判定 ----
a = parse_sksj('星期五第3-4节{2-3周}')
b = parse_sksj('星期五第3-4节{2-5周}')
check("同天同节 冲突", any_conflict(a, b))
c = parse_sksj('星期四第1-2节{2-4周,6-17周}')
check("不同天 不冲突", not any_conflict(a, c))
d = parse_sksj('星期五第3-4节{5周}')
check("同天同节不同周 不冲突", not any_conflict(a, d))
e = parse_sksj('星期五第5-6节{2-3周}')
check("同天节次不重叠 不冲突", not any_conflict(a, e))
f = parse_sksj('星期五第5-6节{2-3周}')
check("跨节次重叠 1-4 vs 4-6", any_conflict(
    [TimeSlot(5, 1, 4, frozenset({2}))], [TimeSlot(5, 4, 6, frozenset({2}))]))
# 无固定排课不参与冲突
check("无排课 '--' 不冲突", not any_conflict(a, parse_sksj('--')))

# ---- 冲突明细 ----
det = conflict_detail(a, b)
check("冲突明细长度", len(det) == 1 and det[0][0].day == 5)

# ---- 展示格式化 ----
check("slots_str", slots_str(parse_sksj('星期三第1-2节{2-5周,7-17周}'))
      == "周三 1-2节(2-5,7-17周)")
check("format_weeks 压缩", format_weeks({2, 3, 4, 6, 7, 8, 9, 10}) == "2-4,6-10周")
check("format_weeks 单周", format_weeks({2}) == "2周")

print()
print("断言失败数:", fails)
sys.exit(1 if fails else 0)