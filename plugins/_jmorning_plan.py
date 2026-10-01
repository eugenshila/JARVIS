"""
ADHD-friendly day planner.

The design rules here are not decoration — they are the whole point, so they're
written down:

* **Short blocks, always the same length.** A fixed 25-minute block removes the
  "how long should this take?" decision, which is where a lot of ADHD task
  initiation stalls. Every block is identical in shape, so starting one is a
  habit rather than a choice.
* **A break after every block, a long one every four.** Breaks are scheduled,
  not earned. Unscheduled breaks become hyperfocus overruns or guilt; a timed
  5-minute break is a boundary in both directions.
* **One thing per block.** Each block names exactly one action with a concrete
  finish line ("module 2 of 7"), never a vague area of work.
* **Hardest work lands in the first blocks.** Executive function is at its best
  early, so the course study and the job review go up front and the admin-ish
  review tasks go after lunch.
* **Nothing runs past the configured end time.** The plan is truncated, not
  compressed — an honest short plan beats an aspirational one that gets
  abandoned by 11am.
* **Every block is reviewable, never automatic.** Blocks say "review and
  prepare", because JARVIS does not submit, send, or trade.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

DEFAULT_BLOCK = 25          # minutes of focused work
DEFAULT_BREAK = 5           # minutes between blocks
DEFAULT_LONG_BREAK = 20     # minutes after a set
BLOCKS_PER_SET = 4


@dataclass
class Block:
    start: datetime
    end: datetime
    kind: str               # work | break | long_break | buffer
    title: str
    detail: str = ""

    @property
    def minutes(self) -> int:
        return int((self.end - self.start).total_seconds() // 60)

    def line(self) -> str:
        icon = {"work": "▶", "break": "·", "long_break": "◍", "buffer": "□"}.get(self.kind, "·")
        base = f"{self.start:%H:%M}–{self.end:%H:%M} {icon} {self.title}"
        return base + (f" — {self.detail}" if self.detail else "")


@dataclass
class Plan:
    blocks: list[Block] = field(default_factory=list)
    unplanned: list[str] = field(default_factory=list)

    @property
    def work_blocks(self) -> list[Block]:
        return [b for b in self.blocks if b.kind == "work"]

    @property
    def focus_minutes(self) -> int:
        return sum(b.minutes for b in self.work_blocks)

    def text(self) -> str:
        out = [b.line() for b in self.blocks]
        if self.unplanned:
            out.append("")
            out.append("Did not fit today (carry forward):")
            out += [f"  – {t}" for t in self.unplanned]
        return "\n".join(out)


def _parse_time(value: str, fallback: datetime) -> datetime:
    try:
        h, m = str(value).split(":")
        return fallback.replace(hour=int(h), minute=int(m), second=0, microsecond=0)
    except Exception:
        return fallback


def build_plan(tasks: list[tuple[str, str]], *, start: datetime | None = None,
               end_time: str = "17:00", block_minutes: int = DEFAULT_BLOCK,
               break_minutes: int = DEFAULT_BREAK,
               long_break_minutes: int = DEFAULT_LONG_BREAK,
               lunch_at: str = "13:00", lunch_minutes: int = 45) -> Plan:
    """
    `tasks` is an ordered list of (title, detail) — already prioritised by the
    caller, hardest first. One task per work block; a task needing more than one
    block should be passed in several times with different details, which is
    exactly how the course modules are split.
    """
    now = start or datetime.now()
    now = now.replace(second=0, microsecond=0)
    day_end = _parse_time(end_time, now.replace(hour=17, minute=0))
    lunch_start = _parse_time(lunch_at, now.replace(hour=13, minute=0))
    lunch_end = lunch_start + timedelta(minutes=lunch_minutes)

    plan = Plan()
    cursor = now
    done = 0
    queue = list(tasks)

    while queue and cursor + timedelta(minutes=block_minutes) <= day_end:
        # Step over lunch rather than scheduling through it.
        if cursor < lunch_end and cursor + timedelta(minutes=block_minutes) > lunch_start:
            plan.blocks.append(Block(lunch_start, lunch_end, "long_break",
                                     "Lunch — away from the screen"))
            cursor = lunch_end
            done = 0
            continue

        title, detail = queue.pop(0)
        block_end = cursor + timedelta(minutes=block_minutes)
        plan.blocks.append(Block(cursor, block_end, "work", title, detail))
        cursor = block_end
        done += 1

        if not queue:
            break
        if done % BLOCKS_PER_SET == 0:
            gap, kind, label = long_break_minutes, "long_break", "Long break — stand up, walk, water"
        else:
            gap, kind, label = break_minutes, "break", "Break — no screens"
        if cursor + timedelta(minutes=gap) > day_end:
            break
        # Don't open a break that would run into lunch — lunch IS the break,
        # and two overlapping rest blocks in the timeline is exactly the kind of
        # ambiguity this plan exists to remove.
        if cursor + timedelta(minutes=gap) > lunch_start and cursor < lunch_end:
            continue
        plan.blocks.append(Block(cursor, cursor + timedelta(minutes=gap), kind, label))
        cursor += timedelta(minutes=gap)

    plan.unplanned = [t for t, _ in queue]

    # A plan should never end on a break: if the day ran out mid-set, the
    # trailing rest blocks are noise.
    while plan.blocks and plan.blocks[-1].kind != "work":
        cursor = plan.blocks[-1].start
        plan.blocks.pop()

    # A closing buffer, if the day has room. Overrun is the norm, not the
    # exception, so it gets its own slot instead of eating the evening.
    if cursor + timedelta(minutes=15) <= day_end:
        plan.blocks.append(Block(cursor, cursor + timedelta(minutes=15), "buffer",
                                 "Catch-up buffer / shut down ritual"))
    return plan


def course_tasks(course, max_blocks: int, block_minutes: int) -> list[tuple[str, str]]:
    """
    Slice one course into block-sized study tasks with a visible finish line.

    Progress is expressed in modules when the course declares them, because
    "module 2 of 7" is a far better motivator than "25 more minutes".
    """
    if course is None:
        return []
    total = max(int(course.duration_minutes or 0), block_minutes)
    needed = max(1, -(-total // block_minutes))         # ceil
    blocks = min(needed, max(1, max_blocks))
    out = []
    for i in range(blocks):
        if course.modules:
            # Contiguous ranges that cover every module exactly once. Dividing
            # by position alone skips numbers (1, 2, 4, 6 of 7), which reads
            # like lost work — the whole course has to be accounted for.
            first = int(i * course.modules / blocks) + 1
            last = max(first, int((i + 1) * course.modules / blocks))
            detail = (f"module {first} of {course.modules}" if first == last
                      else f"modules {first}–{last} of {course.modules}")
        else:
            detail = f"part {i + 1} of {blocks}"
        out.append((f"Study: {course.title}", detail))
    return out
