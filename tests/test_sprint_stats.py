"""Batch 24 A2: the writing sprints the Writer records are read back: functions, the Builder's stats box, Settings > Stats and the CLI."""
import asyncio
import datetime
import json

import pytest
from textual.widgets import DataTable, TabbedContent

from storywheel import builder, fill, settings_app, vault, writing_stats
from storywheel.cli import main as cli

TODAY = datetime.date(2026, 10, 14)                                         # a Wednesday; its week starts Monday 2026-10-12


def at(days_ago, hour=9):
    return (datetime.datetime.combine(datetime.date.today(), datetime.time(hour)) - datetime.timedelta(days=days_ago)).isoformat(timespec="seconds")


def sprint(days_ago, words, minutes=25, actual=None, target=None, reason=None):
    actual = minutes if actual is None else actual
    rec = {"start": at(days_ago), "end": at(days_ago), "minutes": minutes, "actual_minutes": actual, "words": words,
           "wpm": round(words / actual, 1) if actual else 0}
    if target:
        rec["target"], rec["hit"] = target, words >= target
    if reason == "stopped" or reason == "left":
        rec["early"], rec["reason"] = True, reason
    elif reason == "done":
        rec["reason"] = "done"
    return rec


def put(story, *recs):
    story.stats_path.write_text(json.dumps({"days": {}, "sessions": [], "sprints": list(recs)}))


@pytest.fixture
def world(home):
    a = vault.create_universe("Thornwood", ["western"])
    s1 = a.new_story("The Last Clause")
    s1.append_scene("One", "Some words here.")
    s2 = a.new_story("Dry Years")
    b = vault.create_universe("Elsewhere")
    s3 = b.new_story("Far Tale")
    put(s1, sprint(0, 500, 25, target=400), sprint(1, 100, 25, actual=10, reason="stopped"))
    put(s2, sprint(2, 250, 10, reason="left", actual=5))
    put(s3, sprint(30, 1000, 50))
    return a, s1, s2, b, s3


# --- the reading functions -----------------------------------------------------------------------------------------------------

def test_a_story_universe_and_the_library_each_give_their_sprints_newest_first(world):
    a, s1, s2, b, s3 = world
    rows = writing_stats.story_sprints(s1)
    assert [r["words"] for r in rows] == [500, 100]
    r = rows[0]
    assert (r["story"], r["title"], r["planned_minutes"], r["actual_minutes"], r["wpm"], r["target"], r["hit"], r["reason"]) == \
        ("thornwood/the-last-clause", "The Last Clause", 25, 25, 20.0, 400, True, "done")
    assert rows[1]["reason"] == "stopped" and rows[1]["early"] and rows[1]["wpm"] == 10.0 and rows[1]["target"] is None and rows[1]["hit"] is None
    assert [r["words"] for r in writing_stats.sprints(universe=a)] == [500, 100, 250]
    assert [r["words"] for r in writing_stats.sprints()] == [500, 100, 250, 1000]
    assert [r["words"] for r in writing_stats.sprints(story=s2)] == [250] and writing_stats.sprints(story=s2)[0]["reason"] == "left"
    assert [r["words"] for r in writing_stats.sprints(weeks=2)] == [500, 100, 250]                    # (the 30-day-old one is out)
    assert writing_stats.sprints(universe=b, weeks=1) == []


def test_a_missed_target_and_old_records_without_a_reason_read_sensibly(home):
    s = vault.create_universe("U").new_story("S")
    put(s, sprint(0, 50, 25, target=200), {"start": at(1), "minutes": 5, "words": 10, "wpm": 2, "early": True}, {"minutes": 5}, "junk")
    rows = writing_stats.story_sprints(s)
    assert len(rows) == 2                                                   # (no date, or not a record: left out)
    by_words = {r["words"]: r for r in rows}
    assert by_words[50]["hit"] is False and by_words[10]["reason"] == "stopped" and by_words[10]["actual_minutes"] == 5
    s.stats_path.write_text("{ nope")
    assert writing_stats.story_sprints(s) == []


def test_the_summary_totals_best_and_trend(world):
    rows = writing_stats.sprints()
    sm = writing_stats.sprint_summary(rows)
    assert sm["count"] == 4 and sm["words"] == 1850 and sm["best_wpm"] == 50.0
    assert sm["minutes"] == 25 + 10 + 5 + 50 and sm["avg_wpm"] == round(1850 / 90, 1)
    assert sm["targets_set"] == 1 and sm["targets_hit"] == 1 and sm["recent"][0]["words"] == 500
    assert len(sm["trend"]) == 8 and sm["trend"][-1]["sprints"] >= 1
    assert sum(t["sprints"] for t in sm["trend"]) == 4                      # (the 30-day-old one is still inside eight weeks)


def test_the_trend_is_per_monday_week_and_weeks_without_sprints_show_as_empty():
    rows = [{"date": "2026-10-13", "words": 300, "actual_minutes": 20.0}, {"date": "2026-10-12", "words": 100, "actual_minutes": 20.0},
            {"date": "2026-09-30", "words": 50, "actual_minutes": 10.0}]
    trend = writing_stats.sprint_trend(rows, weeks=3, today=TODAY)
    assert trend == [(datetime.date(2026, 9, 28), 1, 5.0), (datetime.date(2026, 10, 5), 0, 0.0), (datetime.date(2026, 10, 12), 2, 10.0)]
    lines = writing_stats.trend_lines(trend)
    assert lines[0].startswith("2026-09-28  ") and "5.0 wpm  (1 sprint)" in lines[0]
    assert "no sprints" in lines[1] and "·" * 20 in lines[1]
    assert "10.0 wpm  (2 sprints)" in lines[2] and "█" * 20 in lines[2] and "█" * 20 not in lines[0]


def test_sprints_this_week_counts_the_last_seven_days(world):
    sm = writing_stats.sprint_summary(writing_stats.sprints())
    assert sm["week"] == 3                                                  # (today, yesterday, two days ago)


def test_reset_story_forgets_sprints_too(world):
    a, s1, *_ = world
    writing_stats.reset_story(s1)
    assert writing_stats.story_sprints(s1) == [] and json.loads(s1.stats_path.read_text())["sprints"] == []


def test_a_sprint_line_says_what_happened(world):
    rows = {r["words"]: r for r in writing_stats.sprints()}
    assert "500 words" in writing_stats.sprint_line(rows[500]) and "target 400: met" in writing_stats.sprint_line(rows[500])
    assert "(stopped early)" in writing_stats.sprint_line(rows[100]) and "(Writer closed)" in writing_stats.sprint_line(rows[250])


# --- the views --------------------------------------------------------------------------------------------------------------------

def test_the_builder_stats_box_shows_the_sprint_line_for_the_open_story(world):
    async def go():
        app = builder.BuilderApp(engine_factory=lambda x: fill.make_engine(x, seed=1), universe="thornwood", story="the-last-clause")
        async with app.run_test(size=(200, 50)) as pilot:
            await pilot.pause()
            return str(app.screen.query_one("#stats").content)
    text = asyncio.run(go())
    assert "Sprints  2 this week · 600 words in 2 · 17.1 wpm average, best 20" in text and "500 words" in text


def test_the_builder_stats_box_has_no_sprint_line_without_sprints(home):
    u = vault.create_universe("Thornwood")
    u.new_story("S")
    async def go():
        app = builder.BuilderApp(engine_factory=lambda x: fill.make_engine(x, seed=1), universe="thornwood", story="s")
        async with app.run_test(size=(200, 50)) as pilot:
            await pilot.pause()
            return str(app.screen.query_one("#stats").content)
    assert "Sprints" not in asyncio.run(go())


def test_settings_stats_tab_lists_sprints_with_a_trend(world):
    async def go():
        app = settings_app.SettingsApp(None, "builder")
        async with app.run_test(size=(200, 50)) as pilot:
            await pilot.pause()
            app.screen.query_one("#tabs", TabbedContent).active = "t-stats"
            await pilot.pause()
            table = app.screen.query_one("#sprints", DataTable)
            return str(app.screen.query_one("#sprint-summary").content), [table.get_row_at(i) for i in range(table.row_count)]
    text, rows = asyncio.run(go())
    assert "4 in all · 1,850 words" in text and "word targets met 1 of 1" in text and "Average words a minute, week by week" in text
    assert text.count("sprint") >= 8 and "█" in text
    assert rows[0][1] == "thornwood/the-last-clause" and rows[0][4] == "500" and rows[0][6] == "met (400)" and rows[0][7] == "finished"
    assert rows[1][7] == "stopped early" and rows[2][7] == "Writer closed"


def test_settings_stats_tab_with_no_sprints_says_how_to_start_one(home):
    async def go():
        app = settings_app.SettingsApp(None, "builder")
        async with app.run_test(size=(200, 50)) as pilot:
            await pilot.pause()
            app.screen.query_one("#tabs", TabbedContent).active = "t-stats"
            await pilot.pause()
            return str(app.screen.query_one("#sprint-summary").content), app.screen.query_one("#sprints", DataTable).row_count
    text, n = asyncio.run(go())
    assert "No sprints yet" in text and "F12" in text and n == 0


# --- the CLI ------------------------------------------------------------------------------------------------------------------------

def test_stats_sprints_json_and_text(world, capsys):
    cli(["stats", "sprints", "--json"])
    data = json.loads(capsys.readouterr().out)
    assert data["scope"] == "the whole library" and data["weeks"] == 8 and data["count"] == 4 and data["words"] == 1850
    assert [r["words"] for r in data["recent"]] == [500, 100, 250, 1000] and len(data["trend"]) == 8
    cli(["stats", "sprints", "--universe", "thornwood", "--weeks", "1", "--json"])
    data = json.loads(capsys.readouterr().out)
    assert data["scope"] == "universe thornwood" and data["count"] == 3 and len(data["trend"]) == 1
    cli(["stats", "sprints", "--story", "thornwood/dry-years", "--weeks", "52", "--json"])
    assert json.loads(capsys.readouterr().out)["count"] == 1
    cli(["stats", "sprints", "--weeks", "52"])
    out = capsys.readouterr().out
    assert "4 (3 this week), 1,850 words" in out and "(stopped early)" in out and "Average words a minute by week" in out
    assert "target 400: met" in out


def test_stats_sprints_with_none_says_so(home, capsys):
    vault.create_universe("U")
    cli(["stats", "sprints"])
    assert "No sprints in the whole library" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        cli(["stats", "sprints", "--universe", "nope"])
