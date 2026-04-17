"""
scripts/security_audit.py — EngCAD Static Security Scanner
───────────────────────────────────────────────────────────
Scans the Python codebase for:
  1. Hardcoded secrets / credentials
  2. SQL injection patterns (string-formatted queries)
  3. Insecure cryptography (MD5, SHA1)
  4. Unsafe deserialization (pickle.loads)
  5. Shell injection risks (os.system, subprocess without list)
  6. Debug / development flags left active

Usage:
  python scripts/security_audit.py [--path .] [--fail-on-issue]

Exit codes: 0 = clean, 1 = issues found (when --fail-on-issue)
"""
from __future__ import annotations

import argparse
import ast
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# ─────────────────────────────────────────────────────────────
# Pattern definitions
# ─────────────────────────────────────────────────────────────

SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("Hardcoded password",        re.compile(r'password\s*=\s*["\'][^"\']{4,}["\']', re.IGNORECASE)),
    ("Hardcoded secret key",      re.compile(r'secret[_-]?key\s*=\s*["\'][^"\']{8,}["\']', re.IGNORECASE)),
    ("Hardcoded API key",         re.compile(r'api[_-]?key\s*=\s*["\'][^"\']{8,}["\']', re.IGNORECASE)),
    ("Hardcoded token",           re.compile(r'token\s*=\s*["\'][A-Za-z0-9+/._-]{20,}["\']', re.IGNORECASE)),
    ("AWS access key literal",    re.compile(r'AKIA[0-9A-Z]{16}')),
    ("Private key PEM header",    re.compile(r'-----BEGIN (RSA|EC|DSA|OPENSSH) PRIVATE KEY-----')),
]

SQL_INJECTION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("SQL string format (%)",     re.compile(r'execute\s*\(\s*["\'][^"\']*%[sd][^"\']*["\'\s]*%')),
    ("SQL f-string",              re.compile(r'execute\s*\(\s*f["\']')),
    ("SQL + concatenation",       re.compile(r'execute\s*\(\s*["\'][^"\']*"\s*\+\s*')),
]

UNSAFE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("MD5 usage",                 re.compile(r'hashlib\.md5\(')),
    ("SHA1 usage",                re.compile(r'hashlib\.sha1\(')),
    ("pickle.loads",              re.compile(r'pickle\.loads\(')),
    ("eval() call",               re.compile(r'\beval\s*\(')),
    ("exec() call",               re.compile(r'\bexec\s*\(')),
    ("os.system() call",          re.compile(r'\bos\.system\s*\(')),
    ("shell=True in subprocess",  re.compile(r'subprocess\.[a-z_]+\([^)]*shell\s*=\s*True')),
    ("DEBUG=True",                re.compile(r'\bDEBUG\s*=\s*True')),
    ("verify=False in requests",  re.compile(r'requests\.[a-z]+\([^)]*verify\s*=\s*False')),
]

ALL_RULES = [
    ("SECRET",       SECRET_PATTERNS),
    ("SQL_INJECTION", SQL_INJECTION_PATTERNS),
    ("UNSAFE",       UNSAFE_PATTERNS),
]

ALLOWLIST_COMMENTS = {"nosec", "noaudit", "audit:ignore"}

# ─────────────────────────────────────────────────────────────
# Data types
# ─────────────────────────────────────────────────────────────

@dataclass
class Finding:
    category: str
    rule: str
    file: str
    line: int
    content: str
    severity: str = "HIGH"

# ─────────────────────────────────────────────────────────────
# Scanner
# ─────────────────────────────────────────────────────────────

def _is_allowlisted(line_text: str) -> bool:
    lower = line_text.lower()
    return any(tag in lower for tag in ALLOWLIST_COMMENTS)


def scan_file(path: Path) -> list[Finding]:
    findings: list[Finding] = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return findings

    lines = text.splitlines()
    for lineno, line in enumerate(lines, start=1):
        if _is_allowlisted(line):
            continue
        for category, rules in ALL_RULES:
            for rule_name, pattern in rules:
                if pattern.search(line):
                    findings.append(Finding(
                        category=category,
                        rule=rule_name,
                        file=str(path),
                        line=lineno,
                        content=line.strip()[:120],
                    ))
    return findings


def scan_directory(root: Path, exclude: list[str] | None = None) -> list[Finding]:
    exclude_dirs = set(exclude or [".venv", "venv", "node_modules", "__pycache__", ".git", "alembic/versions"])
    all_findings: list[Finding] = []
    for py_file in root.rglob("*.py"):
        # Skip excluded directories
        if any(part in exclude_dirs for part in py_file.parts):
            continue
        all_findings.extend(scan_file(py_file))
    return all_findings


# ─────────────────────────────────────────────────────────────
# Reporting
# ─────────────────────────────────────────────────────────────

def print_report(findings: list[Finding], root: Path) -> None:
    if not findings:
        print("✅  No security issues found.")
        return

    by_category: dict[str, list[Finding]] = {}
    for f in findings:
        by_category.setdefault(f.category, []).append(f)

    print(f"\n{'='*70}")
    print(f"  EngCAD Security Audit — {len(findings)} issue(s) found")
    print(f"{'='*70}\n")

    for category, items in sorted(by_category.items()):
        print(f"[{category}] — {len(items)} issue(s)")
        print("-" * 60)
        for item in items:
            try:
                rel_path = Path(item.file).relative_to(root)
            except ValueError:
                rel_path = Path(item.file)
            print(f"  [{item.severity}] {item.rule}")
            print(f"    File : {rel_path}:{item.line}")
            print(f"    Code : {item.content}")
            print()


# ─────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="EngCAD static security scanner")
    parser.add_argument("--path", default=".", help="Root path to scan (default: current dir)")
    parser.add_argument("--fail-on-issue", action="store_true", help="Exit 1 if any issues are found (for CI)")
    parser.add_argument("--exclude", nargs="*", default=None, help="Additional dirs to exclude")
    args = parser.parse_args()

    root = Path(args.path).resolve()
    print(f"Scanning: {root}")

    findings = scan_directory(root, exclude=args.exclude)
    print_report(findings, root)

    summary = {cat: 0 for cat in ("SECRET", "SQL_INJECTION", "UNSAFE")}
    for f in findings:
        summary[f.category] = summary.get(f.category, 0) + 1

    print(f"Summary: {summary}")

    if args.fail_on_issue and findings:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
