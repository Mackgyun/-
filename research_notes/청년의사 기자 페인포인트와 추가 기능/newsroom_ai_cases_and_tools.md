# Newsroom AI and workflow-tool adoption cases, 2025–2026 (Korea and global), and what they mean for 청년의사's internal app

Scope note: about 20 searches and fetches. Sources are labelled. **[Vendor]** marks a company describing its own product or a press release, **[Self-report]** marks a news organisation describing its own tool (not independently verified), and **[Independent]** marks trade press or research coverage. Dates are publication dates.

Features the app already has, which this note treats as "covered": DART/ALIO disclosure collection and alerts; triage inbox with claim, dedupe and published URL; RAG Q&A with citations; style-matched drafts with a number cross-check; press-release mailbox digest with embargo detection; public-hospital year-over-year comparison; 4x daily digest; admin metrics.

---

## Q1. Which AI and automation features have major global newsrooms deployed in 2025–2026, and with what results?

### Takeaway
The deployments that held up and have numbers attached are back-office tools: summaries, transcription and monitoring digests, translation QA, earnings and disclosure automation, and internal "data-in-plain-language" agents. Most measured results are self-reported coverage or speed gains. The best-documented pattern for a small team is a monitoring tool that transcribes and summarises a fixed watchlist of sources and emails a daily digest (NYT Manosphere Report, Chalkbeat/LocalLens, Civic Sunlight). Reader-facing generative summaries produced the most public errors (Bloomberg, Washington Post).

### Cited Findings
**Reuters** [Self-report, CTO blog, dated 23 Jul 2026 on page]
- An AI summarisation skill produces bullet summaries of stories. Reuters says it now covers 94% of major stories, up from 33% — [Thomson Reuters blog](https://www.thomsonreuters.com/en-us/blog/the-tools-that-keep-reuters-journalists-and-its-customers-ahead-of-the-story/)
- CheckMATE, a generative-AI tool that improves machine translation, is used by more than 100 Reuters translators across 7 languages, Korean among them — [Thomson Reuters blog](https://www.thomsonreuters.com/en-us/blog/the-tools-that-keep-reuters-journalists-and-its-customers-ahead-of-the-story/)
- FactGenie suggests alerts and annotates text. LAMP uses an LLM to match images and video to stories. No metrics are given for either — [Thomson Reuters blog](https://www.thomsonreuters.com/en-us/blog/the-tools-that-keep-reuters-journalists-and-its-customers-ahead-of-the-story/)
- Super Summaries, an AI earnings product launched in July 2025, has added more than 3,600 companies to Reuters earnings coverage. Some breaking financial alerts go out in 6–8 seconds. Reuters says journalists must verify AI-generated claims — [Thomson Reuters blog](https://www.thomsonreuters.com/en-us/blog/the-tools-that-keep-reuters-journalists-and-its-customers-ahead-of-the-story/) (the 6–8 second figure comes from the search snippet of the same page)
- Reuters AI Suite, transcription and translation tuned for news, launched in April 2025 — [Thomson Reuters blog](https://www.thomsonreuters.com/en-us/blog/the-tools-that-keep-reuters-journalists-and-its-customers-ahead-of-the-story/)

**Associated Press**
- AP automates some corporate earnings stories from press releases, analyst reports and stock data — [IBM Think (secondary)](https://www.ibm.com/think/insights/ai-in-journalism)
- AP Local Lede, built with AppliedXL, watches more than 430 federal agencies, the Federal Register among them, for actions with local relevance in all 50 states. Each AI tip is checked against its source document before it is distributed in AP Newsroom. One account puts output at about 200 leads a week. Its status is unclear: one source says it is "in pilot" and quotes AP saying "it's possible that this won't live on" — [Editor & Publisher](https://editorandpublisher.com/stories/ap-appliedxl-to-deliver-ai-powered-news-tips-to-local-newsrooms,252035); [PR Newswire, Vendor, 2024](https://prnewswire.com/news-releases/appliedxl-ap-to-deliver-ai-powered-news-tips-to-local-newsrooms-302250798.html); [Newsmachines substack](https://newsmachines.substack.com/p/associated-press-ai-strategy)

**The New York Times** [Independent: Nieman Lab]
- The Manosphere Report watches about 80 podcasts that reporters chose. Each new episode is downloaded, transcribed and summarised by an LLM. Every 24 hours the summaries are rolled into a meta-summary of shared talking points and rhetoric shifts, emailed at 8 a.m. ET. Nearly 40 reporters use it. It gave an early signal on conservative media turning on the Epstein files story and on the Sydney Sweeney ad backlash. Reporters treat its output as leads, not sources — [Nieman Lab, 11 Feb 2026](https://www.niemanlab.org/2026/02/how-the-new-york-times-uses-a-custom-ai-tool-to-track-the-manosphere/)
- Cheatsheet is a spreadsheet tool where reporters upload a dataset and run preset prompt "recipes" to search, summarise, classify or translate it. In beta it had about 300 users (50 very active), with rollout to all Times journalists planned for Feb 2026. Uses include FOIA documents, Syrian prison records and tracking Trump remarks — [Nieman Lab, Feb 2026](https://www.niemanlab.org/2026/02/how-the-new-york-times-uses-a-custom-ai-tool-to-track-the-manosphere/); [Nieman Lab predictions piece by NYT's R. M. Fillion](https://www.niemanlab.org/2025/12/ai-turns-the-firehose-into-a-funnel/)
- A Charlie Kirk analysis transcribed about 2,500 podcasts and videos in 2 weeks. The comparable 2022 Tucker Carlson analysis took about a year — [Nieman Lab, Dec 2025](https://www.niemanlab.org/2025/12/ai-turns-the-firehose-into-a-funnel/)

**Nordic, European and other cases** (via the NYT-authored predictions piece and WAN-IFRA)
- iTromsø (Norway) built Djinn, which sifts municipal documents and archives and suggests story ideas. The 25-person newsroom produced "numerous stories" with it — [Nieman Lab, Dec 2025](https://www.niemanlab.org/2025/12/ai-turns-the-firehose-into-a-funnel/)
- Helsingin Sanomat built Watchdog, which scans public records and emails and flags potential stories to editors — [Nieman Lab, Dec 2025](https://www.niemanlab.org/2025/12/ai-turns-the-firehose-into-a-funnel/)
- CalMatters runs Digital Democracy, a portal of California bills, votes and lawmakers' fundraising — [Nieman Lab, Dec 2025](https://www.niemanlab.org/2025/12/ai-turns-the-firehose-into-a-funnel/)
- Schibsted [Self-report via WAN-IFRA, 17 Nov 2025]:
  - **ARIA** is a set of agents, one per dataset (subscriptions, brand data and so on), coordinated by an agent that compiles answers. Staff query it in Slack.
  - **Videofy** builds 20-second videos from articles inside the CMS, with editor review.
  - An **AI journalist toolbox**, proposed by a journalist, generates Q&A about articles and lets staff try Claude and GPT. Usage is tracked as a company KPI.
  - VG's personalised "since your last visit" module matches lead-story click-through and gets 85% thumbs-up.
  — [WAN-IFRA](https://wan-ifra.org/2025/11/how-schibsted-is-using-ai-to-boost-efficiency-for-their-newsrooms-and-their-readers/)
- Axel Springer: after an all-hands meeting, AI use became "an expectation" ("you only have to explain if you didn't"), per a July 2025 account — [secondary repost](https://www.goodreads.com/author_blog_posts/25924501-ceo-of-europe-s-largest-publisher-mandates-ai-use-in-newsrooms-you-onl) (low-quality host; treat as indicative)
- Nikkei built its own model ("Nikkei Tailor") behind Minutes by Nikkei, with a chatbot that suggests questions — [search summary of Reuters Institute item, Apr 2025; not fetched](https://reutersinstitute.politics.ox.ac.uk/ai-journalism-future-news)

**Local US public-meeting monitoring** [Independent: Nieman Lab, 13 Mar 2025]
- Chalkbeat built its own LLM tool to transcribe and summarise school-board meetings, with prompts tuned to pull out statistics and mentions of Chalkbeat. It was dropped by the end of 2024: it could not identify individual speakers, and every prompt change needed an engineer. Chalkbeat moved to the vendor LocalLens, which offers searchable transcripts, keyword search and custom alerts, and uses it for about 80 districts in 30 states across 8 bureaus. A reporter found a key student source through keyword search — [Nieman Lab](https://www.niemanlab.org/2025/03/local-newsrooms-are-using-ai-to-listen-in-on-public-meetings/)
- Civic Sunlight (used by the Midcoast Villager in Maine) works in steps: a rough transcript, a clean-up pass, automated checks on names and proper nouns, then an email roundup with timestamped links to recordings. The editor said it is "probably not as good as a junior reporter" but better than nothing. It struggles with accents — [Nieman Lab](https://www.niemanlab.org/2025/03/local-newsrooms-are-using-ai-to-listen-in-on-public-meetings/)

**Document analysis**
- Google Pinpoint is free for verified journalists through the Google News Initiative. It indexes and OCRs uploaded files and, since 2024, answers questions about documents with highlighted sources — [Google blog](https://blog.google/products-and-platforms/products/news/pinpoint-journalists-ai-features/); [GNI lesson](https://newsinitiative.withgoogle.com/resources/lessons/pinpoint-a-research-tool-for-journalists)
- One write-up says a 7-person newsroom (Blue Ridge Public Radio) used Pinpoint to track a developer's fraud across 3 cities and shared the collection with partner newsrooms. OCR is weak on poor scans and entity recognition misses unusual names — [mediacopilot.ai (single secondary blog, unverified)](https://mediacopilot.ai/google-pinpoint-small-newsroom-investigation/)

**Industry-level data** [Independent: Reuters Institute, Jan 2026, survey of about 280 news leaders]
- 97% of respondents call back-end automation important. The most-cited use case is transcription, copyediting and metadata (64%). Coding and product (44%), commercial uses (33%) and newsgathering (29%) are rising. Only 44% call their AI initiatives "promising"; 42% call them "limited" — [Reuters Institute Trends & Predictions 2026](https://reutersinstitute.politics.ox.ac.uk/journalism-media-and-technology-trends-and-predictions-2026); [PDF](https://reutersinstitute.politics.ox.ac.uk/sites/default/files/2026-01/Newman%20-%20Trends%20and%20Predictions%202026%20FINAL.pdf) (secondary sites word the 97% and 64% figures inconsistently; check the PDF before quoting)

### Inferences
- The global cases most transferable to a ~35-person trade paper are watchlist monitors that ingest, transcribe, summarise and send a daily digest. They reuse what the app already has (collector, LLM summarisation, digest, push), so the marginal cost is mostly new connectors.
- AP Local Lede (regulators → relevance-filtered tips, each checked against its source before distribution) is the closest analogue to "DART/ALIO for regulators." For 청년의사 the equivalent sources would be 보건복지부, 식약처, 심평원 and 건보공단 notices, 행정예고, 입법예고 and 국회 의안. None of these are yet in the app's listed sources.
- Cheatsheet's preset "recipes" (upload a spreadsheet or document set, run a saved prompt per row) is a cheap, general feature: batch classify or extract over an uploaded file. The Q&A over collected data does not cover ad-hoc uploads.
- Chalkbeat's experience argues for exposing prompt templates to reporters and editors rather than hard-coding them, and for speaker diarisation in any transcription feature.

### Gaps
- No independent measured results (time saved, error rates) for the Reuters, AP or Schibsted tools; all figures are self-reported.
- No 2025–2026 primary sources found for BBC, Guardian internal tools, Nikkei details, Dataminr or NewsWhip newsroom outcomes, or headline/SEO suggestion tools with measured CTR lift.
- AP Local Lede's 2025–2026 status could not be confirmed.

---

## Q2. What have Korean outlets deployed in 2025–2026?

### Takeaway
Korean adoption has become "AI inside the CMS" (titles, proofreading, summaries, press-release-to-article). The newer 2026 wave is reporter-built agents: 전자신문 ETA (keyword feeds, alerts, a fact-check agent and a timeline summary agent) and 서울경제 NOVA (300 reporters). Two outlets work directly on corporate disclosures (이투데이 governance AI, 한경 price data), and 연합뉴스 has an infographic generator plus template assistants for personnel, obituary and 동정 items. Reporter usage is about 60%, per a KPF survey.

### Cited Findings
- **전자신문 ETA** (operating from Jun 2026) is an internal AI news agent built by the paper's own reporters. It started at a vibe-coding hackathon (더존 × Replit) [Self-report]. Features:
  - Keyword-registered real-time news feeds
  - AI briefs that sort and summarise major issues
  - Breaking-news and exclusive alerts
  - Foreign-press collection and tracking of selected outlets
  - A **fact-check agent**: give it an article URL and it compares the article with related reports to assess reliability
  - A **summary agent** that lays out one issue's articles chronologically
  - A writing agent that drafts headline, lead and body from notes
  No usage metrics are given — [전자신문, 2026-06-19/21](https://www.etnews.com/20260619000241)
- **서울경제 AI NOVA** covers item discovery, drafting, editing and proofreading, and title and graphic generation. About 300 reporters use it, and since June it has been sold externally. An editor said "no reporter has used NOVA only once." It prepares in advance the questions a desk chief will ask in the daily report, and auto-converts articles to video — [기자협회보, 2026-07-09](https://www.journalist.or.kr/news/article.html?no=61238)
- **연합뉴스** — [기자협회보, 2026-07-09](https://www.journalist.or.kr/news/article.html?no=61238):
  - An infographic service (Mar 2026) turns sentences, tables, captures or press-release files into chart infographics.
  - An AI assistant for **인사, 부고 and 동정** items turns source material into wire-format copy.
  - A Q&A service over decades of articles, 연합연감 and reporting information was planned for autumn 2026.
  - A real-time STT service transcribes press conferences in almost every language where correspondents are posted and saves the results internally.
- **이투데이** built a real-time AI governance-analysis service on the disclosure API: ownership and governance changes now, financial structure later. Development started in Jul 2025 with launch targeted for Oct–Nov 2025. It is offered to reporters in the CMS and to investors via a dashboard — [기자협회보, 2025-06-26](https://www.journalist.or.kr/news/article.html?no=58812)
- **한경닷컴** has a price-data platform that auto-collects data from sources such as 소비자원 and KOSIS for AI-written price articles and visualisations — [기자협회보, 2025-06-26](https://www.journalist.or.kr/news/article.html?no=58812)
- **아주경제** has an AI CMS (title suggestions, summaries, proofreading, keyword extraction, length adjustment, translation into 5 languages). About 70% of reporters use it — [기자협회보, 2025-06-26](https://www.journalist.or.kr/news/article.html?no=58812)
- **미디어오늘** is automating its "아침신문 솎아보기" column, a morning newspaper roundup previously compiled manually by rotating reporters. **동아일보** is building auto-tagging for its video archive. **경인일보** planned an AI briefing and conversational search over its own regional archive ("K-인사이트") for Oct 2025 — [기자협회보, 2025-06-26](https://www.journalist.or.kr/news/article.html?no=58812)
- **세계일보** reporters built an in-house tool that turns an article URL into card news and shorts. **매일경제** produces AI audio and podcast-style briefings. **MBC** spun off a subsidiary (도스트11) to sell its AI media tools. TTS radio news runs at MBC and MBN — [기자협회보, 2026-07-09](https://www.journalist.or.kr/news/article.html?no=61238)
- **조선일보** launched a press-release-to-article AI (미디어DX, trained on 50k articles) in Dec 2023. Under a 2025 Upstage partnership it set a schedule: proofreading AI (Feb), translation (May), search (Jul), fact-check (Sep), then article generation. AI-assisted articles carry a disclosure line, are limited to online news, and junior and trainee reporters are restricted from using the tool — [미디어오늘](https://www.mediatoday.co.kr/news/articleView.html?idxno=324253) (the schedule was announced as planned; delivery was not verified)
- **중앙일보** runs press-release article writing, search and summaries on Google Cloud AI — [미디어오늘](https://www.mediatoday.co.kr/news/articleView.html?idxno=314854)
- All 15 projects selected for KPF's 2025 digital media service development support programme were AI-related — [기자협회보, 2025-06-26](https://www.journalist.or.kr/news/article.html?no=58812)
- In KPF's "2025 한국의 언론인" survey (n=2,020), about 60% use AI, routinely for data analysis and classification, translation and proofreading. About 40% feel AI threatens their job security — [기자협회보, 2026-07-09](https://www.journalist.or.kr/news/article.html?no=61238)
- A seminar framing: 출입처 monitoring, collecting and classifying material, and transcription, translation and summarisation can largely go to AI, while choosing what to cover and final publication stay with people — [반론보도닷컴 seminar report](https://www.banronbodo.com/news/articleView.html?idxno=33144)

### Inferences
- ETA overlaps strongly with what the app has (feeds, alerts, digests, drafts). Its two features the app lacks are (a) a **fact-check/compare agent**: paste a URL or draft and get it compared against related coverage and own archive, with contradictions flagged; and (b) an **issue timeline agent** that lays out all articles and disclosures on one topic chronologically. Both can be built on the existing RAG store.
- 연합뉴스's **template assistants for 인사, 부고 and 동정** suit a medical trade paper well: hospital appointments, society officer elections and award notices are frequent, formulaic and press-release-driven.
- 서울경제's "pre-answer the desk chief's questions" is a cheap add-on to the existing story claim and draft flow: it generates the likely editor questions and source gaps for a pitch.
- 연합뉴스's infographic generator suggests a "table or press-release file → chart" feature. A small team could do this with a charting library plus an LLM-produced chart spec.

### Gaps
- No 2025–2026 primary sources found on specific AI tools at 한겨레, KBS or SBS beyond the general mentions above. 매일경제 is covered only by the audio item and an older Papago translation item.
- No measured outcomes (time saved, error rates) for any Korean tool.
- No Korean medical or health trade-press AI case was found (for example 메디게이트, 데일리메디, 의협신문).

---

## Q3. Which Korean-language tools do reporters use (transcription, BIG KINDS, KPF tools)?

### Takeaway
Transcription is commoditised. Reporters already use 클로바노트 and 다글로 on their own, but accuracy is uneven and the data sits outside the newsroom. BIG KINDS was relaunched in March 2025 as a free generative-AI platform with daily issue summaries, outlet-selectable answers, HWP/PDF analysis and multi-turn chat. It is both a competitor to and a possible data source for the app's Q&A.

### Cited Findings
- **BIG KINDS AI relaunch** (24 Mar 2025, announced 7 Apr 2025):
  - "오늘의 이슈" sorts about 10,000 articles a day from 104 outlets by section and has AI summarise the key issues.
  - Answers can be restricted to outlets the user picks, for comparing viewpoints.
  - **HWP and PDF upload** lets users analyse a document and chat about it.
  - Multi-turn chat.
  - The base service is free, over 100M+ articles, with emailed alerts on topics of interest.
  — [전자신문](https://www.etnews.com/20250407000046); [미디어스](https://www.mediaus.co.kr/news/articleView.html?idxno=312501); [한국언론인협회](https://akj.or.kr/article/?cate=22&id=2720)
- 서울경제's AI Prism recommender is expanding to issue-based recommendations through a BIG KINDS integration — [기자협회보, 2025-06-26](https://www.journalist.or.kr/news/article.html?no=58812)
- **클로바노트 and 다글로** — [이데일리, 2024-08 (older, still relevant)](https://m.edaily.co.kr/News/Read?newsId=01279206638983712&mediaCodeNo=257):
  - Reporters rely on them on crowded assignments, but still have to reconstruct context and compare with colleagues' notes.
  - A hands-on test found similar spelling errors in both, with 다글로 better at recognising words.
  - 다글로 also transcribes video files and YouTube links.
- Free tiers as of Aug 2026: 클로바노트 personal gets an extra 300 min a month with data-improvement consent, 180 min per file, and no extra-time purchase. 다글로 free gets 1,000 credits a month, with about 4h of recording and 4h of file/YouTube — [시그널필드 (secondary)](https://signalfield.media/articles/ai-meeting-notes-clova-daglo-notta-comparison-f99d5121)
- Naver was preparing an enterprise 클로바노트 with company-email login, 2-factor authentication and device control. This points to a security gap in the personal accounts — [이데일리](https://m.edaily.co.kr/News/Read?newsId=01279206638983712&mediaCodeNo=257)
- 기자협회보 has a reporters' app roundup, including 다글로 for recordings and YouTube links (older) — [기자협회보](http://journalist.or.kr/m/m_article.html?no=47842)

### Inferences
- The gap is not transcription itself. It is that transcripts never reach the newsroom's searchable store. One feature would cover it: upload an audio file or paste a 클로바/다글로 transcript, then get a summary, quotes with timestamps, the numbers mentioned, and the result indexed into the RAG archive. The draft feature could then cite interview quotes and the number cross-check could cover spoken figures. Whisper or a Gemini/OpenAI audio API makes this cheap; Korean medical vocabulary needs a custom glossary.
- An HWP/PDF "upload and ask" feature is now baseline (BIG KINDS has it). Government health documents are often HWP, so HWP text extraction is a concrete requirement.
- BIG KINDS has no public API confirmed in these sources. Its daily-issue summary could be linked to rather than rebuilt.

### Gaps
- No source found on 리턴제로 (VITO) newsroom adoption, 팩트체크넷 tooling in 2025–2026, or other KPF AI tools beyond BIG KINDS.
- No independent Korean medical-terminology accuracy comparison of STT tools.
- Whether BIG KINDS offers API access for AI features was not checked.

---

## Q4. What tools exist for tracking regulatory and legislative events and for topic or entity watchlists?

### Takeaway
US legislative trackers (Politico Pro, Quorum, FiscalNote) have converged on AI bill summaries plus AI triage that tags priority, issue and stance, because "teams don't need more alerts." The newsroom equivalents are AP Local Lede (regulator feed → relevance-filtered tips), CalMatters Digital Democracy, and the NYT, Helsingin Sanomat and iTromsø watchlist monitors. Nothing comparable to these was found for Korean health regulation.

### Cited Findings
- **Politico Pro**: Legislative and Regulatory Compasses and Dialogue Tracking are automated trackers covering 25+ years of federal data and up to 10 years for all 50 states. It offers AI-generated bill summaries — [Politico Pro Legislative Compass fact sheet, Vendor](https://www.Politicopro.Com/fact-sheet/legislative-compass.pdf); [Politico Pro AI bill summaries, Vendor](https://politicopro.com/pro-features/ai-generated-bill-summaries/)
- **Quorum**'s Bill Tracker Agent reviews every bill and suggests stance, priority and issue area, and whether to watch it. Its product lead says "Teams don't need more alerts." Announced 27 Jul 2026 — [Quorum, Vendor](https://www.quorum.us/company-news/quorum-launches-bill-tracker-agent-to-help-government-affairs-teams-act-faster-on-legislation/); [Quorum blog, Vendor](https://www.quorum.us/blog/introducing-the-bill-tracker-agent-automate-policy-triage-and-risk-analysis/)
- **FiscalNote PolicyNote** is a policy monitoring platform built on CQ legislative data — [FiscalNote, Vendor](https://fiscalnote.com/blog/best-legislative-tracking-software). Quorum's competitor page calls PolicyNote AI a Q&A research assistant — [Quorum, Vendor/competitor](https://www.quorum.us/about/fiscalnote-alternative/)
- **AP Local Lede**: 430+ federal agencies, with source validation before distribution (see Q1) — [Editor & Publisher](https://editorandpublisher.com/stories/ap-appliedxl-to-deliver-ai-powered-news-tips-to-local-newsrooms,252035)
- **CalMatters Digital Democracy**: bills, votes and fundraising per lawmaker — [Nieman Lab, Dec 2025](https://www.niemanlab.org/2025/12/ai-turns-the-firehose-into-a-funnel/)
- **LocalLens** offers keyword search and custom alerts on meeting transcripts — [Nieman Lab, Mar 2025](https://www.niemanlab.org/2025/03/local-newsrooms-are-using-ai-to-listen-in-on-public-meetings/)
- **전자신문 ETA** offers keyword-registered feeds and tracking of selected outlets — [전자신문](https://www.etnews.com/20260619000241)

### Inferences
- The highest-value gap for 청년의사 is a health-policy tracker that applies the app's red/yellow/gray scoring and push alerts to sources beyond DART and ALIO:
  - 국회 의안정보시스템 bills: 보건복지위원회, plus status changes such as committee referral, 소위 and 본회의
  - 입법예고 and 행정예고 (복지부, 식약처)
  - 심평원 and 건보공단 notices: 급여기준 changes and 고시
  - 식약처 approvals and safety letters
  - 건정심 agendas
  Quorum's lesson applies: prioritise the AI triage tags (priority, issue, stance toward doctors, hospitals and pharma) over raw alert volume. The specific sources are from domain knowledge and were not researched here, so feed and API availability needs checking.
- **Entity watchlists**: per-reporter keyword, company, hospital or lawmaker subscriptions across all collected sources (ETA-style). The app's alerts appear to be classification-driven rather than per-reporter watchlists; worth confirming.
- **"Status change" alerts** (a bill moves stage, a disclosure is amended) are a distinct, cheap feature: diff the previous state.

### Gaps
- No independent reviews comparing Politico Pro, Quorum and FiscalNote. All capability claims are vendor-sourced.
- Korean legislative or regulatory tracker products (any 국회 의안 alert services used by newsrooms) were not researched.

---

## Q5. Which collaboration workflow tools do newsrooms use (story budgets, assignments, Slack, editorial and embargo calendars)?

### Takeaway
Dedicated planning tools (Kordiam, Superdesk Planning) centre on one shared story budget with assignments, deadlines and Slack or chat notifications. Small newsrooms often get by with Slack plus a shared doc or Coda. The app's claim and published-URL features already do part of this. What it lacks is a forward-looking calendar (embargo lifts, scheduled events, deadlines) and assignment and status changes pushed into chat.

### Cited Findings
- **Kordiam** is a cloud editorial calendar and story budget. It sends assignments and updates to Slack, links each story entry to its Slack conversation, and syncs its calendar view with Slack. It has no native CMS publishing. Pricing is cited from $263/month — [Kordiam Slack integration, Vendor](https://kordiam.io/slack-editorial-calendar-integration); [Kordiam integrations, Vendor](https://kordiam.io/integrations) (pricing figure from a search summary of a listing; not independently verified)
- **Superdesk Planning** (open source, aimed at larger organisations) handles event and coverage planning, with alerts routed through messaging tools such as Slack — [Superdesk, Vendor](https://www.superdesk.org/publishing/planning-component)
- **Coda** can combine story budget and editorial calendar in one tracker, connected to Slack (2019, older) — [Poynter, 2019](https://www.poynter.org/tech-tools/2019/coda-is-an-all-in-one-document-tool-that-could-fix-your-story-budget-and-editorial-planning-woes/)
- Better News (API) recommends a single budget everyone can access, including through coordination tools like Slack — [Better News](https://betternews.org/provide-tools-support-better-workflows-broader-roles/)
- Schibsted runs its ARIA data agents inside Slack, so staff ask questions where they already work — [WAN-IFRA, Nov 2025](https://wan-ifra.org/2025/11/how-schibsted-is-using-ai-to-boost-efficiency-for-their-newsrooms-and-their-readers/)
- 서울경제 NOVA prepares the questions a desk chief will ask in the daily report — [기자협회보, 2026-07-09](https://www.journalist.or.kr/news/article.html?no=61238)

### Inferences
- Candidate additions:
  - (a) A **forward calendar** combining embargo lifts (already detected in the mailbox digest), scheduled events (국회 committee meetings, 건정심, 학회 conferences, earnings and disclosure deadlines) and story deadlines, with a reminder push before each.
  - (b) A **daily budget view** for desk chiefs: claimed stories, status, expected publish time, gaps by beat.
  - (c) **Chat integration**: push claims and assignments to KakaoWork or Slack, or whatever messenger 청년의사 uses (unknown).
- Off-the-shelf Kordiam-class tools cost hundreds of USD a month and do not integrate with the app's data. Building a light budget and calendar on the existing claim data is the more feasible path.

### Gaps
- No 2025–2026 independent case study of a small newsroom's planning-board adoption with measured results.
- No Korean newsroom planning-tool cases found. Korean outlets largely embed planning in the CMS, but this is unverified.

---

## Q6. What are the lessons and risks (hallucination incidents, guidelines, disclosure, copyright)?

### Takeaway
The documented failures are all in **unreviewed, reader-facing generated text**: Bloomberg summaries, the Washington Post AI podcasts, a syndicated fake book list, and a regional Korean broadcaster's AI-news overreach. Korea's main framework is KPF's Feb 2025 "언론을 위한 생성형 AI 준칙." It allows AI for research, transcription, translation and data analysis, discourages fully AI-generated articles, and requires disclosure, correction and a named responsible person. This supports building AI features as reporter-assist with logging and verification, which the app already leans toward with citations and number cross-check.

### Cited Findings
- **Bloomberg** began AI bullet summaries on articles in Jan 2025. By late March at least 36 had needed corrections, for example getting the year of Canada tariffs wrong. Bloomberg said 99% meet its editorial standards — [Talking Biz News (on NYT report)](https://talkingbiznews.com/media-news/bloomberg-has-a-rocky-start-with-ai-summaries/); [Washington Times, 29 Mar 2025](https://m.washingtontimes.com/news/2025/mar/29/bloombergs-use-ai-summaries-articles-leads-numerous-corrections/)
- **Washington Post** AI podcasts: Semafor reported that 68%–84% of AI-generated scripts failed the Post's internal testing, yet the feature launched as "beta" — [Semafor, 14 Dec 2025](https://www.semafor.com/article/12/14/2025/iterate-through-why-the-washington-post-launched-an-error-ridden-ai-product); [Futurism](https://futurism.com/artificial-intelligence/washington-post-continue-ai-podcasts)
- The **LA Times** removed an erroneous AI-generated description related to the KKK (2025) — [Talking Biz News](https://talkingbiznews.com/media-news/bloomberg-has-a-rocky-start-with-ai-summaries/)
- **Chicago Sun-Times** (18 May 2025): a syndicated summer reading list had 10 of 15 books invented. A freelancer used AI without fact-checking it. The paper apologised and updated its policies — [CBS Chicago](https://www.cbsnews.com/chicago/news/summer-reading-ai-generated-titles-chicago-sun-times/); [Snopes](https://www.snopes.com/fact-check/chicago-sun-times-ai-reading-list/)
- **G1 (Korea)**: during the Apr 2025 Inje wildfire, the duty reporter focused on producing AI news and the outlet ran only brief items, drawing internal criticism. Management and union then wrote an "AI 뉴스 대응 매뉴얼" — [기자협회보, 2026-07-09](https://www.journalist.or.kr/news/article.html?no=61238)
- **KPF 언론을 위한 생성형 AI 준칙** (posted 2025-02-04; 10 articles, 36 items) — [KPF booklet](https://www.kpf.or.kr/front/board/boardContentsView.do?board_id=2&contents_id=47ab30f7ef52499595ecb29101de2606); [기자협회보](http://www.journalist.or.kr/news/article.html?no=57255):
  - Assistive uses (research, transcription, translation, data analysis) are broadly allowed. Fully AI-generated articles or video are "not desirable."
  - AI use must be disclosed (notice text, watermark, audio notice), as must direct use of AI output.
  - Errors must be corrected immediately and marked.
  - Each outlet should designate a person responsible for its AI policy.
- 조선일보 adds an AI-assistance disclosure line, limits AI articles to online, and restricts junior reporters' use — [미디어오늘](https://www.mediatoday.co.kr/news/articleView.html?idxno=324253)
- 한국일보 was cited as the first Korean outlet with generative-AI guidelines (Apr 2024) — [기자협회보, 2025-06-26](https://www.journalist.or.kr/news/article.html?no=58812)
- Newsrooms using meeting-summary AI (Chalkbeat, Midcoast Villager) treat output as a "tip" that must be independently verified — [Nieman Lab, Mar 2025](https://www.niemanlab.org/2025/03/local-newsrooms-are-using-ai-to-listen-in-on-public-meetings/)
- Copyright and licensing context: Press Gazette tracks publisher AI deals and lawsuits, for example US papers suing Brave and Canadian publishers suing Anthropic — [Press Gazette tracker](https://pressgazette.co.uk/platforms/news-publisher-ai-deals-lawsuits-openai-google/). Schibsted reinvests revenue from its OpenAI deal into internal AI — [WAN-IFRA](https://wan-ifra.org/2025/11/how-schibsted-is-using-ai-to-boost-efficiency-for-their-newsrooms-and-their-readers/)

### Inferences
- Features that operationalise the KPF 준칙 cheaply and are not yet in the app:
  - (a) An **AI-use log per article** (which tool, which prompt or draft, who reviewed), to support disclosure and correction duties.
  - (b) An automatic **disclosure-line suggestion** when an AI draft is used substantially.
  - (c) A **pre-publication verification checklist**: named entities, titles and affiliations, dates, and quotes checked against transcripts and sources. This extends the existing number cross-check to names, dates and quotes, the error types behind the Bloomberg and Sun-Times cases.
  - (d) A **corrections tracker** tied to the published-URL record.
- The G1 case argues against features that pull reporters into producing AI copy during breaking news. Keep AI as triage and assist.

### Gaps
- No Korean hallucination or correction incident in print or online news (as opposed to broadcast) was found for 2025–2026.
- No 한국신문협회-specific AI guideline was found; KPF's 준칙 is the main reference. Korean copyright litigation status (for example newspapers vs. Naver or AI firms) was not researched.

---

### Cross-cutting feasibility summary (inference, for the report writer)
Candidate features not yet in the app, with evidence and rough feasibility for a 30–40 person team on one PC using LLM APIs:

| # | Feature | Evidence | Feasibility |
|---|---|---|---|
| 1 | Health-policy/regulator tracker (국회 의안, 입법/행정예고, 심평원/건보/식약처) with AI triage and status-change alerts | AP Local Lede; Quorum; Helsingin Sanomat Watchdog; CalMatters | Medium: depends on feed and scrape availability, reuses existing pipeline |
| 2 | Per-reporter entity/keyword watchlists across all sources | 전자신문 ETA; LocalLens alerts | Low effort |
| 3 | Interview/audio transcript ingestion: summary, quotes, numbers, indexed for RAG and drafts | NYT Manosphere/Cheatsheet; 연합 STT; Reuters AI Suite; 64% top use case | Low–medium: STT API cost per hour; needs a medical glossary and diarisation |
| 4 | Fact-check/compare agent for a draft or URL vs. archive and coverage, extending checks to names, dates and quotes | 전자신문 ETA; 조선 fact-check plan; Bloomberg/Sun-Times failure modes | Medium |
| 5 | Issue timeline agent (all articles and disclosures on one topic, chronological) | 전자신문 ETA summary agent | Low |
| 6 | Template assistants for 인사, 부고, 동정 and award items | 연합뉴스 | Low |
| 7 | Batch "recipes" over an uploaded spreadsheet or document set; HWP/PDF upload-and-ask | NYT Cheatsheet; BIG KINDS file analysis; Google Pinpoint | Low–medium (HWP parsing) |
| 8 | Forward calendar (embargo lifts, events, deadlines) and daily budget view with messenger push | Kordiam/Superdesk; Better News | Low–medium |
| 9 | Table or press release → chart/infographic | 연합뉴스 infographic service | Medium |
| 10 | AI-use log, disclosure line and corrections tracker | KPF 준칙; 조선 disclosure practice | Low |
| 11 | Editor-question pre-brief for pitches | 서울경제 NOVA | Low |
