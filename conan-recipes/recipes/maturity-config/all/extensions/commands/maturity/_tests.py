"""Test report for maturity:build and maturity:coverage (not a command itself).

Turns ctest's JUnit XML (ctest --output-junit) into one self-contained, sortable HTML file, a
markdown summary (console, GitHub job summary, PR comment) and a JSON file with the totals.
"""

import html
import json
import os
import xml.etree.ElementTree as ET

STATUSES = ("failed", "passed", "skipped", "disabled")
# ctest reports a matched SKIP_REGULAR_EXPRESSION or SKIP_RETURN_CODE as "notrun" with these
# messages; any other "notrun" (e.g. a missing executable) fails the ctest run.
SKIP_MESSAGES = ("SKIP_REGULAR_EXPRESSION_MATCHED", "SKIP_RETURN_CODE")


def parse_junit(path):
    """Rows (name, status, time in seconds, message, output) from a ctest JUnit file."""
    rows = []
    for case in ET.parse(path).getroot().iter("testcase"):
        status, message = case.get("status", "run"), ""
        failure, skipped = case.find("failure"), case.find("skipped")
        if status == "disabled":
            status = "disabled"
        elif status == "notrun":
            message = skipped.get("message", "") if skipped is not None else ""
            status = "skipped" if message.startswith(SKIP_MESSAGES) else "failed"
        elif status == "fail" or failure is not None:
            status, message = "failed", (failure.get("message", "") if failure is not None else "")
        else:
            status = "passed"
        rows.append({"name": case.get("name", ""), "status": status,
                     "time": float(case.get("time") or 0), "message": message,
                     "output": case.findtext("system-out") or ""})
    return rows


def totals(rows):
    counts = {status: sum(r["status"] == status for r in rows) for status in STATUSES}
    return {"total": len(rows), **counts, "time": round(sum(r["time"] for r in rows), 6)}


def md(text):
    """Keep a test name from breaking a markdown table cell."""
    return text.replace("|", "\\|")


def summary_markdown(title, rows, slowest=5):
    t = totals(rows)
    lines = [f"### {title}", "",
             f"**{t['passed']} passed**, {t['failed']} failed, {t['skipped']} skipped, "
             f"{t['disabled']} disabled ({t['total']} tests, {t['time']:.2f} s)", ""]
    failed = [r["name"] for r in rows if r["status"] == "failed"]
    if failed:
        lines += ["Failed: " + ", ".join(f"`{name}`" for name in failed), ""]
    timed = sorted((r for r in rows if r["status"] in ("passed", "failed")),
                   key=lambda r: r["time"], reverse=True)[:slowest]
    if timed:
        lines += ["| Slowest tests | Time |", "| --- | --- |",
                  *(f"| `{md(r['name'])}` | {r['time'] * 1000:.1f} ms |" for r in timed), ""]
    return "\n".join(lines)


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
:root {{ --bg:#fff; --fg:#1f2328; --muted:#59636e; --line:#d1d9e0; --head:#f6f8fa;
  --passed:#1a7f37; --failed:#cf222e; --skipped:#9a6700; --disabled:#59636e; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#0d1117; --fg:#e6edf3; --muted:#9198a1;
  --line:#3d444d; --head:#151b23; --passed:#3fb950; --failed:#f85149; --skipped:#d29922;
  --disabled:#9198a1; }} }}
body {{ margin:0; padding:24px 16px; background:var(--bg); color:var(--fg);
  font:14px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; }}
main {{ max-width:1100px; margin:0 auto; }}
h1 {{ font-size:20px; margin:0 0 4px; }} .meta {{ color:var(--muted); margin:0 0 16px; }}
.tiles {{ display:flex; flex-wrap:wrap; gap:8px; margin-bottom:16px; }}
.tile {{ border:1px solid var(--line); border-radius:6px; padding:8px 14px; min-width:90px;
  background:var(--bg); color:var(--fg); font:inherit; text-align:left; cursor:pointer; }}
.tile b {{ display:block; font-size:22px; }} .tile.on {{ outline:2px solid var(--fg); }}
.tile.time {{ cursor:default; }}
.passed b {{ color:var(--passed); }} .failed b {{ color:var(--failed); }}
.skipped b {{ color:var(--skipped); }} .disabled b {{ color:var(--disabled); }}
table {{ width:100%; border-collapse:collapse; }}
th, td {{ text-align:left; padding:6px 10px; border-bottom:1px solid var(--line);
  vertical-align:top; }}
th {{ background:var(--head); cursor:pointer; user-select:none; white-space:nowrap; }}
th[aria-sort=ascending]::after {{ content:" \\25B2"; }}
th[aria-sort=descending]::after {{ content:" \\25BC"; }}
td.num, th.num {{ text-align:right; font-variant-numeric:tabular-nums; }}
.badge {{ font-weight:600; }} .badge.passed {{ color:var(--passed); }}
.badge.failed {{ color:var(--failed); }} .badge.skipped {{ color:var(--skipped); }}
.badge.disabled {{ color:var(--disabled); }}
details summary {{ cursor:pointer; color:var(--muted); }}
pre {{ white-space:pre-wrap; word-break:break-word; margin:6px 0 0; font-size:12px; }}
.wrap {{ overflow-x:auto; }}
</style></head>
<body><main>
<h1>{title}</h1>
<p class="meta">{meta}</p>
<div class="tiles">
<button class="tile on" data-filter="all"><b>{total}</b>tests</button>
<button class="tile passed" data-filter="passed"><b>{passed}</b>passed</button>
<button class="tile failed" data-filter="failed"><b>{failed}</b>failed</button>
<button class="tile skipped" data-filter="skipped"><b>{skipped}</b>skipped</button>
<button class="tile disabled" data-filter="disabled"><b>{disabled}</b>disabled</button>
<div class="tile time"><b>{time}</b>total time</div>
</div>
<div class="wrap"><table id="tests">
<thead><tr><th data-key="name">Test</th><th data-key="status" aria-sort="ascending">Status</th>
<th data-key="time" class="num">Time (ms)</th></tr></thead>
<tbody>
{rows}
</tbody></table></div>
</main>
<script>
(() => {{
  const body = document.querySelector("#tests tbody");
  const heads = document.querySelectorAll("#tests th");
  const order = {{failed: 0, passed: 1, skipped: 2, disabled: 3}};
  const key = (row, k) => k === "time" ? parseFloat(row.dataset.time)
    : k === "status" ? order[row.dataset.status] : row.dataset.name.toLowerCase();
  function sort(th, dir) {{
    const k = th.dataset.key, rows = [...body.rows];
    rows.sort((a, b) => {{
      const x = key(a, k), y = key(b, k);
      return (x < y ? -1 : x > y ? 1 : key(a, "name") < key(b, "name") ? -1 : 1) * dir;
    }});
    heads.forEach(h => h.removeAttribute("aria-sort"));
    th.setAttribute("aria-sort", dir > 0 ? "ascending" : "descending");
    rows.forEach(r => body.appendChild(r));
  }}
  heads.forEach(th => th.addEventListener("click", () =>
    sort(th, th.getAttribute("aria-sort") === "ascending" ? -1 : 1)));
  document.querySelectorAll(".tile[data-filter]").forEach(tile => tile.addEventListener("click", () => {{
    document.querySelectorAll(".tile").forEach(t => t.classList.remove("on"));
    tile.classList.add("on");
    const f = tile.dataset.filter;
    [...body.rows].forEach(r => {{ r.hidden = f !== "all" && r.dataset.status !== f; }});
  }}));
  sort(document.querySelector('th[data-key="status"]'), 1);
}})();
</script>
</body></html>
"""

ROW = ('<tr data-name="{name}" data-status="{status}" data-time="{time}">'
       '<td>{name}{details}</td><td><span class="badge {status}">{status}</span></td>'
       '<td class="num">{ms}</td></tr>')


def write_html(title, meta, rows, path):
    t = totals(rows)
    body = []
    for r in rows:
        details = ""
        if r["status"] != "passed" and (r["message"] or r["output"]):
            text = "\n".join(filter(None, [r["message"], r["output"].rstrip()]))
            details = (f"<details><summary>{html.escape(r['message'] or 'output')}</summary>"
                       f"<pre>{html.escape(text)}</pre></details>")
        body.append(ROW.format(name=html.escape(r["name"], quote=True), status=r["status"],
                               time=r["time"], ms=f"{r['time'] * 1000:.1f}", details=details))
    page = PAGE.format(title=html.escape(title), meta=html.escape(meta), rows="\n".join(body),
                       time=f"{t['time']:.2f} s",
                       **{k: v for k, v in t.items() if k != "time"})
    with open(path, "w", encoding="utf-8") as f:
        f.write(page)


def write_report(junit_path, stem, title, meta):
    """Write <stem>.html, <stem>.md and <stem>.json next to each other from a JUnit file; append
    the markdown to the GitHub job summary when there is one. Returns (totals, markdown)."""
    rows = parse_junit(junit_path)
    write_html(title, meta, rows, stem + ".html")
    text = summary_markdown(title, rows)
    with open(stem + ".md", "w", encoding="utf-8") as f:
        f.write(text)
    t = totals(rows)
    with open(stem + ".json", "w", encoding="utf-8") as f:
        json.dump(t, f, indent=2)
    if target := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(target, "a", encoding="utf-8") as f:
            f.write(text + "\n")
    return t, text


def run_with_report(run_build, junit_path, stem, title, meta):
    """Run a build whose tests write <junit_path>, then write the report, also when the build
    failed on a test. Re-raises the build's error afterwards."""
    from conan.api.output import ConanOutput
    from conan.errors import ConanException

    os.makedirs(os.path.dirname(junit_path), exist_ok=True)
    if os.path.exists(junit_path):
        os.remove(junit_path)  # never report the results of an earlier run
    error = None
    try:
        run_build()
    except ConanException as e:
        error = e
    if os.path.isfile(junit_path):
        _, text = write_report(junit_path, stem, title, meta)
        ConanOutput().info(text)
        ConanOutput().info(f"Test report: file://{stem}.html")
    if error:
        raise error
