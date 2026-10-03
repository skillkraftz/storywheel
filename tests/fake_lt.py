"""A stand-in for the LanguageTool HTTP server: python fake_lt.py PORT. Environment: FAKE_LT_LOG (append every text it is asked about),
FAKE_LT_DELAY (seconds to wait before answering), FAKE_LT_BROKEN (answer with junk)."""
import json
import os
import sys
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

# word -> (rule id, category id, message, replacements)
RULES = {
    "alot": ("ALOT", "GRAMMAR", "'alot' is not a word. Did you mean 'a lot'?", ["a lot", "allot"]),
    "teh": ("MORFOLOGIK_RULE_EN_US", "TYPOS", "Possible spelling mistake.", ["the"]),
    "very": ("VERY_STYLE", "STYLE", "Consider a stronger word than 'very'.", ["really"]),
    "their is": ("THEIR_IS", "CONFUSED_WORDS", "Did you mean 'there is'?", ["there is"]),
}


def u16(text, i):
    return len(text[:i].encode("utf-16-le")) // 2


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self._send(200, "[]")

    def do_POST(self):
        form = urllib.parse.parse_qs(self.rfile.read(int(self.headers.get("Content-Length", 0))).decode("utf-8"))
        text = form.get("text", [""])[0]
        if os.environ.get("FAKE_LT_LOG"):
            with open(os.environ["FAKE_LT_LOG"], "a", encoding="utf-8") as f:
                f.write(json.dumps({"text": text, "cats": form.get("disabledCategories", [""])[0], "rules": form.get("disabledRules", [""])[0]}) + "\n")
        time.sleep(float(os.environ.get("FAKE_LT_DELAY", "0")))
        if os.environ.get("FAKE_LT_BROKEN"):
            return self._send(200, "<html>nonsense")
        off_c = set(form.get("disabledCategories", [""])[0].split(","))
        off_r = set(form.get("disabledRules", [""])[0].split(","))
        matches = []
        for needle, (rule, cat, msg, reps) in RULES.items():
            start = 0
            while (i := text.find(needle, start)) >= 0:
                start = i + len(needle)
                if rule in off_r or cat in off_c:
                    continue
                matches.append({"message": msg, "offset": u16(text, i), "length": u16(text, i + len(needle)) - u16(text, i),
                                "replacements": [{"value": r} for r in reps], "rule": {"id": rule, "description": msg, "category": {"id": cat, "name": cat}}})
        matches.sort(key=lambda m: m["offset"])
        self._send(200, json.dumps({"software": {"name": "FakeLanguageTool"}, "matches": matches}))


if __name__ == "__main__":
    HTTPServer(("127.0.0.1", int(sys.argv[1])), Handler).serve_forever()
