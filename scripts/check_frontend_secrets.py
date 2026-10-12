"""Fail CI if frontend source contains server secret names or credential-like literals."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
SECRET_NAMES = re.compile(r"\b(?:API_SECRET_KEY|OMI_WEBHOOK_SECRET|QDRANT_API_KEY|LYZR_API_KEY)\b", re.I)
TOKEN_LITERALS = re.compile(
    r"(?i)(?:sk-[a-z0-9_-]{24,}|(?:api|secret|token|key)[_-]?[=:]\s*['\"][a-z0-9_./+=-]{24,})"
)


def main() -> int:
    findings: list[str] = []
    for path in FRONTEND.rglob("*"):
        if not path.is_file() or path.suffix.lower() in {".png", ".jpg", ".jpeg", ".ico", ".woff", ".woff2"}:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if SECRET_NAMES.search(content) or TOKEN_LITERALS.search(content):
            findings.append(str(path.relative_to(ROOT)))
    if findings:
        print("Possible server-side secret reference or credential in frontend files:")
        print("\n".join(findings))
        return 1
    print("Frontend secret audit passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
