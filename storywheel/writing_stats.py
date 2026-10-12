"""
Writing statistics, read from each story's stats.json (the Writer keeps them) and its manuscript.

    days()                 {date: words} across every story in the library
    streak(days, today)    (current streak, best streak) in days
    summary(universe, story)   everything the Builder's stats box and the Settings stats tab show
    sprints(...)           the writing sprints the Writer recorded (per story, per universe, or the whole library)
    sprint_summary(rows)   this week, totals, average and best words a minute, recent sprints and a weekly trend
"""
import datetime
import json

from . import settings, vault


def _date(text):
    return datetime.date.fromisoformat(text)


def story_days(story):
    """{date: words written that day} for one story (from its stats.json)."""
    try:
        data = json.loads(story.stats_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {d: day_words(v) for d, v in (data.get("days") or {}).items()}


def day_words(day):
    """One day's words: the sum over machines when stats.json has them (days[date].machines = {host: words}, so a sync tool merging the
    files from two computers can't count a day twice), else the older single `words` number."""
    machines = day.get("machines")
    if isinstance(machines, dict) and machines:
        return sum(int(v or 0) for v in machines.values())
    return int(day.get("words", 0) or 0)


def days(universes=None):
    """Words per day across all the stories (or the given universes')."""
    out = {}
    for u in (universes if universes is not None else vault.list_universes()):
        for s in u.stories():
            for d, w in story_days(s).items():
                out[d] = out.get(d, 0) + w
    return out


def streak(per_day, today=None):
    """(current, best): consecutive days with words. A day that has not got words yet (today) does not break
    the current streak, which then counts back from yesterday."""
    today = today or datetime.date.today()
    written = {_date(d) for d, w in per_day.items() if w > 0}
    cur = 0
    day = today if today in written else today - datetime.timedelta(days=1)
    while day in written:
        cur += 1
        day -= datetime.timedelta(days=1)
    best = run = 0
    prev = None
    for d in sorted(written):
        run = run + 1 if prev is not None and (d - prev).days == 1 else 1
        best = max(best, run)
        prev = d
    return cur, best


def bar(done, goal, width=20):
    if goal <= 0:
        return ""
    frac = min(1.0, done / goal)
    full = int(round(frac * width))
    return "█" * full + "░" * (width - full)


def summary(universe=None, story=None, today=None):
    """Numbers for the stats box: today vs the goal, streaks, totals for the story and the universe."""
    today = today or datetime.date.today()
    per_day = days()
    goal = int(settings.load_story(story.path)["daily_goal"]) if story else int(settings.load_global().get("daily_goal") or 0)
    words_today = per_day.get(today.isoformat(), 0)
    cur, best = streak(per_day, today)
    out = {"today": words_today, "goal": goal, "percent": (round(100 * words_today / goal) if goal else None),
           "streak": cur, "best_streak": best, "bar": bar(words_today, goal),
           "week": sum(w for d, w in per_day.items() if 0 <= (today - _date(d)).days < 7)}
    if story is not None:
        out["story_words"] = story.word_count()
        out["story_scenes"] = len(story.scene_list())
        out["story_title"] = story.title
    if universe is not None:
        out["universe_words"] = sum(s.word_count() for s in universe.stories())
        out["universe_stories"] = len(universe.stories())
        out["universe_name"] = universe.name
    return out


def set_day(date, words, universes=None):
    """Correct one day's total across all stories to `words`: the difference goes on an "(edited)" machine entry of the story that wrote
    most that day (the first story when none did), so nothing else in stats.json is touched. Returns the change."""
    stories = [s for u in (universes if universes is not None else vault.list_universes()) for s in u.stories()]
    if not stories:
        return 0
    have = {s: story_days(s).get(date, 0) for s in stories}
    delta = max(0, int(words)) - sum(have.values())
    if not delta:
        return 0
    target = max(stories, key=lambda s: have[s])
    try:
        data = json.loads(target.stats_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    data.setdefault("days", {})
    day = data["days"].setdefault(date, {})
    machines = day.get("machines")
    if not isinstance(machines, dict) or not machines:
        machines = {"(earlier)": int(day.get("words", 0) or 0)} if day.get("words") else {}
    machines["(edited)"] = int(machines.get("(edited)", 0)) + delta
    day["machines"] = machines
    day["words"] = day_words(day)
    data.setdefault("sessions", [])
    target.stats_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return delta


def reset_story(story):
    """Forget a story's recorded history (its days, sessions and sprints). The manuscript is not touched. Returns the words that were recorded."""
    before = sum(story_days(story).values())
    story.stats_path.write_text(json.dumps({"days": {}, "sessions": [], "sprints": []}, indent=2), encoding="utf-8")
    return before


def history(limit=60):
    """[(date, words)] newest first, for the stats tab."""
    per_day = days()
    return sorted(per_day.items(), reverse=True)[:limit]


def per_story():
    """[(universe name, story title, words, today's words)] for every story."""
    today = datetime.date.today().isoformat()
    rows = []
    for u in vault.list_universes():
        for s in u.stories():
            rows.append((u.name, s.title, s.word_count(), story_days(s).get(today, 0)))
    return rows


# --- writing sprints (the Writer adds one to stats.json's "sprints" when it ends, is stopped, or the Writer is closed) -------------------------

def _num(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def story_sprints(story):
    """The sprints recorded for one story, oldest first: each a dict with date, universe, story (id), title, planned_minutes, actual_minutes,
    words, wpm, target (or None), hit (True/False when a target was set, else None) and how it ended: reason "done", "stopped" or "left"."""
    try:
        data = json.loads(story.stats_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    out = []
    for rec in data.get("sprints") or []:
        if not isinstance(rec, dict):
            continue
        start = str(rec.get("start") or "")
        try:
            date = datetime.date.fromisoformat(start[:10]).isoformat()
        except ValueError:
            continue                                                    # (a record with no usable date can't be placed in a week)
        planned = _num(rec.get("minutes"))
        actual = _num(rec.get("actual_minutes"), planned)
        words = int(_num(rec.get("words")))
        target = int(_num(rec.get("target"))) or None
        reason = rec.get("reason") or ("stopped" if rec.get("early") else "done")
        out.append({"date": date, "start": start, "universe": story.universe.slug, "story": f"{story.universe.slug}/{story.slug}",
                    "title": story.title, "planned_minutes": planned, "actual_minutes": actual, "words": words,
                    "wpm": round(_num(rec.get("wpm"), words / actual if actual else 0.0), 1), "target": target,
                    "hit": bool(rec.get("hit")) if target else None, "reason": reason, "early": reason != "done"})
    return out


def sprints(universe=None, story=None, weeks=None, today=None):
    """Sprints newest first: one story's, one universe's, or the whole library's; `weeks` keeps only the last N weeks (7 days each)."""
    today = today or datetime.date.today()
    if story is not None:
        stories = [story]
    elif universe is not None:
        stories = universe.stories()
    else:
        stories = [s for u in vault.list_universes() for s in u.stories()]
    rows = [r for s in stories for r in story_sprints(s)]
    if weeks:
        rows = [r for r in rows if 0 <= (today - _date(r["date"])).days < 7 * int(weeks)]
    return sorted(rows, key=lambda r: r["start"], reverse=True)


def _week_start(date):
    return date - datetime.timedelta(days=date.weekday())


def sprint_trend(rows, weeks=8, today=None):
    """[(Monday of the week, sprints, average words a minute)] for the last `weeks` weeks, oldest first, weeks with no sprint included
    (average 0). The average is total words over total minutes, so a long sprint counts for more than a short one."""
    today = today or datetime.date.today()
    first = _week_start(today) - datetime.timedelta(weeks=int(weeks) - 1)
    buckets = {first + datetime.timedelta(weeks=i): [0, 0, 0.0] for i in range(int(weeks))}
    for r in rows:
        b = buckets.get(_week_start(_date(r["date"])))
        if b is not None:
            b[0] += 1
            b[1] += r["words"]
            b[2] += r["actual_minutes"]
    return [(wk, n, round(w / m, 1) if m else 0.0) for wk, (n, w, m) in sorted(buckets.items())]


def trend_lines(trend, width=20):
    """The trend as plain text, one line a week: "2026-10-05  ██████░░░░  12.4 wpm  (3 sprints)"."""
    top = max((avg for _, _, avg in trend), default=0)
    return [f"{wk.isoformat()}  {bar(avg, top, width) if n else '·' * width}  "
            + (f"{avg:.1f} wpm  ({n} sprint{'s' if n != 1 else ''})" if n else "no sprints") for wk, n, avg in trend]


def sprint_summary(rows, weeks=8, recent=8, today=None):
    """Figures for the stats views: sprints this week, total sprint words, average and best words a minute, the target score, the most recent
    sprints and the weekly trend."""
    today = today or datetime.date.today()
    minutes = sum(r["actual_minutes"] for r in rows)
    words = sum(r["words"] for r in rows)
    with_target = [r for r in rows if r["target"]]
    return {"count": len(rows), "week": sum(1 for r in rows if 0 <= (today - _date(r["date"])).days < 7),
            "words": words, "minutes": round(minutes, 1), "avg_wpm": round(words / minutes, 1) if minutes else 0.0,
            "best_wpm": max((r["wpm"] for r in rows), default=0.0), "targets_set": len(with_target),
            "targets_hit": sum(1 for r in with_target if r["hit"]), "recent": rows[:recent],
            "trend": [{"week": wk.isoformat(), "sprints": n, "avg_wpm": avg} for wk, n, avg in sprint_trend(rows, weeks, today)]}


def sprint_line(r):
    """One sprint on one line: "2026-10-12  the-thornwood/the-last-clause  25 min planned, 18.5 done  412 words  22.3 wpm  target 500: short"."""
    target = f"  target {r['target']:,}: {'met' if r['hit'] else 'short'}" if r["target"] else ""
    ended = {"done": "", "stopped": "  (stopped early)", "left": "  (Writer closed)"}.get(r["reason"], "")
    return (f"{r['date']}  {r['story']}  {r['planned_minutes']:g} min planned, {r['actual_minutes']:g} done  {r['words']:,} words  "
            f"{r['wpm']:g} wpm{target}{ended}")
