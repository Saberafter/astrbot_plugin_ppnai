"""Beijing 05:00 drawing days, historical rebucketing, and statistics output."""

import json
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

BEIJING = timezone(timedelta(hours=8))
DAY_START_HOUR = 5


def statistics_day(now: datetime | None = None) -> date:
    current = now if now is not None else datetime.now(BEIJING)
    if current.utcoffset() is None:
        raise ValueError("统计时间必须包含时区")
    return (
        current.astimezone(BEIJING) - timedelta(hours=DAY_START_HOUR)
    ).date()


@dataclass(frozen=True)
class DrawStatistics:
    start: datetime
    end: datetime
    daily_counts: list[tuple[date, int]]
    ranking: list[tuple[str, str, int]]

    @property
    def total(self) -> int:
        return sum(count for _, count in self.daily_counts)


def rebuild_draw_days(
    legacy: dict[str, dict[str, int]], audit_file: Path,
) -> dict[str, dict[str, int]]:
    expected = Counter({
        (user_id, day): count
        for user_id, days in legacy.items()
        for day, count in days.items()
        if count
    })
    rebuilt: dict[str, Counter[str]] = {user_id: Counter() for user_id in legacy}
    if not expected:
        return {user_id: {} for user_id in legacy}
    observed: Counter[tuple[str, str]] = Counter()
    try:
        with audit_file.open(encoding="utf-8-sig") as stream:
            for line in stream:
                if not line.strip():
                    continue
                entry = json.loads(line)
                if entry.get("outcome") != "success":
                    continue
                at = datetime.fromisoformat(entry["at"])
                draw_day = statistics_day(at).isoformat()
                user_id = str(entry["user_id"])
                calendar_day = at.astimezone(BEIJING).date().isoformat()
                observed[user_id, calendar_day] += 1
                rebuilt.setdefault(user_id, Counter())[draw_day] += 1
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        raise ValueError("历史绘图统计迁移失败：无法完整读取逐条成功记录，原数据未改动") from exc
    if observed != expected:
        raise ValueError("历史绘图统计迁移失败：逐条成功记录与原统计不一致，原数据未改动")
    return {user_id: dict(sorted(days.items())) for user_id, days in rebuilt.items()}


def format_draw_statistics(statistics: DrawStatistics) -> str:
    seven_days = len(statistics.daily_counts) == 7
    lines = [
        "七日绘图统计" if seven_days else "今日绘图排行榜",
        "北京时间，每天 05:00 分界",
        f"周期：{statistics.start:%m-%d %H:%M} 至 "
        f"{statistics.end:%m-%d %H:%M}（截至当前）",
        f"{'七日' if seven_days else '今日'}成功生成：{statistics.total} 张",
    ]
    if seven_days:
        lines.append("\n每日张数（日期指当日 05:00 起）：")
        lines.extend(
            f"{day:%m-%d}：{count} 张" for day, count in statistics.daily_counts
        )
        lines.append("\n七日排行榜（前十名）：")
    elif statistics.ranking:
        lines.append("\n今日排行榜（前十名）：")
    if not statistics.ranking:
        lines.append("本周期暂无成功生成的图片。")
    for index, (user_id, name, count) in enumerate(statistics.ranking[:10], 1):
        display = name or f"用户 {user_id[-4:]}"
        lines.append(f"{index}. {display}：{count} 张")
    return "\n".join(lines)
