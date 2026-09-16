import re

import httpx

from ..config import settings

CODE_BLOCK_RE = re.compile(r"```[a-zA-Z0-9_+-]*\n(.*?)```", re.DOTALL)
HEADING_RE = re.compile(
    r"^#{1,6}\s*.*?(install|usage|quick ?start|getting started).*$",
    re.IGNORECASE | re.MULTILINE,
)


def _extract_quickstart(readme_text: str) -> str | None:
    heading_match = HEADING_RE.search(readme_text)
    if heading_match:
        rest = readme_text[heading_match.end():]
        code_match = CODE_BLOCK_RE.search(rest)
        if code_match:
            return code_match.group(1).strip()

    code_match = CODE_BLOCK_RE.search(readme_text)
    if code_match:
        return code_match.group(1).strip()

    return None


def _parse_repo(repo: str) -> str:
    repo = repo.strip()
    match = re.search(r"github\.com/([^/\s]+/[^/\s#?]+)", repo)
    if match:
        return match.group(1).removesuffix(".git")
    return repo


async def get_repo_quickstart(repo: str) -> dict:
    owner_repo = _parse_repo(repo)
    if "/" not in owner_repo:
        raise ValueError(f"Invalid repo identifier: {repo!r} (expected 'owner/repo')")

    headers = {"Accept": "application/vnd.github+json"}
    if settings.github_token:
        headers["Authorization"] = f"Bearer {settings.github_token}"

    async with httpx.AsyncClient(timeout=10.0, headers=headers) as client:
        meta_resp = await client.get(f"https://api.github.com/repos/{owner_repo}")
        if meta_resp.status_code == 404:
            raise ValueError(f"Repo not found: {owner_repo}")
        meta_resp.raise_for_status()
        meta = meta_resp.json()

        readme_resp = await client.get(
            f"https://api.github.com/repos/{owner_repo}/readme",
            headers={**headers, "Accept": "application/vnd.github.raw+json"},
        )
        readme_text = readme_resp.text if readme_resp.status_code == 200 else ""

    return {
        "repo": owner_repo,
        "description": meta.get("description"),
        "stars": meta.get("stargazers_count"),
        "language": meta.get("language"),
        "topics": meta.get("topics", []),
        "url": meta.get("html_url"),
        "quickstart": _extract_quickstart(readme_text) if readme_text else None,
    }
