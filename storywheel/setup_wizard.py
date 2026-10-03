"""`storywheel setup`: a short questionnaire for a new machine. Answers are remembered (settings.local.toml: setup_done), so running it again
only asks the questions that are new; `storywheel setup --again` asks everything. Every answer can be changed later in Settings (F4)."""
import shutil
from pathlib import Path

from . import paths, settings, tools

# Each question: (id, title). The asking is in ask_<id>; they receive the Setup object.
QUESTIONS = ("author", "folders", "window", "transparent", "dictionary", "update")


class Setup:
    def __init__(self, ask=input, say=print, again=False, defaults=False):
        self._ask, self.say, self.again, self.defaults = ask, say, again, defaults
        self.g = settings.load_global()

    # --- asking ----------------------------------------------------------------------------------------------------------------------

    def ask(self, prompt, default=""):
        if self.defaults:
            return default
        shown = f" [{default}]" if default not in ("", None) else ""
        try:
            answer = self._ask(f"  {prompt}{shown}: ")
        except EOFError:
            answer = ""
        answer = (answer or "").strip()
        return answer if answer else default

    def yes(self, prompt, default=True):
        answer = self.ask(f"{prompt} (y/n)", "y" if default else "n").lower()
        return answer.startswith("y")

    def done(self):
        return list(self.g.get("setup_done") or [])

    def mark(self, qid):
        done = self.done()
        if qid not in done:
            done.append(qid)
        settings.save_global({"setup_done": done})
        self.g = settings.load_global()

    # --- the questions -----------------------------------------------------------------------------------------------------------------

    def ask_author(self):
        self.say("Your details go on the first page of a manuscript (Shunn format). You can leave any blank and fill them in later.")
        values = {}
        values["author_name"] = self.ask("Name on the byline (your pen name, or your name)", self.g.get("author_name", ""))
        values["legal_name"] = self.ask("Legal name for the contact block", self.g.get("legal_name", "") or values["author_name"])
        values["address"] = self.ask("Address (use / between lines)", (self.g.get("address", "") or "").replace("\n", " / ")).replace(" / ", "\n")
        values["email"] = self.ask("Email", self.g.get("email", ""))
        values["phone"] = self.ask("Phone", self.g.get("phone", ""))
        settings.save_global(values)

    def ask_folders(self):
        lib = self.ask("Folder for your library (universes, stories, manuscripts)", paths.tilde(paths.library_root()))
        man = self.ask("Folder for exported manuscripts", paths.tilde(paths.manuscripts_root()))
        for key, value in (("library", lib), ("manuscripts_dir", man)):
            path = Path(value).expanduser()
            path.mkdir(parents=True, exist_ok=True)
            settings.save_global({key: str(path)})

    def ask_window(self):
        if not shutil.which("neovide") and tools.is_arm64():
            self.say(tools.NEOVIDE_ARM64)
            settings.save_global({"neovide": False})
        elif shutil.which("neovide"):
            use = self.yes("Neovide is installed. Write in its own window rather than in this terminal?", bool(self.g.get("neovide")))
            settings.save_global({"neovide": use})
        else:
            self.say("The Writer will open in this terminal. (Neovide is an optional window with real line spacing; "
                     + tools.missing("neovide").split(". ", 1)[1] + ")")
            settings.save_global({"neovide": False})

    def ask_transparent(self):
        settings.save_global({"transparent_background": self.yes(
            "Use your terminal's own background (so its transparency shows through)?", bool(self.g.get("transparent_background", True)))})

    def ask_dictionary(self):
        from . import dictionary
        if dictionary.installed():
            self.say("The dictionary is already installed.")
            return
        if self.yes("Fetch the offline dictionary and thesaurus now? (a one-time download of about 36 MB)", True):
            from . import cli_world
            import argparse
            try:
                cli_world.cmd_dictionary(argparse.Namespace(action="install", json=False, oewn=None, moby=None))
            except SystemExit:
                self.say("The download did not finish. Run  storywheel dictionary install  to try again.")
        else:
            self.say("Skipped. Words and spellcheck will say what to run:  storywheel dictionary install")

    def ask_update(self):
        current = self.g.get("update_remote") or ""
        self.say("`storywheel update` reinstalls from the folder storywheel was installed from (fetching its git remote first, if it has one). "
                 "A remote here is optional: it is used only if that folder is gone (a git URL, or user@host:path/storywheel). Leave it blank to skip.")
        settings.save_global({"update_remote": self.ask("Git remote to update from", current)})

    # --- running -------------------------------------------------------------------------------------------------------------------------

    def run(self):
        todo = [q for q in QUESTIONS if self.again or q not in self.done()]
        if not todo:
            self.say("Setup is already done on this machine. Everything can be changed in Settings (F4); `storywheel setup --again` asks "
                     "all the questions again.")
            return []
        self.say(f"storywheel setup: {len(todo)} question(s).\n")
        for q in todo:
            getattr(self, "ask_" + q)()
            self.mark(q)
            self.say("")
        self.say("Done. Change any of this later in Settings (F4). Start writing with:  storywheel")
        return todo


def run(ask=input, say=print, again=False, defaults=False):
    return Setup(ask, say, again, defaults).run()
