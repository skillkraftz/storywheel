"""
Writing statistics, read from each story's stats.json (the Writer keeps them) and its manuscript.

    days()                 {date: words} across every story in the library
    streak(days, today)    (current streak, best streak) in days
    summary(universe, story)   everything the Builder's stats box and the Settings stats tab show
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
    """Forget a story's recorded history (its days and sessions). The manuscript is not touched. Returns the words that were recorded."""
    before = sum(story_days(story).values())
    story.stats_path.write_text(json.dumps({"days": {}, "sessions": []}, indent=2), encoding="utf-8")
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
