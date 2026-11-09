"""Where the evaluation finds the prompt, the pages and the AWS credentials.

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
SECRETS = REPO / "compose/secrets.env"
CREDENTIALS = Path.home() / ".aws" / "credentials"
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


AWS_KEYS = frozenset(
    {"AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN"}
)


def load_env_file() -> None:
    """compose/secrets.env, if there is one: KEY=VALUE lines, the shell's own
    values kept, empty values skipped. Compose reads the same file.

    The AWS keys in it are skipped when ~/.aws/credentials exists. They are
    an export of that file for compose, and an environment variable beats a
    profile in boto3, so a stale export would win over fresh credentials.
    """
    if not SECRETS.exists():
        return
    skip = AWS_KEYS if CREDENTIALS.exists() else frozenset()
    for line in SECRETS.read_text(encoding="utf-8").splitlines():
        key, sep, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if sep and key and not key.startswith("#") and value and key not in skip:
            os.environ.setdefault(key, value)


def aws_profile() -> str | None:
    """The profile boto3 will use, chosen from ~/.aws/credentials when
    AWS_PROFILE does not say. One profile and no [default]: that one.
    A [default]: left to boto3. Several and no default: ask."""
    if os.environ.get("AWS_PROFILE"):
        return os.environ["AWS_PROFILE"]
    if not CREDENTIALS.exists():
        return None
    names: list[str] = re.findall(
        r"^\[(.+?)\]", CREDENTIALS.read_text(encoding="utf-8"), re.MULTILINE
    )
    if "default" in names or not names:
        return None
    if len(names) == 1:
        os.environ["AWS_PROFILE"] = names[0]
        return names[0]
    message = (
        f"{CREDENTIALS} has {len(names)} profiles and no [default]. "
        f"Set AWS_PROFILE to one of: {', '.join(names)}"
    )
    raise SystemExit(message)


NO_CREDENTIALS = (
    "No AWS credentials found. Paste a profile from the AWS access portal into "
    "~/.aws/credentials (or run `aws configure`). With more than one profile and "
    "no [default], set AWS_PROFILE. Temporary credentials expire: paste them "
    "again if Bedrock answers 403."
)


def check_credentials() -> None:
    """Stop before the first model call if boto3 would find no credentials."""
    load_env_file()
    aws_profile()
    import boto3

    if boto3.Session().get_credentials() is None:
        raise SystemExit(NO_CREDENTIALS)


def prepare(content_dir: Path, *, needs_bedrock: bool) -> None:
    if needs_bedrock:
        check_credentials()
    os.environ.setdefault("AWS_REGION", REGION)
    os.environ.setdefault("AWS_DEFAULT_REGION", REGION)
    os.environ["CONTENT_DIR"] = str(content_dir)
    os.environ["SYSTEM_PROMPT_PATH"] = str(PROMPT)
