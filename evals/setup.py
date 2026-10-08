"""Where the evaluation finds the prompt, the pages and the Bedrock key.

Call `prepare()` before importing anything from `app`: app.config reads the
environment once, at import.
"""

import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
EVALS = REPO / "evals"
RESULTS = EVALS / "results"
PROMPT = REPO / "prompts/system.md"
SECRETS = REPO / ".env"
REGION = "eu-west-2"


def dockerfile_content_ref() -> str:
    """The service-manual-ui commit the image is built with."""
    text = (REPO / "Dockerfile").read_text(encoding="utf-8")
    match = re.search(r"^ARG CONTENT_REF=(\S+)", text, re.MULTILINE)
    if not match:
        message = "no ARG CONTENT_REF=<sha> in the Dockerfile"
        raise SystemExit(message)
    return match.group(1)


def git(directory: Path, *args: str) -> str:
    result = subprocess.run(  # noqa: S603 - fixed git arguments
        ["git", "-C", str(directory), *args],  # noqa: S607
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip()


def local_ref(content_dir: Path) -> str:
    """A local checkout's commit, marked when its pages have uncommitted edits."""
    sha = git(content_dir, "rev-parse", "--short=12", "HEAD") or "unknown"
    dirty = git(content_dir, "status", "--porcelain", "--", ".")
    return f"local {sha}{' with uncommitted edits' if dirty else ''}"


def content(
    content_dir: Path | None = None, ref: str | None = None
) -> tuple[Path, str]:
    """The toolkit pages and the ref that names them.

    With no directory, the pages at `ref` (default: the Dockerfile's) are
    fetched once into evals/.content/<ref>, so a run answers from exactly
    what the deployed service answers from.
    """
    if content_dir:
        return content_dir.resolve(), local_ref(content_dir)
    ref = ref or dockerfile_content_ref()
    dest = EVALS / ".content" / ref
    if not (dest / "REF").exists():
        subprocess.run(  # noqa: S603 - our own script, a ref from the Dockerfile or a run
            [
                sys.executable,
                str(REPO / "scripts/fetch_content.py"),
                "--ref",
                ref,
                "--dest",
                str(dest),
            ],
            check=True,
        )
    return dest, ref


def prompt_version() -> str:
    """The prompt's content hash and the commit it sits on."""
    sha = hashlib.sha256(PROMPT.read_bytes()).hexdigest()[:12]
    commit = git(REPO, "rev-parse", "--short=7", "HEAD") or "unknown"
    edited = git(REPO, "status", "--porcelain", "--", str(PROMPT))
    return f"{sha} on {commit}{' with uncommitted edits' if edited else ''}"


def load_secrets() -> None:
    """Put the Bedrock key in the environment without printing it."""
    if os.environ.get("AWS_BEARER_TOKEN_BEDROCK"):
        return
    if SECRETS.exists():
        for line in SECRETS.read_text(encoding="utf-8").splitlines():
            key, sep, value = line.partition("=")
            if sep and key.strip() == "AWS_BEARER_TOKEN_BEDROCK" and value.strip():
                os.environ["AWS_BEARER_TOKEN_BEDROCK"] = value.strip()
                return
    message = f"Set AWS_BEARER_TOKEN_BEDROCK, or put it in {SECRETS.relative_to(REPO)}"
    raise SystemExit(message)


def prepare(content_dir: Path, *, needs_bedrock: bool) -> None:
    if needs_bedrock:
        load_secrets()
    os.environ.setdefault("AWS_REGION", REGION)
    os.environ.setdefault("AWS_DEFAULT_REGION", REGION)
    os.environ["CONTENT_DIR"] = str(content_dir)
    os.environ["SYSTEM_PROMPT_PATH"] = str(PROMPT)
