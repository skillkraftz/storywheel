"""Downloads send a normal User-Agent, fall back to curl or wget when a server refuses Python, and fail with a plain message."""
import gzip
import http.server
import os
import shutil
import threading
from pathlib import Path

import pytest

from storywheel import __version__, dictionary_build, download, grammar


class Server:
    """A local server: `policy(user_agent) -> (status, body)`; records the User-Agent of every request."""
    def __init__(self, policy):
        self.seen = []
        outer = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                ua = self.headers.get("User-Agent", "")
                outer.seen.append(ua)
                status, body = policy(ua)
                self.send_response(status)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        self.httpd = http.server.HTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.httpd.server_port}/file.bin"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def close(self):
        self.httpd.shutdown()


@pytest.fixture
def serve():
    servers = []
    def make(policy):
        s = Server(policy)
        servers.append(s)
        return s
    yield make
    for s in servers:
        s.close()


def test_the_user_agent_is_a_normal_one_not_pythons(serve, tmp_path):
    srv = serve(lambda ua: (403, b"no python here") if ua.startswith("Python-urllib") else (200, b"the file"))
    out = download.fetch(srv.url, tmp_path / "f.bin")
    assert out.read_bytes() == b"the file" and srv.seen == [f"storywheel/{__version__}"] and download.USER_AGENT == f"storywheel/{__version__}"


def test_a_server_that_refuses_us_is_tried_again_with_curl(serve, tmp_path):
    if not shutil.which("curl"):
        pytest.skip("curl isn't installed")
    srv = serve(lambda ua: (200, b"curl got it") if ua.startswith("curl/") else (403, b"no"))
    said = []
    out = download.fetch(srv.url, tmp_path / "f.bin", said.append)
    assert out.read_bytes() == b"curl got it" and srv.seen[0].startswith("storywheel/") and srv.seen[-1].startswith("curl/")
    assert any("fetched with curl" in m and "HTTP 403" in m for m in said) and not list(tmp_path.glob("*.part"))


def test_wget_is_the_second_choice(serve, tmp_path, monkeypatch):
    srv = serve(lambda ua: (200, b"wget got it") if ua.startswith("Wget/") else (403, b"no"))
    if not shutil.which("wget"):
        pytest.skip("wget isn't installed")
    real = shutil.which
    monkeypatch.setattr(shutil, "which", lambda name: None if name == "curl" else real(name))
    out = download.fetch(srv.url, tmp_path / "f.bin")
    assert out.read_bytes() == b"wget got it"


def test_nothing_to_fall_back_on_says_so_plainly(serve, tmp_path, monkeypatch):
    srv = serve(lambda ua: (403, b"no"))
    monkeypatch.setattr(shutil, "which", lambda name: None)
    with pytest.raises(download.DownloadError) as e:
        download.fetch(srv.url, tmp_path / "f.bin")
    text = str(e.value)
    assert "HTTP 403" in text and "Neither curl nor wget is installed" in text and "sudo apt install curl" in text and "--from" in text
    assert not (tmp_path / "f.bin").exists() and not list(tmp_path.glob("*.part"))


def test_a_refusal_that_curl_cannot_get_around_either_reports_both(serve, tmp_path):
    if not shutil.which("curl"):
        pytest.skip("curl isn't installed")
    srv = serve(lambda ua: (403, b"no"))
    with pytest.raises(download.DownloadError, match="curl could not fetch it either"):
        download.fetch(srv.url, tmp_path / "f.bin")


def test_a_missing_page_is_not_retried_with_other_tools(serve, tmp_path):
    srv = serve(lambda ua: (404, b"gone"))
    with pytest.raises(download.DownloadError, match="Couldn't download .*HTTP 404"):
        download.fetch(srv.url, tmp_path / "f.bin")
    assert len(srv.seen) == 1


def test_an_unreachable_server_is_a_plain_message(tmp_path):
    with pytest.raises(download.DownloadError, match="Couldn't download"):
        download.fetch("http://127.0.0.1:9/nothing", tmp_path / "f.bin", timeout=2)


def test_grammar_install_uses_it_and_survives_a_403(serve, tmp_path, home):
    import zipfile, io
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("LanguageTool-6.6/languagetool-server.jar", "jar")
    srv = serve(lambda ua: (403, b"python refused") if ua.startswith("Python-urllib") else (200, buf.getvalue()))
    assert grammar.install(None, url=srv.url) == "6.6" and srv.seen == [f"storywheel/{__version__}"]
    assert not (home / "home" / "languagetool-download.zip").exists()


def test_the_dictionary_download_uses_it_too(serve, tmp_path):
    srv = serve(lambda ua: (200, b"source") if ua.startswith("storywheel/") else (403, b"no"))
    assert dictionary_build.download(srv.url, tmp_path / "oewn.xml.gz").read_bytes() == b"source"
    bad = serve(lambda ua: (404, b""))
    with pytest.raises(dictionary_build.DictionaryBuildError, match="Couldn't download"):
        dictionary_build.download(bad.url, tmp_path / "x")
