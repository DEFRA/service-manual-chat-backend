"""The toolkit pages the model answers from.

Locally this is a read-only mount of service-manual-ui `src/content`, so the
backend serves exactly what the site serves. A page's URL is its path under
the content directory without the `.md`, which is the same mapping the front
end uses when it checks a quote against a page.
"""

import re
from dataclasses import dataclass
from logging import getLogger
from pathlib import Path

from app.ask.quote_check import check_quote, strip_inline_tags
from app.ask.schemas import Answer, Source

logger = getLogger(__name__)

FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
TITLE = re.compile(r"^title:\s*(.+?)\s*$", re.MULTILINE)


@dataclass(frozen=True)
class Page:
    url: str
    title: str
    body: str


def parse_page(url: str, text: str) -> Page:
    match = FRONTMATTER.match(text)
    frontmatter = match.group(1) if match else ""
    body = text[match.end() :] if match else text
    title_match = TITLE.search(frontmatter)
    title = title_match.group(1).strip("'\"") if title_match else url
    return Page(url=url, title=title, body=body.strip())


def content_ref(content_dir: Path) -> str | None:
    """The service-manual-ui ref the pages came from, or None for a mount.

    `scripts/fetch_content.py` writes `REF` next to the pages when it bakes
    them into the image. A bind mount of the site checkout has no such file.
    """
    ref_file = content_dir / "REF"
    if not ref_file.is_file():
        return None
    return ref_file.read_text(encoding="utf-8").strip() or None


def load_corpus(content_dir: Path, prefix: str = "ai-toolkit") -> dict[str, Page]:
    """Every markdown page under the prefix, keyed by URL.

    `ai-toolkit.md` and `ai-toolkit/**.md` both belong to the toolkit.
    """
    pages: dict[str, Page] = {}
    candidates = [
        content_dir / f"{prefix}.md",
        *sorted((content_dir / prefix).rglob("*.md")),
    ]
    for path in candidates:
        if not path.is_file():
            continue
        url = "/" + path.relative_to(content_dir).with_suffix("").as_posix()
        pages[url] = parse_page(url, path.read_text(encoding="utf-8"))
    logger.info("Loaded %d toolkit pages from %s", len(pages), content_dir)
    return pages


def verify(answer: Answer, corpus: dict[str, Page]) -> Answer:
    """Keep only what the corpus backs up.

    A source is kept only if it names a page we hold. A quoted rule is kept
    only if its words really appear on the page it cites, whole and in order:
    a quote that starts or stops part way through a sentence is dropped too,
    and logged as its own failure, because a rule quoted selectively can say
    the opposite of the rule. The front end does the same check, but the API
    should be trustworthy on its own: a wrong answer about a rule is the
    failure that matters most.
    """
    sources = [s for s in answer.sources if s.url in corpus]
    dropped = len(answer.sources) - len(sources)
    if dropped:
        logger.warning("Dropped %d sources not in the corpus", dropped)

    rule = answer.rule_verbatim
    if rule is not None:
        page = corpus.get(rule.source.url)
        outcome = "no_page" if page is None else check_quote(rule.text, page.body)
        if outcome != "ok":
            # Logged by page, length and which check failed, never the words:
            # model output could echo what the person typed, which must never
            # reach the logs.
            logger.warning(
                "Dropped a quoted rule outcome=%s url=%s length=%d",
                outcome,
                rule.source.url,
                len(rule.text),
            )
            rule = None

    return answer.model_copy(update={"sources": sources, "rule_verbatim": rule})


def as_context(corpus: dict[str, Page]) -> str:
    """The whole toolkit as one block for the model.

    About 35k tokens for 43 pages. Fine for a local loop where the
    instructions are cached; retrieval (E3) replaces this before anything
    faces the public.

    Inline tags are stripped so the model reads a rule the way the reader
    does. Ten rules sit inside `<li><strong>`, and a model that quotes through
    the tags is quoting text nobody sees.
    """
    return "\n\n".join(
        f'<page url="{page.url}" title="{page.title}">\n'
        f"{strip_inline_tags(page.body)}\n</page>"
        for page in corpus.values()
    )


def source_for(page: Page) -> Source:
    return Source(title=page.title, url=page.url)
