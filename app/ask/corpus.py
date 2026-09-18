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


def normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def quote_appears_on_page(quote: str, page: Page) -> bool:
    return normalise(quote) in normalise(page.body)


def verify(answer: Answer, corpus: dict[str, Page]) -> Answer:
    """Keep only what the corpus backs up.

    A source is kept only if it names a page we hold. A quoted rule is kept
    only if the words really appear on the page it cites. The front end does
    the same check, but the API should be trustworthy on its own: a wrong
    answer about a rule is the failure that matters most.
    """
    sources = [s for s in answer.sources if s.url in corpus]
    dropped = len(answer.sources) - len(sources)
    if dropped:
        logger.warning("Dropped %d sources not in the corpus", dropped)

    rule = answer.rule_verbatim
    if rule is not None:
        page = corpus.get(rule.source.url)
        if page is None or not quote_appears_on_page(rule.text, page):
            # Logged by page and length only: model output could echo what
            # the person typed, which must never reach the logs.
            logger.warning(
                "Dropped a quoted rule not found on its page url=%s length=%d",
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
    """
    return "\n\n".join(
        f'<page url="{page.url}" title="{page.title}">\n{page.body}\n</page>'
        for page in corpus.values()
    )


def source_for(page: Page) -> Source:
    return Source(title=page.title, url=page.url)
