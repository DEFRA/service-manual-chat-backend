"""Fetch the toolkit pages from service-manual-ui at a pinned ref.

The image is built without a sibling checkout of the site, so the Dockerfile
runs this to put `src/content/ai-toolkit.md` and `src/content/ai-toolkit/`
from a GitHub tarball into `content/`, the same layout compose bind-mounts
locally. The ref goes into `content/REF` so the service can log which pages
it answers from. Standard library only: it runs before `uv sync`.

    python3 scripts/fetch_content.py --ref <sha or branch> --dest content
"""

import argparse
import io
import sys
import tarfile
from pathlib import Path
from urllib.request import urlopen

REPO = "DEFRA/service-manual-ui"
SOURCE_PREFIX = "src/content/"
PAGES = ("ai-toolkit.md", "ai-toolkit/")
REF_FILE = "REF"


def tarball_url(ref: str) -> str:
    return f"https://github.com/{REPO}/archive/{ref}.tar.gz"


def download(url: str) -> bytes:
    with urlopen(url, timeout=60) as response:  # noqa: S310 - https URL built above
        return response.read()


def is_page(relative: str) -> bool:
    return any(
        relative == page or relative.startswith(page) for page in PAGES
    ) and relative.endswith(".md")


def extract(archive: bytes, dest: Path) -> list[Path]:
    """Write every toolkit page in the tarball under dest and return their paths."""
    written: list[Path] = []
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
        for member in tar.getmembers():
            if not member.isfile():
                continue
            # GitHub tarballs put everything under one top-level directory
            # named after the repo and ref; drop it.
            _, _, inside = member.name.partition("/")
            if not inside.startswith(SOURCE_PREFIX):
                continue
            relative = inside.removeprefix(SOURCE_PREFIX)
            if not is_page(relative):
                continue
            target = dest / relative
            if not target.resolve().is_relative_to(dest.resolve()):
                message = f"refusing to write outside {dest}: {member.name}"
                raise SystemExit(message)
            target.parent.mkdir(parents=True, exist_ok=True)
            with tar.extractfile(member) as source:  # type: ignore[union-attr]
                target.write_bytes(source.read())
            written.append(target)
    return written


def fetch(ref: str, dest: Path) -> list[Path]:
    written = extract(download(tarball_url(ref)), dest)
    if not written:
        message = f"no toolkit pages found in {REPO} at {ref}"
        raise SystemExit(message)
    (dest / REF_FILE).write_text(f"{ref}\n", encoding="utf-8")
    return written


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--ref", required=True, help="commit sha, tag or branch")
    parser.add_argument("--dest", default="content", type=Path)
    args = parser.parse_args(argv)
    written = fetch(args.ref, args.dest)
    print(f"{len(written)} toolkit pages from {REPO}@{args.ref} into {args.dest}")


if __name__ == "__main__":  # pragma: no cover
    main(sys.argv[1:])
