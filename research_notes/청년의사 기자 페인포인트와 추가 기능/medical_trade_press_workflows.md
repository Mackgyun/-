# How medical, pharma and biotech trade journalists work (Korea and abroad): pain points and newsroom product features

Research date: 2026-11-15. About 21 search and fetch calls. Many Korean sources are older than 2023 and are marked with their year. Search snippets were checked against the source page where possible (WebFetch was used for mediatoday 319042 and the STAT+ page). Everything else rests on search-result summaries and should be re-checked before anyone quotes it.

---

## 1. The Korean 의료전문지 landscape: competitors, business models, data products, structural pain points

### Takeaway
Korean medical trade outlets sit inside a regulatory niche. The 약사법 allows prescription-drug (ETC) advertising only in medical or pharma professional media and journals. This makes pharma advertising the structural revenue base and creates a standing tension with editorial independence. On the data-product side, the clearest paid model I found is 바이오스펙테이터's high-priced BioS+ premium subscription. 데일리팜 and 히트뉴스 build regular data-driven coverage on licensed prescription data (UBIST, IQVIA) rather than selling their own DB, as far as I could find.

### Cited Findings
- **Legal basis of the ad model.** Under 약사법 제68조 제6항, prescription drugs (except vaccines) may be advertised only in 의약전문매체 or journals aimed at medical and pharma professionals. Even a pharma company's own website describing its ETC products is illegal. A 2024 기자수첩 argues this limits access to information. — [머니투데이, 2024-01-18](https://www.mt.co.kr/opinion/2024/01/18/2024011709494288398)
- **Ad-review exemption.** Newspaper, broadcast and internet drug ads must be pre-reviewed, but 전문지 are excluded from that review requirement (per search summary of the 바이오스펙테이터 article, undated, likely pre-2023). — [바이오스펙테이터](https://www.biospectator.com/news/view/2875)
- **Press release vs. disguised ad.** Under 식약처 guidance, an article is judged a 기사형 광고 (prohibited) when a company wrote false or exaggerated copy and pushed it to a reporter, or when a company asked for a specific ETC product to be described in detail. A new-product press release that goes beyond the approved indication can breach the 약사법. — [메디파나뉴스](http://m.medipana.com/index_sub.asp?NewsNum=192019)
- A lawyer quoted in 의협신문: "if a reporter asks only about A and the company also supplies B, C and D, the excess can be deemed advertising." A normal press release based on objective, verifiable data is not treated as an ad (date not confirmed). — [의협신문](https://www.doctorsnews.co.kr/news/articleView.html?idxno=125847)
- **바이오스펙테이터 BioS+.** Marketed as a premium news service for a "전문가언론" (expert press), offering analysis rather than "simple information delivery." BioS+ articles require paid-member login, sign-up works only on the PC site, and payment needs admin approval. — [BioS+ section](https://m.biospectator.com/section/section_list.php?MID=11700)
  - One search summary quoted pricing of 6 months ₩3,000,000 / 12 months ₩5,000,000 for individuals or companies. I could not verify this on the fetched page, so treat it as unconfirmed.
- **바이오스펙테이터 also runs a Telegram channel** for distribution. — [t.me/biospectatorT](https://t.me/biospectatorT)
- **Prescription-data journalism (데일리팜, 히트뉴스).**
  - UBIST (유비케어) calculates prescription sales from pharmacy dispensing of outpatient prescriptions.
  - 데일리팜 explains the source differences. UBIST's panel is pharmacists. IMS/IQVIA's panel covers pharmacies, clinics, hospitals and wholesalers, so it also sees in-hospital injectables and OTC. EDI (심평원 claims) is the most accurate.
  - [데일리팜](https://m.dailypharm.com/user/news/156840)
- 데일리팜 regularly ranks pharma companies by UBIST outpatient prescription sales (e.g., quarterly top-10 stories). — [데일리팜](https://dailypharm.com/user/news/90665)
- 히트뉴스 has covered the UBIST vs IQVIA competition ("처방액+세부데이터 복합전략"). — [히트뉴스](https://www.hitnews.co.kr/news/articleView.html?idxno=56744)
- Data-source pitfall: after UBIST changed its algorithm, gaps between datasets caused confusion in the industry (데일리팜, older article). — [데일리팜](https://www.dailypharm.com/user/news/65358)
- **UBIST products.** UBIST Pharmacy (outpatient prescription sales analytics, also pitched to stock investors) and UBIST HCD (prescribing-institution analytics). The descriptions are company claims. — [teamubist](https://www.teamubist.co.kr/Introduce/Pharmacy); [이투데이](https://www.etoday.co.kr/news/view/2332845)
- **메디게이트.** Its parent platform calls itself the "NO.1 의사 커뮤니티 & 커리어 플랫폼," so 메디게이트뉴스 is attached to a doctor community and career platform. — [App Store listing](https://apps.apple.com/app/id892284960)
- **Portal partnership.** Naver suspended news-partnership evaluation in May 2023 and announced a new 뉴스제휴위원회 to launch in June 2025.
  - Structure: a policy committee, a partnership-review committee and an operations-evaluation committee. Reviewers are drawn at random from a pool of 300–500 experts.
  - New-entrant evaluation is at least 50% quantitative, and qualitative evaluators judge only their own field.
  - [한국기자협회](https://www.journalist.or.kr/news/article.html?no=58593); [미디어스, 2025](https://www.mediaus.co.kr/news/curationView.html?idxno=313162)
- 미디어오늘 (2025/26) reported that Naver's partnership review runs monthly from March, with seven reviewers rotated every six months. — [미디어오늘](https://www.mediatoday.co.kr/news/articleView.html?idxno=332520)
- I found no source on rules specific to medical trade outlets in Naver's partnership process.

### Inferences
- Because ETC advertising is legally confined to professional media, competitors fight over pharma ad budgets and over "professional readership" (doctors, pharmacists, investors). Data and analysis products (BioS+, prescription rankings) are how outlets set themselves apart.
- For 청년의사, an internal tool that (a) automatically flags the regulatory risk of 기사형 광고 in press-release-based drafts (excess indication claims, "최초/최대" wording, comparative superiority) and (b) logs sponsor and advertiser relationships next to each story would serve both compliance and independence.
- Prescription-data stories (UBIST, IQVIA, EDI) are a recurring competitor format. Even if 청년의사 does not license UBIST, tracking competitors' prescription-ranking stories and 심평원 public data could fill the gap. A source-difference explainer (UBIST vs IQVIA vs EDI) could be built into the AI Q&A.

### Gaps
- I found no verified current pricing or feature list for 바이오스펙테이터 BioS+ (only an unverified ₩3m/₩5m figure), 히트뉴스's or 데일리팜's paid products, 더바이오, 코리아바이오메드, 메디칼업저버, 메디칼타임즈 or 데일리메디. Their subscription and about pages were not fetched.
- I found no data on traffic, headcount or revenue mix (ad vs subscription vs events) for any Korean medical trade outlet.
- I found no authoritative count of 의약전문지 or survey of pharma sponsorship practices; a search on "전문지 난립" returned nothing directly relevant.
- I did not confirm which medical trade outlets currently have Naver or Daum search or content partnerships.

---

## 2. What Korean medical reporters say about their work: access, embargoes, 기자단, verification

### Takeaway
The most concrete recent (2024) friction is access. During the 의정갈등, the 대한의사협회 (KMA, 의협) unilaterally suspended several outlets for two weeks over unfavourable coverage, insisted on spokesperson-only contact and demanded deletions. More broadly, Korean 기자단 and embargo practices are informal and set by the reporters' groups, and 전문지 reporters report being excluded or disadvantaged. Academic work on Korean medical journalists is thin and mostly concerns physician-journalists at general outlets.

### Cited Findings
- **2024 의협 출입정지.** On 2024-06-27, 한국기자협회 said the KMA had "unilaterally notified multiple outlets of suspension because their reporting conflicted with doctors' demands."
  - In at least one case the trigger was a column, not a news article.
  - The KMA demanded that reporters go only through its spokesperson, and called some reports false and asked for deletion even though its own executives had confirmed the facts.
  - The KMA spokesperson apologized, attributing it to the new president's chaotic early term. The suspensions lasted two weeks.
  - The article does not name the outlets.
  - [미디어오늘, 2024-06-27](https://www.mediatoday.co.kr/news/articleView.html?idxno=319042); also [이투데이](https://www.etoday.co.kr/news/view/2374272), [아주경제](https://www.ajunews.com/view/20240627162850687)
- 기자협회 noted the KMA has no formal 출입기자단, yet used the idea of "출입정지" to chill reporting (per search summary). — [미디어오늘](https://www.mediatoday.co.kr/news/articleView.html?idxno=319042)
- **Doctors back on the streets (Nov 2025).** Doctors' groups returned to rallies, threatening "총력 투쟁" against "의료악법." This shows the 의정 conflict beat is still active after the 2024–25 standoff. — [메디컬투데이](https://www.mdtoday.co.kr/news/view/1065577592051230)
- **기자단 and 전문지 exclusion** (미디어오늘 "기자단 이제는 바꾸자" series, around 2019).
  - Institutions grant pressrooms and passes on a discriminatory basis, while a private body, the 기자단, decides who gets them.
  - A 전문지 reporter ("B기자") argued that the criteria should be set by the institution, not by reporters.
  - [미디어오늘 ⑤](http://www.mediatoday.co.kr/news/articleView.html?idxno=211664); [③ "기자단 가입 위해" 선물에 트로트까지](https://www.mediatoday.co.kr/news/articleView.html?idxno=211461)
- **Embargo enforcement.**
  - Embargoes require the parties' consent, and outlets outside the 기자단 that were never notified are arguably not bound.
  - Sanctions (pressroom bans, cutting off press releases) are applied by the 출입 reporters themselves. A court held such customary sanctions not unlawful.
  - Year unclear (older). [미디어오늘](https://www.mediatoday.co.kr/news/articleView.html?idxno=124570); see also [미디어오늘 "엠바고 남발에 저널리즘이 멍든다"](https://www.mediatoday.co.kr/news/articleView.html?idxno=5445)
- **Academic study of physician-journalists.**
  - Study: 김지현·김용찬·심민선·박기호, "의학전문기자의 전문성과 언론사 조직 내에서의 업무 자율성: 이중적 직업 정체성의 전략적 이용," 한국언론학보 62(1), 7–35 (2018).
  - Method: in-depth interviews with 10 의학전문기자 at major outlets.
  - Finding: they use their dual doctor-reporter identity strategically to widen their work autonomy.
  - [KCI](https://www.kci.go.kr/kciportal/ci/sereArticleSearch/ciSereArtiView.kci?sereArticleSearchBean.artiId=ART002317890); [DBpia](https://www.dbpia.co.kr/journal/articleDetail?nodeId=NODE07369599)
- **Accuracy evidence (old).**
  - A 2006 가정의학회지 study of TV evening-news medical items found about 40% errors from an evidence-based-medicine standpoint.
  - The error rate was 12.5% when the reporter was a 의학전문기자 vs 46.1% otherwise, but there were only 8 specialist items.
  - [가정의학회지 2006;27:523-528](https://www.kjfm.or.kr/upload/pdf/Jkafm027-07-02.pdf)
- **Health-article mix.** A content analysis of 1,227 health articles in six newspapers in 2014 found industry/product, policy and medical-service topics most frequent (오대영·최믿음, 언론과학연구, 2016). — [KCI](https://www.kci.go.kr/kciportal/ci/sereArticleSearch/ciSereArtiView.kci?sereArticleSearchBean.artiId=ART002114788)
- **Advertorial share in a crisis.** In MERS "prevention food" internet articles, 37% were judged advertorial, and sources were often unclear or low-credibility. — [Korean Review of Crisis & Emergency Management](https://journal.kci.go.kr/cemtp/archive/articlePdf?artiId=ART002055021)
- **Older critique.** An old 의협신문 piece is headlined "의학 전문기자들, 상업화·과장 문제있어" (commercialization and exaggeration problems among medical reporters). — [의협신문](https://www.doctorsnews.co.kr/news/articleView.html?idxno=100454)
- **한국의학바이오기자협회 (의기협).** Launched in March 2021. In March 2026 it named 민태원 (국민일보 의학전문기자) as its third president. It holds policy symposia, e.g., on health-checkup big data at the Korea Press Center. — [경향신문, 2026-03-19](https://www.khan.co.kr/article/202603191544001)

### Inferences
- **Access risk.** Trade reporters covering the 의협 and other professional bodies face access retaliation (suspensions, spokesperson-only rules, deletion demands). A feature that logs every official statement and Q&A with a timestamp and source, and keeps records of fact-confirmation contacts, would help a newsroom defend against "오보" claims. 청년의사 is closely tied to the doctor community, which makes this especially relevant.
- **Embargo tracking.** Korean embargoes are informal and enforced by 기자단, with sanctions such as being cut off from press releases. The app's existing embargo detection could be extended into an embargo ledger: which 출입처 or 기자단 set it, release time, and a record of breaches or penalties.
- **Verification support.** Korean academic evidence on trade-press accuracy is outdated, but the international guidance in section 3 (HealthNewsReview criteria) is directly transferable as an AI checklist.

### Gaps
- I found no 2023–2026 기자협회보 or 미디어오늘 article specifically interviewing 의료전문지 reporters about press-release overload, 학회-season workload or the pharma-ad dependence they feel day to day.
- I found no KCI paper since 2020 focused specifically on 의료전문지 or 보건의료 trade reporters' working conditions (the search returned only the 2018 한국언론학보 study and older content analyses).
- I did not confirm the details of 의기협's education programs (2025 seminar content not found).
- I did not research whether 복지부, 식약처 and 심평원 기자단 currently admit 전문지 reporters.

---

## 3. International specialist health outlets and their tools

### Takeaway
Leading US and UK health trade outlets layer structured trackers, topic-specific newsletters, author and topic alerts, and team licenses on top of news. Examples are STAT+'s trackers, Fierce Pharma's running regulatory tracker, and Endpoints' FDA+ newsletter. On the public-interest side, the field relies on expert-reaction services (Science Media Centre), embargo infrastructure (EurekAlert!), reporting checklists (HealthNewsReview's 10 criteria, AHCJ guides) and crowdsourced investigation formats (KFF Health News' Bill of the Month).

### Cited Findings
- **STAT+ (fetched 2026).**
  - Trackers on "generative AI, obesity drugs, CRISPR, and the FDA fast-tracked devices," plus "premium data tools and industry trackers to identify trends, study competitors."
  - Subscriber newsletters such as "AI Prognosis" and "Biotech Scorecard."
  - Breaking-news notifications and email alerts by topic or author.
  - Pricing: $39 a month or $399 a year. Group plans for 2–10 users cost $300 per user per year, and 11+ users get custom Enterprise pricing.
  - Discounts of up to 75% for students, educators and healthcare workers.
  - [STAT+](https://www.statnews.com/stat-plus/)
- **Fierce Pharma "Regulatory tracker".** A running, periodically renewed roundup (H2 2025, H1/2026 editions) of FDA approvals and filings, each edition titled after its latest item (e.g., "FDA starts review of Sandoz's generic tirzepatide"). — [Fierce Pharma 2026 tracker](https://www.fiercepharma.com/pharma/fierce-pharma-regulatory-tracker-2026); [H2 2025](https://www.fiercepharma.com/pharma/fierce-pharma-regulatory-tracker-second-half-2025)
- **Endpoints News FDA+.** A dedicated FDA channel and a weekly ENDPOINTS FDA+ newsletter (Wednesdays, 2 PM ET), alongside its daily and weekly products. — [Endpoints FDA+ channel](https://endpts.com/channel/fda-plus/page/40)
- **The PDUFA calendar ecosystem (third-party, 2026).** PDUFA dates are FDA's target decision dates.
  - pdufa.bio: free calendar of about 110 2026 PDUFA dates. Its $100/yr Pro tier adds a live tracker, date-slip alerts and a screener.
  - BiopharmaWatch: paid calendar with trial readouts.
  - FDATracker: adds trial completion dates and cash runway.
  - MarketBeat and Benzinga: free calendars.
  - [pdufa.bio pricing](https://www.pdufa.bio/pricing); [pdufa.bio calendar](https://www.pdufa.bio/calendar); [BiopharmaWatch](https://www.biopharmawatch.com/); [FDATracker](https://www.fdatracker.com/fda-calendar/); [Benzinga](https://www.benzinga.com/fda-calendar/pdufa)
- **Science Media Centre (UK) model.**
  - Rapid Reactions: expert comment sent out in response to breaking stories.
  - Roundups: third-party scientist reaction to new research, prepared before the embargo lifts.
  - Briefings: scientists meet journalists face to face.
  - All of these rely on an expert database.
  - SMC launched a one-year pilot All-Ireland SMC in June 2024, limited to Rapid Reactions and Roundups. New Zealand's SMC runs a similar "Expert Reaction" format.
  - [SMC Journalist FAQs 2024 (PDF)](https://sciencemediacentre.org/wp-content/uploads/2016/08/Journalist-FAQs-2024-1.pdf); [SMC roundups](https://sciencemediacentre.org/roundups-for-journalists); [SMC Ireland](https://sciencemediacentre.org/roundups-ireland); [SMC NZ](https://www.sciencemediacentre.co.nz/category/science-alert-experts-respond/page/26/)
- **EurekAlert! (AAAS) embargo system.**
  - An embargo is a date and time before which registered reporters, who get advance access, agree not to publish.
  - Registration is free but individual (no shared newsroom accounts), and AAAS decides eligibility.
  - Journal content is additionally gated by each journal.
  - Embargoed releases move to the public feed automatically when the embargo lifts. PIOs can share releases up to two weeks ahead.
  - [EurekAlert FAQ](https://www.eurekalert.org/help); [Embargoes on EurekAlert (blog, 2018)](https://blog.eurekalert.org/2018/08/27/embargoes-on-eurekalert/); [PIO guidelines](https://eurekalert.org/pioguidelines)
- PLOS and PNAS tie embargoed access to EurekAlert registration (the PNAS page is archived and may be outdated). — [PLOS embargo policy](https://plos.org/?p=1113); [PNAS press (archived 2020)](https://bac-lac.wayback.archive-it.org/web/20200424190126/https://www.pnas.org/page/about/press)
- **HealthNewsReview.org 10 criteria.**
  - Standardized criteria for stories claiming medical-intervention effects, including: adequately discussing costs, quantifying benefits, and explaining or quantifying harms.
  - About 70% of reviewed stories scored unsatisfactory on cost, benefit and harm. Of 1,854 stories, only 30% of cost scores were satisfactory.
  - The site has stopped publishing reviews, but AHCJ wrote in July 2024 that the criteria "are as relevant as ever."
  - [AHCJ, 2024-07](https://healthjournalism.org/blog/2024/07/writing-about-health-care-interventions-the-healthnewsreview-criteria-are-as-relevant-as-ever/); [PMC4029196](https://pmc.ncbi.nlm.nih.gov/articles/PMC4029196); [Nieman Lab](https://www.niemanlab.org/?p=169015)
- **AHCJ resources.**
  - The medical-studies core topic links "Covering Medical Research: A Guide for Reporting on Studies" (Gary Schwitzer), the NIH clinical research glossary, Dartmouth question lists, and a CJR case on "false balance."
  - It warns that "significant" means something different in research than in everyday language.
  - [AHCJ resource page](https://healthjournalism.org/?p=7194); [AHCJ guides](https://healthjournalism.org/helpful-links/guides-to-reporting/); [Implementing the 10 criteria](https://healthjournalism.org/?p=13325)
- **KFF Health News "Bill of the Month."**
  - A crowdsourced investigation of reader-submitted medical bills, running since 2018 with NPR.
  - The NPR partnership ended in December 2024, and the series continues with The Washington Post's Well+Being.
  - Nearly 10,000 submissions, and about 1 in 3 bills were resolved for the patient by publication.
  - [WGBH/NPR, 2024-12-20](https://www.wgbh.org/news/2024-12-20/bill-of-the-month-the-series-that-dissects-and-slashes-medical-bills); [KFF series page](https://kffhealthnews.org/series/bill-of-the-month/)
- KFF Health News also built a database of drugmaker campaign donations over 10 years (date not confirmed in results). — [KFF Health News](https://kffhealthnews.org/tag/investigation/)

### Inferences
- The common pattern is that trade outlets turn recurring beats (approvals, regulatory filings, pipeline readouts) into structured, continuously updated trackers. These feed both stories and paid products, while per-topic and per-author alerts plus team licenses monetize B2B readers. 청년의사's existing DART/ALIO monitoring is the same building block. The step up is to publish or curate trackers internally first.
- The SMC model (a pre-built expert database with rapid, pre-embargo reaction gathering) maps well onto 청년의사's doctor-founded network. An internal "expert reaction desk" (specialty-tagged doctors, 학회 officers and pharmacologists, with contact history and response speed) would speed verification of clinical-trial and policy claims.
- The HealthNewsReview criteria (cost, benefit size, harms, evidence quality, novelty, availability, alternatives, conflicts of interest, independent sources, not relying only on the press release) can be turned into an AI pre-publication checklist for drafts generated from pharma press releases.

### Gaps
- I did not verify a full list of STAT+ trackers beyond those named on the STAT+ page. I found no STAT-run PDUFA calendar (the PDUFA calendars found are third-party).
- I did not fetch the product details for BioCentury, Evaluate Vantage, Citeline (Pink Sheet/Scrip) or MedPage Today trackers. These are enterprise products, and I found no public feature pages in the searches.
- I did not cover JAMA, NEJM or Lancet press-embargo programs specifically.
- Retraction Watch database, ClinicalTrials.gov results tracking, and ASCO/AACR/ESMO coverage workflows (abstract-release embargo times, late-breaking abstracts) were not researched within the call budget.

---

## 4. Which tools and workflows could be adapted to the Korean context (inference-heavy)

### Takeaway
Most international tools rest on public, scheduled regulatory events (PDUFA dates), embargo infrastructure and expert databases. Korea has analogous scheduled events (식약처 approvals, 약제급여평가위원회 and 건정심 agendas, 학회 congresses), but I found no evidence that any Korean medical trade outlet publishes a structured calendar or tracker for them. That makes it a plausible differentiator, though it is my inference and not verified.

### Cited Findings
- PDUFA calendars are a proven, monetizable format: free calendar plus paid alerts on date slips. pdufa.bio Pro costs $100/yr. — [pdufa.bio pricing](https://www.pdufa.bio/pricing)
- STAT+ sells topic trackers plus per-topic and per-author alerts, with team pricing ($300/user/yr for 2–10 users). — [STAT+](https://www.statnews.com/stat-plus/)
- Fierce maintains a running regulatory tracker updated per approval or filing. — [Fierce Pharma](https://www.fiercepharma.com/pharma/fierce-pharma-regulatory-tracker-2026)
- Korean trade outlets already produce recurring data stories from UBIST, IQVIA and EDI prescription data, noting limits such as outpatient-only coverage and no hospital-type breakdown. — [데일리팜](https://m.dailypharm.com/user/news/156840); [히트뉴스](https://www.hitnews.co.kr/news/articleView.html?idxno=56744)
- Korean embargoes are informal and 기자단-enforced, and outlets outside the 기자단 may not be notified. — [미디어오늘](https://www.mediatoday.co.kr/news/articleView.html?idxno=124570)
- EurekAlert's model is individual accounts, automatic public release at embargo lift, and up to two weeks of advance access. — [EurekAlert FAQ](https://www.eurekalert.org/help)

### Inferences (feature ideas for 청년의사's internal app; not evidence-backed demand)
1. **Korean regulatory calendar ("K-PDUFA").** One calendar for 식약처 approvals and 품목허가 (and items like 신속심사 or GIFT), 약평위 results, 건정심 agenda and results, 암질심 (cancer-drug reimbursement committee), 약가협상 deadlines, and 고시 effective dates. Add a "date-slip" alert like pdufa.bio's. Combined with DART disclosures, this would give pharma reporters a single pipeline view.
2. **학회 season planner.** A calendar of major Korean 학회 congresses (춘계/추계) and international ones (ASCO, AACR, ESMO, ADA, EASD and others). Fields: abstract-release and embargo times, Korean companies presenting (cross-referenced with DART disclosures of 학회 presentations), reporter assignment and claim, and post-congress follow-up. This addresses the workload spike, which the brief names but I did not find documented.
3. **Expert reaction desk (SMC-style).** A specialty-tagged expert database built on 청년의사's doctor network, with a one-click request for reactions to a new study or policy, collected into a roundup draft. Track conflicts of interest (pharma consulting) per expert.
4. **Pre-publication evidence checklist.** Score AI drafts and press-release-based stories against the HealthNewsReview criteria (absolute vs relative risk, harms, cost/급여, study phase and sample size, independent source, COI). Add a 약사법 기사형광고 risk flag (indications beyond 허가 사항, "최초/최대" claims, ETC product detail on company request). [Sources for the criteria: AHCJ 2024; for the ad rules: 메디파나뉴스, 의협신문 above]
5. **Embargo ledger and source-access log.** Extend the existing embargo detection to record issuer, 기자단, lift time and conditions, with auto-unlock reminders. Keep a log of statements and fact-confirmation contacts with professional bodies (의협, 병협, 학회) to rebut "오보" claims and record access sanctions, in light of the 2024 의협 suspension episode.
6. **Prescription and reimbursement data tracker.** Use public 심평원 and 건보공단 data (and licensed UBIST/IQVIA if budget allows) for quarterly rankings by company and product, with built-in source caveats (UBIST vs IQVIA vs EDI differences).
7. **Topic trackers and B2B alerts (STAT+-style).** Internal "living" trackers for hot beats: 의대 정원/의정갈등 timeline, 비만치료제 in Korea, 공공병원 finances (already partly built), bio licensing deals and tech-transfer contracts from DART. These could later become a premium product or newsletter for pharma and investor readers.
8. **Crowdsourced reader-submission investigations (Bill of the Month analog).** Collect doctor-reader submissions (e.g., 삭감 사례, 수가 문제, 전공의 근무 실태) into structured investigations. This fits 청년의사's doctor-community readership.

### Gaps
- I found no source confirming whether 식약처, 심평원 or 복지부 publish machine-readable schedules for 약평위, 건정심 or 암질심 meetings or approval targets. Feasibility of features 1 and 6 needs a separate check (data.go.kr, 심평원 공지).
- I found no evidence on whether competing Korean outlets (히트뉴스, 데일리팜, 바이오스펙테이터, 더바이오) already offer regulatory calendars, deal trackers or pipeline DBs. The competitive whitespace is unverified.
- I found no first-hand Korean reporter testimony on 학회-season workload or press-release volume to rank these ideas by pain-point severity. A short internal survey of 청년의사 reporters is recommended.
