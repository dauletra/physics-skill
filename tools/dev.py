#!/usr/bin/env python3
"""Live preview while working on illustrations.

Visual work is the one part of this project a test cannot finish for you: a
picture can pass every assertion and still be ugly. This serves the contact
sheet and the worked example, rebuilds them whenever a source file changes,
and reloads the page — so the loop is "edit, glance", not "edit, run, find
the file, refresh".

    python tools/dev.py              -> http://127.0.0.1:8000
    python tools/dev.py --port 9000

Stdlib only, like everything else here: no watcher library, just a poll over
modification times.
"""

from __future__ import annotations

import argparse
import functools
import http.server
import socketserver
import sys
import threading
import time
import traceback
import webbrowser
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "tools"))

OUTPUT = REPO / "dist" / "dev"
WATCHED = [REPO / "src" / "physics_svg", REPO / "examples", REPO / "tools"]
POLL_SECONDS = 0.5

INDEX = """<!doctype html>
<meta charset="utf-8">
<title>physics-svg — dev</title>
<style>
  body {{ font-family: "PT Sans", "Segoe UI", sans-serif; padding: 32px; max-width: 720px;
         margin: 0 auto; }}
  a {{ display: block; padding: 12px 16px; margin-bottom: 10px; border: 1px solid #ddd;
       border-radius: 8px; color: #111; text-decoration: none; }}
  a:hover {{ background: #f6f6f6; }}
  .status {{ color: #666; font-size: 14px; }}
  .error {{ white-space: pre-wrap; background: #fff4f4; border: 1px solid #f0c0c0;
            padding: 16px; border-radius: 8px; font-family: monospace; font-size: 13px; }}
</style>
<h1>physics-svg — dev</h1>
<p class="status">Сборка {stamp}. Страницы перезагружаются сами при изменении исходников.</p>
{body}
<script>
  // The page asks the server for the current build id; when it changes,
  // whatever is open reloads itself.
  let current = "{stamp}";
  setInterval(async () => {{
    try {{
      const stamp = await (await fetch("/__stamp", {{cache: "no-store"}})).text();
      if (stamp.trim() && stamp.trim() !== current) location.reload();
    }} catch (e) {{}}
  }}, 1000);
</script>
"""

RELOADER = """
<script>
  let current = null;
  setInterval(async () => {
    try {
      const stamp = (await (await fetch("/__stamp", {cache: "no-store"})).text()).trim();
      if (current === null) { current = stamp; }
      else if (stamp && stamp !== current) { location.reload(); }
    } catch (e) {}
  }, 1000);
</script>
"""

_stamp = "0"


def rebuild() -> None:
    """Regenerate everything the browser is looking at."""
    global _stamp
    OUTPUT.mkdir(parents=True, exist_ok=True)
    pages: list[tuple[str, str]] = []
    errors: list[str] = []

    for label, name, builder in (
        ("Контрольный лист иллюстраций", "contact-sheet.html", _contact_sheet),
        ("Пример документа", "document.html", _example_document),
    ):
        try:
            (OUTPUT / name).write_text(builder() + RELOADER, encoding="utf-8")
            pages.append((label, name))
        except Exception:
            errors.append(f"{label}:\n{traceback.format_exc()}")

    _stamp = str(time.time())
    body = "".join(f'<a href="{name}">{label}</a>' for label, name in pages)
    body += "".join(f'<div class="error">{error}</div>' for error in errors)
    (OUTPUT / "index.html").write_text(
        INDEX.format(stamp=_stamp, body=body), encoding="utf-8"
    )
    status = "ошибки: " + str(len(errors)) if errors else "ок"
    print(f"[{time.strftime('%H:%M:%S')}] пересобрано — {status}")
    for error in errors:
        print(error, file=sys.stderr)


def _contact_sheet() -> str:
    import contact_sheet

    return contact_sheet.build(OUTPUT / "_contact.html").read_text(encoding="utf-8")


def _example_document() -> str:
    from physics_svg.document import build_document, load_workspace

    workspace = load_workspace(REPO / "examples" / "kinematics-9th-grade")
    return build_document(workspace.document, workspace.blocks, source=workspace.source)


def _snapshot() -> dict[Path, float]:
    seen: dict[Path, float] = {}
    for root in WATCHED:
        for path in root.rglob("*"):
            if path.is_file() and path.suffix in (".py", ".json", ".md"):
                seen[path] = path.stat().st_mtime
    return seen


def watch() -> None:
    previous = _snapshot()
    while True:
        time.sleep(POLL_SECONDS)
        current = _snapshot()
        if current != previous:
            previous = current
            rebuild()


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 - stdlib naming
        if self.path.startswith("/__stamp"):
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(_stamp.encode())
            return
        super().do_GET()

    def log_message(self, *args: object) -> None:
        pass  # the rebuild log is the only interesting output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args()

    rebuild()
    threading.Thread(target=watch, daemon=True).start()

    # `directory` is a constructor argument, not a class attribute: setting it
    # on the class is silently overwritten by SimpleHTTPRequestHandler.
    handler = functools.partial(Handler, directory=str(OUTPUT))
    with socketserver.TCPServer(("127.0.0.1", args.port), handler) as server:
        url = f"http://127.0.0.1:{args.port}/"
        print(f"Слежу за исходниками, открыто на {url} (Ctrl+C чтобы выйти)")
        if not args.no_open:
            webbrowser.open(url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nПока.")


if __name__ == "__main__":
    main()
