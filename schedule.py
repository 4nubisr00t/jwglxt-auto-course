# -*- coding: utf-8 -*-
"""
排课时间引擎
=============
解析正方教务 sksj 字符串 → 结构化时间槽，提供冲突判定与展示格式化。

sksj 真实格式（湘大正方实测）：
  '星期六第3-4节{2周}'
  '星期六第5-6节{2-4周,6-10周}'
  '星期一第9-10节{2-5周,10-17周}'
  '星期三第1-2节{2-5周,7-17周}<br/>星期四第1-2节{2-4周,6-17周}<br/>星期五第3-4节{2-3周}'
  '--'                    # 无固定排课（网课/集中实践等），视为不冲突
"""
import re
from dataclasses import dataclass, field

DAY_CN = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "日": 7}
DAY_STR = {1: "周一", 2: "周二", 3: "周三", 4: "周四", 5: "周五", 6: "周六", 7: "周日"}

_SLOT_RE = re.compile(r"([一二三四五六日])第(\d+)-(\d+)节\{([^}]*)\}")


@dataclass(frozen=True)
class TimeSlot:
    """一个时间槽：星期几 + 节次闭区间 + 周次集合。"""
    day: int                       # 1=周一 .. 7=周日
    start: int                     # 起始节次
    end: int                       # 结束节次（闭区间）
    weeks: frozenset = frozenset()  # 生效周次集合（空=不排课/未知）

    def overlaps(self, other: "TimeSlot") -> bool:
        """两个时间槽是否冲突：同日 + 节次区间重叠 + 周次有交集。"""
        if self.day != other.day:
            return False
        if max(self.start, other.start) > min(self.end, other.end):
            return False
        if not self.weeks or not other.weeks:
            return False          # 任一侧周次未知/空，不判冲突
        return bool(self.weeks & other.weeks)

    def __repr__(self):
        return (f"<TimeSlot {DAY_STR[self.day]} {self.start}-{self.end}节 "
                f"周{format_weeks(self.weeks)}>")


def _expand_weeks(seg: str) -> set:
    """'2周' -> {2}；'2-4周,6-10周' -> {2,3,4,6..10}。"""
    out = set()
    for part in seg.split(","):
        part = part.strip()
        if not part:
            continue
        m = re.match(r"(\d+)(?:-(\d+))?", part)
        if not m:
            continue
        a = int(m.group(1))
        b = int(m.group(2)) if m.group(2) else a
        out.update(range(a, b + 1))
    return out


def format_weeks(weeks) -> str:
    """周次集合压缩成区间串：'{2,3,4,6,7,8,9,10}' -> '2-4,6-10周'。"""
    ws = sorted(weeks)
    if not ws:
        return "--"
    segs = []
    lo = hi = ws[0]
    for w in ws[1:]:
        if w == hi + 1:
            hi = w
        else:
            segs.append(f"{lo}-{hi}" if lo != hi else f"{lo}")
            lo = hi = w
    segs.append(f"{lo}-{hi}" if lo != hi else f"{lo}")
    return ",".join(segs) + "周"


def parse_sksj(sksj: str) -> list:
    """解析 sksj 字符串为 TimeSlot 列表。'--' / 空 → []。"""
    if not sksj or sksj.strip() in ("--", ""):
        return []
    slots = []
    for seg in re.split(r"<br\s*/?>", sksj):
        m = _SLOT_RE.search(seg)
        if not m:
            continue
        day = DAY_CN.get(m.group(1))
        if day is None:
            continue
        start = int(m.group(2))
        end = int(m.group(3))
        weeks = frozenset(_expand_weeks(m.group(4)))
        slots.append(TimeSlot(day, start, end, weeks))
    return slots


def slots_str(slots: list) -> str:
    """时间槽 → 展示串：'周三 1-2节(2-5,7-17周); 周五 3-4节(2-3周)'。"""
    if not slots:
        return "时间待定"
    parts = []
    for s in sorted(slots, key=lambda x: (x.day, x.start)):
        wk = f"({format_weeks(s.weeks)})" if s.weeks else ""
        parts.append(f"{DAY_STR[s.day]} {s.start}-{s.end}节" + wk)
    return "; ".join(parts)


def any_conflict(a_slots: list, b_slots: list) -> bool:
    """两组时间槽是否存在任意冲突。"""
    if not a_slots or not b_slots:
        return False
    return any(x.overlaps(y) for x in a_slots for y in b_slots)


def conflict_detail(a_slots: list, b_slots: list) -> list:
    """返回冲突对明细 [(a_slot, b_slot), ...]。"""
    if not a_slots or not b_slots:
        return []
    return [(x, y) for x in a_slots for y in b_slots if x.overlaps(y)]


# ---------------------------------------------------------------- 课程视图

def jxb_occupied(jxb: dict) -> list:
    """教学班已占座位：容量 jxbrl 与已选 yxzrs（大分页行里 yxzrs 可能已是余量语义？）
    返回 (容量, 已选) 归一化：n 取 jxbrl 优先，余量 = 容量 - 已选。"""
    rl = int(jxb.get("jxbrl") or 0)          # 容量
    yx = int(jxb.get("yxzrs") or 0)          # 已选人数
    if rl <= 0:                              # 网课类软上限：用 max_yx 兜底
        return None
    return rl, yx


def surplus_of(jxb: dict, max_yx: int = 0) -> int:
    """余量（保守估计）：容量 - 已选；软上限班（rl=0）用全表最大已选做参照。"""
    rl = int(jxb.get("jxbrl") or 0)
    yx = int(jxb.get("yxzrs") or 0)
    if rl <= 0:
        return max(0, max_yx - yx)
    return max(0, rl - yx)