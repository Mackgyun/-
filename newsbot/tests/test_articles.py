from newsbot.articles import ArticleCollector, Article, parse_article, parse_list, search_articles
from newsbot.db import Database

ARTICLE = """<html><head><title>복지부, 필수의료 수가 인상 - 청년의사</title>
<meta property="og:title" content="복지부, 필수의료 수가 인상 추진">
<meta property="article:published_time" content="2026-11-05T13:30:00+09:00"></head>
<body><h3 class="heading">복지부, 필수의료 수가 인상 추진</h3>
<article id="article-view-content-div" itemprop="articleBody">
<p>보건복지부가 필수의료 분야 수가를 내년부터 15% 인상한다고 5일 밝혔다.</p>
<p>복지부 관계자는 "의료 현장의 인력난을 해소하기 위한 조치"라고 말했다. 인상 대상은 소아청소년과와 산부인과 등이다.</p>
<p>송수연 기자 soo331@docdocdoc.co.kr</p></article></body></html>"""


def test_parse_list():
    html = '<a href="/news/articleView.html?idxno=300">a</a><a href="/news/articleView.html?idxno=300">b</a>' \
           '<a href="/news/articleView.html?idxno=299">c</a>'
    assert parse_list(html) == [300, 299]


def test_parse_article():
    a = parse_article(ARTICLE, 300, "https://x/300")
    assert a.title == "복지부, 필수의료 수가 인상 추진"
    assert a.author_id == "soo331" and a.author == "송수연"
    assert a.published_at.startswith("2026-11-05T13:30")
    assert "15% 인상" in a.body


def test_search_fts():
    db = Database(":memory:")
    col = ArticleCollector(db, "https://x", delay=0)
    col.save(parse_article(ARTICLE, 300, "https://x/300"))
    col.save(Article(301, "제약사 기술이전 계약", "김기자", "kim", "", "", "한미약품이 기술이전 계약을 맺었다. " * 5, "https://x/301"))
    hits = search_articles(db, "필수의료 수가 인상 발표")
    assert hits and hits[0]["idxno"] == 300
    assert search_articles(db, "기술이전 계약", author_id="soo331") == []
    assert search_articles(db, "기술이전 계약", author_id="kim")[0]["idxno"] == 301
