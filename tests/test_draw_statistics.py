import ast
import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from src import user_manager
from src.config import Config
from src.draw_statistics import format_draw_statistics, statistics_day
from src.user_manager import UserManager


@pytest.mark.parametrize(("timestamp", "expected"), [
    ("2026-10-22T00:00:00+08:00", "2026-10-21"),
    ("2026-10-22T04:59:59.999999+08:00", "2026-10-21"),
    ("2026-10-22T05:00:00+08:00", "2026-10-22"),
    ("2026-10-22T23:59:59+08:00", "2026-10-22"),
    ("2026-10-21T20:59:59+00:00", "2026-10-21"),
    ("2026-10-21T21:00:00+00:00", "2026-10-22"),
    ("2026-10-21T14:00:00-07:00", "2026-10-22"),
    ("2027-01-01T04:59:59+08:00", "2026-12-31"),
    ("2026-11-01T04:59:59+08:00", "2026-10-31"),
    ("2028-03-01T04:59:59+08:00", "2028-02-29"),
])
def test_beijing_statistics_day(timestamp: str, expected: str):
    assert statistics_day(datetime.fromisoformat(timestamp)).isoformat() == expected


def test_naive_statistics_time_is_rejected():
    with pytest.raises(ValueError, match="时区"):
        statistics_day(datetime(2026, 10, 22, 5))  # noqa: DTZ001 - Reject naive input.


@pytest.fixture
def fixed_day(monkeypatch: pytest.MonkeyPatch):
    day = [date(2026, 10, 21)]
    monkeypatch.setattr(user_manager, "statistics_day", lambda: day[0])
    return day


def write_store(directory: Path, users: dict, *, migrated: bool = True) -> bytes:
    store = {
        "users": users, "whitelist": ["alice"], "blacklist": ["blocked"],
    }
    if migrated:
        store["draw_day_start_hour"] = 5
    data = json.dumps(store, indent=2).encode()
    (directory / "user_data.json").write_bytes(data)
    return data


def legacy_store(directory: Path) -> bytes:
    original = write_store(directory, {
        "alice": {
            "quota": 7, "last_checkin_date": "2026-10-22", "draw_total": 3,
            "draw_daily": {"2026-10-20": 1, "2026-10-21": 1, "2026-10-22": 1},
            "display_name": "Alice",
        },
        "bob": {
            "quota": 4, "draw_total": 1, "draw_daily": {"2026-10-21": 1},
        },
    }, migrated=False)
    entries = [
        {"user_id": "alice", "at": "2026-10-20T23:00:00+08:00"},
        {"user_id": "alice", "at": "2026-10-21T01:00:00+08:00"},
        {"user_id": "bob", "at": "2026-10-21T07:00:00+08:00"},
        {"user_id": "alice", "at": "2026-10-21T20:00:00+00:00"},
    ]
    for entry in entries:
        entry.update(outcome="success", batch_count=3)
    entries.append({"outcome": "failure"})
    (directory / "anlas_audit.jsonl").write_text(
        "\n".join(json.dumps(entry) for entry in entries) + "\n", encoding="utf-8",
    )
    return original


def test_legacy_migration_preserves_totals_quotas_and_original_backup(
    tmp_path: Path, fixed_day: list[date],
):
    original = legacy_store(tmp_path)
    audit = (tmp_path / "anlas_audit.jsonl").read_bytes()
    manager = UserManager(tmp_path)
    assert manager.get_total_draw_count() == 4
    assert manager.get_quota("alice") == 7
    assert manager.get_whitelist() == ["alice"]
    assert manager.get_blacklist() == ["blocked"]
    migrated = json.loads(manager.data_file.read_text("utf-8"))
    assert migrated["draw_day_start_hour"] == 5
    assert migrated["users"]["alice"]["last_checkin_date"] == "2026-10-22"
    assert migrated["users"]["alice"]["draw_daily"] == {
        "2026-10-20": 2, "2026-10-21": 1,
    }
    assert migrated["users"]["bob"]["draw_daily"] == {"2026-10-21": 1}
    assert (tmp_path / "user_data.before-5am-stats.json").read_bytes() == original
    assert (tmp_path / "anlas_audit.jsonl").read_bytes() == audit
    assert manager.get_draw_statistics().total == 2
    assert manager.get_draw_statistics(days=7).total == 4
    assert fixed_day[0] == date(2026, 10, 21)


def test_migration_is_idempotent_and_no_longer_depends_on_audit(tmp_path: Path):
    original = legacy_store(tmp_path)
    assert UserManager(tmp_path).get_total_draw_count() == 4
    migrated = (tmp_path / "user_data.json").read_bytes()
    (tmp_path / "anlas_audit.jsonl").unlink()
    assert UserManager(tmp_path).get_total_draw_count() == 4
    assert (tmp_path / "user_data.json").read_bytes() == migrated
    assert (tmp_path / "user_data.before-5am-stats.json").read_bytes() == original


@pytest.mark.parametrize("invalid_audit", [
    None,
    "",
    "{invalid json\n",
    '{"outcome":"success","user_id":"alice","at":"2026-10-20T23:00:00+08:00"}\n',
    '{"outcome":"success","user_id":"alice","at":"2026-10-20T23:00:00"}\n',
])
def test_incomplete_migration_never_modifies_existing_data(
    tmp_path: Path, invalid_audit: str | None,
):
    original = legacy_store(tmp_path)
    path = tmp_path / "anlas_audit.jsonl"
    if invalid_audit is None:
        path.unlink()
    else:
        path.write_text(invalid_audit, encoding="utf-8")
    manager = UserManager(tmp_path)
    with pytest.raises(ValueError, match="迁移失败"):
        manager.get_total_draw_count()
    assert manager.data_file.read_bytes() == original
    assert not (tmp_path / "user_data.before-5am-stats.json").exists()
    assert not (tmp_path / "user_data.json.tmp").exists()
    with pytest.raises(ValueError, match="迁移失败"):
        manager.get_total_draw_count()


def test_quota_only_legacy_store_does_not_require_audit(tmp_path: Path):
    write_store(tmp_path, {"alice": {"quota": 7}}, migrated=False)
    manager = UserManager(tmp_path)
    assert manager.get_quota("alice") == 7
    assert manager.get_total_draw_count() == 0
    assert json.loads(manager.data_file.read_text("utf-8"))["draw_day_start_hour"] == 5


def test_invalid_user_file_is_not_replaced_with_an_empty_store(tmp_path: Path):
    original = b"{invalid user file"
    (tmp_path / "user_data.json").write_bytes(original)
    with pytest.raises(ValueError, match="原文件未改动"):
        UserManager(tmp_path).get_total_draw_count()
    assert (tmp_path / "user_data.json").read_bytes() == original


def test_records_cross_statistics_days_and_survive_reload(
    tmp_path: Path, fixed_day: list[date],
):
    manager = UserManager(tmp_path)
    manager.record_successful_draw("alice", 2, "Alice")
    manager.record_successful_draw("alice", 0)
    manager.record_successful_draw("alice", -1)
    assert manager.get_today_draw_ranking() == [("alice", "Alice", 2)]
    fixed_day[0] = date(2026, 10, 22)
    manager.record_successful_draw("alice", 1)
    manager.reload()
    assert manager.get_today_draw_ranking() == [("alice", "Alice", 1)]
    assert manager.get_draw_statistics(days=7).total == 3
    assert manager.get_total_draw_count() == 3


def test_seven_days_include_current_day_and_six_prior_days_only(
    tmp_path: Path, fixed_day: list[date],
):
    write_store(tmp_path, {
        "alice": {
            "draw_total": 1000,
            "draw_daily": {
                "2026-10-14": 100, "2026-10-15": 1,
                "2026-10-20": 2, "2026-10-21": 3, "2026-10-22": 200,
            },
        },
        "bob": {"draw_daily": {"2026-10-21": 6}, "draw_total": 6},
    })
    manager = UserManager(tmp_path)
    statistics = manager.get_draw_statistics(days=7)
    assert statistics.start.isoformat() == "2026-10-15T05:00:00+08:00"
    assert statistics.end.isoformat() == "2026-10-22T05:00:00+08:00"
    assert statistics.daily_counts == [
        (date(2026, 10, 15), 1),
        (date(2026, 10, 16), 0),
        (date(2026, 10, 17), 0),
        (date(2026, 10, 18), 0),
        (date(2026, 10, 19), 0),
        (date(2026, 10, 20), 2),
        (fixed_day[0], 9),
    ]
    assert statistics.total == 12
    assert statistics.ranking == [("alice", "", 6), ("bob", "", 6)]
    assert manager.get_today_draw_ranking(limit=1) == [("bob", "", 6)]
    assert manager.get_total_draw_count() == 1006


def test_report_total_includes_users_outside_top_ten(
    tmp_path: Path, fixed_day: list[date],
):
    write_store(tmp_path, {
        f"user{index:04}": {
            "draw_daily": {fixed_day[0].isoformat(): 1}, "draw_total": 1,
        }
        for index in range(12)
    })
    statistics = UserManager(tmp_path).get_draw_statistics(days=7)
    report = format_draw_statistics(statistics)
    assert statistics.total == 12
    assert "七日成功生成：12 张" in report
    assert len([line for line in report.splitlines() if ". 用户 " in line]) == 10
    assert "用户 0000" in report
    assert "user0000" not in report


def test_empty_statistics_show_zero_days(tmp_path: Path, fixed_day: list[date]):
    manager = UserManager(tmp_path)
    statistics = manager.get_draw_statistics(days=7)
    assert statistics.total == 0
    assert len(statistics.daily_counts) == 7
    assert "本周期暂无成功生成的图片" in format_draw_statistics(statistics)
    assert statistics.daily_counts[-1][0] == fixed_day[0]
    with pytest.raises(ValueError, match="统计天数"):
        manager.get_draw_statistics(days=0)


def test_concurrent_records_do_not_lose_counts(tmp_path: Path, fixed_day: list[date]):
    manager = UserManager(tmp_path)
    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(lambda _: manager.record_successful_draw("alice"), range(50)))
    assert UserManager(tmp_path).get_total_draw_count() == 50
    assert manager.get_draw_statistics().daily_counts == [(fixed_day[0], 50)]


def test_checkin_keeps_calendar_midnight_boundary(
    tmp_path: Path, fixed_day: list[date], monkeypatch: pytest.MonkeyPatch,
):
    class CalendarDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 10, 22)

    monkeypatch.setattr(user_manager, "date", CalendarDate)
    write_store(tmp_path, {
        "alice": {"quota": 0, "last_checkin_date": "2026-10-21"},
    })
    config = Config()
    config.quota.checkin_min_quota = 2
    config.quota.checkin_max_quota = 2
    manager = UserManager(tmp_path)
    assert fixed_day[0] == date(2026, 10, 21)
    assert manager.checkin("alice", config)[:2] == (True, 2)
    assert manager.checkin("alice", config)[0] is False


@pytest.mark.parametrize(("method", "expected"), [
    ("cmd_nai_today_ranking", "今日成功生成：2 张"),
    ("cmd_nai_seven_day_statistics", "七日成功生成：3 张"),
])
def test_statistics_commands_use_the_real_manager(
    tmp_path: Path, fixed_day: list[date], method: str, expected: str,
):
    write_store(tmp_path, {
        "alice": {
            "draw_total": 3,
            "draw_daily": {"2026-10-20": 1, fixed_day[0].isoformat(): 2},
        },
    })
    path = Path(__file__).resolve().parents[1] / "main.py"
    tree = ast.parse(path.read_text("utf-8"))
    handler = next(
        node for cls in tree.body if isinstance(cls, ast.ClassDef)
        for node in cls.body if isinstance(node, ast.AsyncFunctionDef) and node.name == method
    )
    handler.decorator_list = []
    scope = {"AstrMessageEvent": object, "format_draw_statistics": format_draw_statistics}
    exec(compile(ast.Module(body=[handler], type_ignores=[]), str(path), "exec"), scope)  # noqa: S102 - Trusted local handler.
    plugin = SimpleNamespace(user_manager=UserManager(tmp_path))
    event = SimpleNamespace(plain_result=lambda text: text)

    async def run():
        return [item async for item in scope[method](plugin, event)]

    outputs = asyncio.run(run())
    assert len(outputs) == 1
    assert expected in outputs[0]
    assert "05:00" in outputs[0]
