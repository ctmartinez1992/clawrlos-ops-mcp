import re
from xml.etree import ElementTree

import httpx

ARXIV_QUERY_URL = "https://export.arxiv.org/api/query?id_list={id}"
ATOM_NS = "{http://www.w3.org/2005/Atom}"
GITHUB_RE = re.compile(r"https?://github\.com/[^\s)\]}>\"']+")


def _normalize_id(arxiv_id_or_url: str) -> str:
    value = arxiv_id_or_url.strip()
    match = re.search(r"arxiv\.org/(?:abs|pdf)/([\w.\-]+?)(?:v\d+)?(?:\.pdf)?$", value)
    if match:
        return match.group(1)
    match = re.match(r"^([\w.\-]+?)(?:v\d+)?$", value)
    if match:
        return match.group(1)
    raise ValueError(f"Could not parse an arXiv id from: {arxiv_id_or_url!r}")


async def get_paper_brief(arxiv_id_or_url: str) -> dict:
    arxiv_id = _normalize_id(arxiv_id_or_url)

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(ARXIV_QUERY_URL.format(id=arxiv_id))
        resp.raise_for_status()

    root = ElementTree.fromstring(resp.text)
    entry = root.find(f"{ATOM_NS}entry")
    if entry is None:
        raise ValueError(f"No arXiv paper found for id: {arxiv_id}")

    title_el = entry.find(f"{ATOM_NS}title")
    summary_el = entry.find(f"{ATOM_NS}summary")
    title = (title_el.text or "").strip() if title_el is not None else None

    if title is None:
        raise ValueError(f"No arXiv paper found for id: {arxiv_id}")

    summary = (summary_el.text or "").strip() if summary_el is not None else None
    authors = [
        (author.find(f"{ATOM_NS}name").text or "").strip()
        for author in entry.findall(f"{ATOM_NS}author")
        if author.find(f"{ATOM_NS}name") is not None
    ]

    # arXiv's optional "comment" field lives in a separate <arxiv:...> namespace;
    # simplest reliable way to catch a code link there too is to search the raw
    # entry XML rather than tracking that namespace explicitly.
    entry_text = ElementTree.tostring(entry, encoding="unicode")
    code_match = GITHUB_RE.search(entry_text)

    return {
        "arxiv_id": arxiv_id,
        "title": title,
        "authors": authors,
        "abstract": summary,
        "url": f"https://arxiv.org/abs/{arxiv_id}",
        "code_url": code_match.group() if code_match else None,
    }
