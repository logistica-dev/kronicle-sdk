#!/usr/bin/env python3
"""Build shields.io endpoint badge payloads from a tox journal and coverage report.

Invoked by the `tox` job in .github/workflows/ci.yml just after
`tox run-parallel --result-json`:

    python3 .github/scripts/make_badges.py <journal.json> <coverage.xml> <out-dir> [pyproject.toml]

`journal.json` is tox's own `--result-json` report, which tox writes from a
`finally` block: it is therefore present even when an environment fails, and it
records every environment's result regardless of earlier failures (tox's
`--fail-fast` defaults to off).

Which interpreters to expect comes from `[tool.tox].env_list`, so the badge
follows tox's own configuration instead of a list duplicated here; non
interpreter envs (e.g. `quality`) are excluded by name. An interpreter that is
missing from the journal counts as failed, so a config that never ran cannot
render as green.

`coverage.xml` is coverage.py's XML report, produced by the single tox env that
instruments the run ([tool.tox.env.py312] — the other envs pass --no-cov, so
there is exactly one report to read).

Writes `python.json` and `coverage.json` into <out-dir>.
"""

from __future__ import annotations

import json
import re
import sys
import tomllib
from pathlib import Path
from xml.etree import ElementTree

INTERPRETER_ENV = re.compile(r"^py(\d+)$")


def expected_interpreters(pyproject: Path) -> list[tuple[str, str]]:
    """[(env_name, label)] from [tool.tox].env_list, e.g. ('py311', '3.11')."""
    if not pyproject.exists():
        return []
    config = tomllib.loads(pyproject.read_text())
    env_list = config.get("tool", {}).get("tox", {}).get("env_list") or []
    found: list[tuple[tuple[int, int], str, str]] = []
    for env in env_list:
        match = INTERPRETER_ENV.match(str(env))
        if match:
            digits = match.group(1)
            version = (int(digits[0]), int(digits[1:]))
            found.append((version, str(env), f"{version[0]}.{version[1]}"))
    return [(env, label) for _, env, label in sorted(found)]


def journal_results(journal: Path) -> dict[str, bool]:
    """Map tox env name -> passed, from tox's --result-json report."""
    testenvs = json.loads(journal.read_text()).get("testenvs", {})
    return {env: bool(data.get("result", {}).get("success")) for env, data in testenvs.items()}


def coverage_percent(coverage: Path) -> float | None:
    """Line-coverage percentage from coverage.py's XML report."""
    if not coverage.exists():
        return None
    root = ElementTree.parse(coverage).getroot()
    valid = int(root.get("lines-valid") or 0)
    return 100.0 * int(root.get("lines-covered") or 0) / valid if valid else None


def percent_color(percent: float) -> str:
    if percent >= 100:
        return "brightgreen"
    if percent >= 90:
        return "green"
    if percent >= 75:
        return "yellow"
    return "red"


def write_badge(out_dir: Path, name: str, label: str, message: str, color: str) -> None:
    payload = {"schemaVersion": 1, "label": label, "message": message, "color": color}
    (out_dir / name).write_text(json.dumps(payload) + "\n")


def python_badge(out_dir: Path, expected: list[tuple[str, str]], results: dict[str, bool]) -> None:
    if not expected:
        write_badge(out_dir, "python.json", "python", "no result", "lightgrey")
        return
    broken = [label for env, label in expected if not results.get(env, False)]
    if broken:
        write_badge(out_dir, "python.json", "python", "failed: " + " ".join(broken), "red")
    else:
        write_badge(out_dir, "python.json", "python", " | ".join(label for _, label in expected), "brightgreen")


def coverage_badge(out_dir: Path, coverage: Path) -> None:
    percent = coverage_percent(coverage)
    if percent is None:
        write_badge(out_dir, "coverage.json", "coverage", "unknown", "lightgrey")
        return
    message = f"{percent:.2f}".rstrip("0").rstrip(".") + "%"
    write_badge(out_dir, "coverage.json", "coverage", message, percent_color(percent))


def main(argv: list[str]) -> int:
    if not 4 <= len(argv) <= 5:
        print(__doc__, file=sys.stderr)
        return 2
    journal, coverage, out_dir = (Path(arg) for arg in argv[1:4])
    pyproject = Path(argv[4]) if len(argv) == 5 else Path("pyproject.toml")
    out_dir.mkdir(parents=True, exist_ok=True)

    if journal.exists():
        expected = expected_interpreters(pyproject)
        python_badge(out_dir, expected, journal_results(journal))
    else:
        # tox never got far enough to write the journal: report a red badge
        # rather than leaving the published one stale.
        print(f"warning: {journal} not found", file=sys.stderr)
        python_badge(out_dir, expected_interpreters(pyproject), {})
    coverage_badge(out_dir, coverage)

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
