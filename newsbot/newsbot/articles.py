"""청년의사(docdocdoc.co.kr) 자사 기사 수집과 검색.

- 기자 본인 기사만 모아 스타일북을 만들고, 초안 쓸 때 비슷한 과거 기사를 찾는다.
- 사내 분석용이며, 요청 사이에 2초씩 쉰다. 회사가 ND소프트에서 DB를 받으면 이 수집은 대체한다.
- 페이지 구조가 바뀌어도 버티도록 JSON-LD → og 메타 → 본문 영역 순으로 읽는다.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from .db import Database, now_iso

log = logging.getLogger(__name__)
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ChungnyunBriefing/0.2 (internal)"}
IDX = re.compile(r"articleView\.html\?idxno=(\d+)")
EMAIL = re.compile(r"([A-Za-z0-9._-]+)@docdocdoc\.co\.kr")
DATE = re.compile(r"(20\d{2})[.\-](\d{2})[.\-](\d{2})\s+(\d{2}):(\d{2})")
BODY_SELECTORS = ["#article-view-content-div", "[itemprop=articleBody]", "article.article-veiw-body",
                  "article.article-view-body", "#articleBody", "article"]


@dataclass
class Article:
    idxno: int
    title: str
    author: str
    author_id: str
    section: str
    published_at: str
    body: str
    url: str


def parse_list(html: str) -> list[int]:
    seen, out = set(), []
    for m in IDX.finditer(html):
        n = int(m.group(1))
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out


def _jsonld(soup: BeautifulSoup) -> dict:
    for s in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(s.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        for d in data if isinstance(data, list) else [data]:
            if isinstance(d, dict) and "Article" in str(d.get("@type", "")):
                return d
    return {}


def _meta(soup: BeautifulSoup, *names: str) -> str:
    for n in names:
        tag = soup.find("meta", attrs={"property": n}) or soup.find("meta", attrs={"name": n})
        if tag and tag.get("content"):
            return tag["content"].strip()
    return ""


def parse_article(html: str, idxno: int, url: str) -> Article | None:
    soup = BeautifulSoup(html, "html.parser")
    ld = _jsonld(soup)
    title = (ld.get("headline") or _meta(soup, "og:title") or (soup.title.string if soup.title else "") or "").strip()
    title = re.sub(r"\s*[-|]\s*청년의사.*$", "", title)

    body_el = None
    for sel in BODY_SELECTORS:
        body_el = soup.select_one(sel)
        if body_el:
            break
    if body_el:
        for junk in body_el.select("script, style, figure, .ad, .ads, iframe"):
            junk.decompose()
        body = "\n".join(p.get_text(" ", strip=True) for p in body_el.find_all(["p", "div"]) if p.get_text(strip=True))
        if not body:
            body = body_el.get_text("\n", strip=True)
    else:
        body = ld.get("articleBody") or ""
    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    if not title or len(body) < 100:
        return None

    text = soup.get_text(" ", strip=True)
    email = EMAIL.search(body[-400:]) or EMAIL.search(text)
    author = ""
    a = ld.get("author")
    if isinstance(a, dict):
        author = a.get("name", "")
    elif isinstance(a, list) and a and isinstance(a[0], dict):
        author = a[0].get("name", "")
    if not author:
        m = re.search(r"([가-힣]{2,4})\s*기자", text)
        author = m.group(1) if m else ""
    published = ld.get("datePublished") or _meta(soup, "article:published_time")
    if not published:
        m = DATE.search(text)
        published = f"{m.group(1)}-{m.group(2)}-{m.group(3)}T{m.group(4)}:{m.group(5)}:00+09:00" if m else ""
    section = _meta(soup, "article:section") or ""
    return Article(idxno, title, author.replace("기자", "").strip(), email.group(1).lower() if email else "",
                   section, published, body, url)


class ArticleCollector:
    def __init__(self, db: Database, base: str, http: httpx.AsyncClient | None = None, delay: float = 2.0):
        self.db = db
        self.base = base
        self.http = http or httpx.AsyncClient(headers=HEADERS, timeout=30, follow_redirects=True)
        self.delay = delay

    async def _get(self, url: str) -> str:
        await asyncio.sleep(self.delay)
        r = await self.http.get(url)
        r.raise_for_status()
        return r.text

    async def collect_reporter(self, reporter_id: str, max_pages: int = 20, progress=None) -> dict:
        """기자 ID(이메일 앞부분)의 기사를 모은다. 목록 필터가 안 먹어도 본문의 이메일로 다시 거른다."""
        reporter_id = reporter_id.strip().lower()
        added = checked = 0
        for page in range(1, max_pages + 1):
            list_url = (f"{self.base}/news/articleList.html?sc_area=I&sc_word={reporter_id}"
                        f"&view_type=sm&page={page}")
            ids = parse_list(await self._get(list_url))
            new_ids = [i for i in ids if not self.db.one("SELECT 1 FROM articles WHERE idxno=?", (i,))]
            if not ids:
                break
            for idxno in new_ids:
                url = urljoin(self.base, f"/news/articleView.html?idxno={idxno}")
                checked += 1
                try:
                    art = parse_article(await self._get(url), idxno, url)
                except httpx.HTTPError as e:
                    self.db.log("error", f"article {idxno}: {e!r}")
                    continue
                if art and art.author_id == reporter_id:
                    self.save(art)
                    added += 1
                if progress:
                    progress(page, added, checked)
            if not new_ids:
                break  # 이미 모은 구간에 도달
        return {"added": added, "checked": checked}

    def save(self, a: Article) -> None:
        with self.db.tx() as c:
            c.execute("""INSERT OR REPLACE INTO articles(idxno, title, author, author_id, section, published_at,
                         body, url, fetched_at) VALUES(?,?,?,?,?,?,?,?,?)""",
                      (a.idxno, a.title, a.author, a.author_id, a.section, a.published_at, a.body, a.url, now_iso()))
            c.execute("DELETE FROM articles_fts WHERE rowid=?", (a.idxno,))
            c.execute("INSERT INTO articles_fts(rowid, title, body) VALUES(?,?,?)", (a.idxno, a.title, a.body))


def _fts_query(text: str) -> str:
    """검색어에서 3글자 이상 덩어리를 뽑아 OR 검색어로 만든다 (trigram 색인)."""
    words = re.findall(r"[가-힣A-Za-z0-9]{3,}", text)
    uniq = []
    for w in words:
        if w not in uniq:
            uniq.append(w)
    return " OR ".join(f'"{w}"' for w in uniq[:12])


def search_articles(db: Database, text: str, author_id: str | None = None, limit: int = 5) -> list[dict]:
    q = _fts_query(text)
    if not q:
        return []
    sql = """SELECT a.idxno, a.title, a.author, a.published_at, a.url, substr(a.body, 1, 1500) AS body
             FROM articles_fts f JOIN articles a ON a.idxno = f.rowid
             WHERE articles_fts MATCH ?"""
    params: list = [q]
    if author_id:
        sql += " AND a.author_id = ?"
        params.append(author_id)
    sql += " ORDER BY bm25(articles_fts) LIMIT ?"
    params.append(limit)
    try:
        return db.query(sql, tuple(params))
    except Exception:  # noqa: BLE001 - FTS 문법 오류 시 빈 결과
        log.exception("fts search failed")
        return []
