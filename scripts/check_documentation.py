"""Check local documentation links, anchors, fences, phase numbering and coverage."""

import argparse
import json
import re
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]


def anchors(content):
    result, seen = set(), {}
    for heading in re.findall(r"^#{1,6}\s+(.+)$", content, re.M):
        heading = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", heading).strip().lower()
        slug = "".join(c for c in heading if c.isalnum() or c in " _-").replace(" ", "-")
        number = seen.get(slug, 0)
        seen[slug] = number + 1
        result.add(slug + (f"-{number}" if number else ""))
    result.update(re.findall(r'id="([^"]+)"', content))
    return result


def inspect(paths):
    errors, links = [], 0
    for path in paths:
        name = path.relative_to(ROOT).as_posix()
        content = path.read_text(encoding="utf-8-sig")
        fence = None
        for line in content.splitlines():
            match = re.match(r"^\s*(`{3,}|~{3,})", line)
            if match:
                token = match[1]
                if fence is None:
                    fence = token
                elif token[0] == fence[0] and len(token) >= len(fence):
                    fence = None
        if fence:
            errors.append(f"{name}: unbalanced code fence")
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", content):
            target = target.strip("<>").split(' "')[0]
            if re.match(r"^[a-zA-Z]+:", target):
                continue
            filename, _, anchor = unquote(target).partition("#")
            destination = path.parent / filename if filename else path
            if not destination.exists():
                errors.append(f"{name}: missing {target}")
                continue
            links += 1
            if anchor and destination.suffix.lower() == ".md":
                if anchor not in anchors(destination.read_text(encoding="utf-8-sig")):
                    errors.append(f"{name}: missing anchor {target}")
    return links, errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Write a new JSON report; never overwrite")
    args = parser.parse_args()
    paths = [
        ROOT / name
        for name in [
            "README.md",
            "SECURITY.md",
            "AGENTS.md",
            "WORKFLOW_PLATFORM_IMPLEMENTATION_PLAN.md",
        ]
    ]
    paths += sorted((ROOT / "docs").glob("*.md"))
    links, errors = inspect(paths)
    phases = [
        int(n)
        for n in re.findall(
            r"^# Phase (\d+):", (ROOT / "docs/phases.md").read_text(encoding="utf-8"), re.M
        )
    ]
    if phases != list(range(1, 106)):
        errors.append("Phase headings must be unique and ordered from 1 through 105")
    expected = [f"R{n:02}" for n in range(1, 15)]
    for name in ["WORKFLOW_PLATFORM_IMPLEMENTATION_PLAN.md", "docs/PLATFORM_EVIDENCE.md"]:
        rows = re.findall(r"^\| (R\d{2})\b", (ROOT / name).read_text(encoding="utf-8-sig"), re.M)
        if rows != expected:
            errors.append(f"{name}: R01–R14 table must cover every requirement exactly once")
    report = {
        "documents": len(paths),
        "local_links": links,
        "phase_headings": len(phases),
        "requirements_per_table": len(expected),
        "errors": errors,
        "passed": not errors,
        "scope": (
            "Local inline Markdown links/anchors, fences, phase headings and requirement tables; "
            "external URLs and semantic claims require separate review"
        ),
    }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    raise SystemExit(bool(errors))


if __name__ == "__main__":
    main()
