import io
import tarfile

import pytest

import fetch_content


def tarball(files: dict[str, str], top: str = "service-manual-ui-abc123") -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for name, text in files.items():
            data = text.encode("utf-8")
            info = tarfile.TarInfo(f"{top}/{name}")
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


SITE = {
    "src/content/ai-toolkit.md": "---\ntitle: AI toolkit\n---\nHello",
    "src/content/ai-toolkit/using-ai/index.md": "---\ntitle: Using AI\n---\nRules",
    "src/content/ai-toolkit/using-ai/diagram.png": "not a page",
    "src/content/ai-toolkit-triage.md": "a different section that shares the prefix",
    "src/content/accessibility.md": "not the toolkit",
    "README.md": "not content",
}


def test_extract_keeps_only_toolkit_markdown(tmp_path):
    written = fetch_content.extract(tarball(SITE), tmp_path)

    assert sorted(p.relative_to(tmp_path).as_posix() for p in written) == [
        "ai-toolkit.md",
        "ai-toolkit/using-ai/index.md",
    ]
    assert (tmp_path / "ai-toolkit/using-ai/index.md").read_text() == SITE[
        "src/content/ai-toolkit/using-ai/index.md"
    ]
    assert not (tmp_path / "accessibility.md").exists()
    assert not (tmp_path / "ai-toolkit-triage.md").exists()


def test_extract_refuses_a_path_that_escapes_dest(tmp_path):
    archive = tarball({"src/content/ai-toolkit/../../../escape.md": "out"})

    with pytest.raises(SystemExit, match="outside"):
        fetch_content.extract(archive, tmp_path / "content")

    assert not (tmp_path / "escape.md").exists()


def test_fetch_records_the_ref(tmp_path, monkeypatch):
    urls = []

    def fake_download(url):
        urls.append(url)
        return tarball(SITE)

    monkeypatch.setattr(fetch_content, "download", fake_download)

    fetch_content.fetch("caefc03", tmp_path)

    assert urls == ["https://github.com/DEFRA/service-manual-ui/archive/caefc03.tar.gz"]
    assert (tmp_path / "REF").read_text() == "caefc03\n"


def test_fetch_fails_when_the_ref_has_no_toolkit(tmp_path, monkeypatch):
    monkeypatch.setattr(
        fetch_content, "download", lambda _url: tarball({"README.md": "empty"})
    )

    with pytest.raises(SystemExit, match="no toolkit pages"):
        fetch_content.fetch("caefc03", tmp_path)

    assert not (tmp_path / "REF").exists()


def test_main_prints_the_count(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(fetch_content, "download", lambda _url: tarball(SITE))

    fetch_content.main(["--ref", "caefc03", "--dest", str(tmp_path)])

    assert capsys.readouterr().out.strip() == (
        f"2 toolkit pages from DEFRA/service-manual-ui@caefc03 into {tmp_path}"
    )
