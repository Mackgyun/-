# 의료·제약·바이오·보건정책 기자가 모니터링하는 정보원과 자동수집 가능성 (2026-11 기준)

How we checked: on 2026-11-15 we called endpoints live from this sandbox. To confirm that a data.go.kr service exists, we called it with no key. A reply of `SERVICE_KEY_IS_NULL` means the service exists. A reply of `NO_OPENAPI_SERVICE_ERROR` means it is retired. We also scraped each data.go.kr dataset page for its endpoint, 업데이트 주기, 트래픽 and 이용허락범위. A row is marked **[검증]** only when we confirmed it on an official page or with a live call. A row is marked **[미검증]** when it rests on secondary sources or on memory. The sandbox could not open the sites of several Korean agencies (curl timed out): mfds.go.kr, nedrug.mfds.go.kr, hira.or.kr, opendata.hira.or.kr, nhis.or.kr and cris.nih.go.kr. The cause may be IP or overseas blocking. kind.krx.co.kr returned 403 (Akamai Access Denied). **Your production server, if it is in Korea, should test these sites again itself.**

---

## Q1. 정보원별 공식 Open API·RSS·다운로드 여부, 정확한 서비스명, 갱신 빈도

### Takeaway
Most of the high-value MFDS data is offered as REST APIs on data.go.kr, labelled "실시간": drug approvals, clinical trial approvals, recalls and sales suspensions, safety letters, administrative sanctions, device approvals, and supply interruptions. Each is free and gives a development account 10,000 calls per day. The 22nd National Assembly bill API on 열린국회정보 works today, including bills filtered by committee. By contrast, **정책브리핑 (korea.kr) stopped its RSS service on 2026-07-01.** The replacement is the data.go.kr API 「문화체육관광부_정책브리핑_정책뉴스_API」. Data that matters most to the HIRA and NHIS beat has no API: changes to the 약제급여목록 (reimbursement list), 약평위 (drug benefit evaluation committee) results, and drug price negotiation results. These come only as notices, board posts or attachments, so they need HTML scraping.

### Cited Findings

#### A. 식약처 (MFDS): data.go.kr (기관코드 1471000)
All rows below were checked on their data.go.kr dataset pages: REST, JSON/XML, free, development account 10,000 calls/day, 업데이트 주기 shown as "실시간". Usage terms say "이용허락범위 제한 없음" unless a row notes otherwise.

| 데이터 | data.go.kr ID | 엔드포인트 (Base / 오퍼레이션) | 기자 활용 | 출처 |
|---|---|---|---|---|
| 의약품 제품 허가정보 | 15095677 | `apis.data.go.kr/1471000/DrugPrdtPrmsnInfoService08` / `getDrugPrdtPrmsnInq08` (list), `getDrugPrdtPrmsnDtlInq08` (detail), `getDrugPrdtMcpnDtlInq08` (ingredients). **Service07 still answers but 06 returns "폐기됨", so the version number keeps rising and must be tracked.** [검증] | New approvals, first generics, approvals for new drugs | [data.go.kr 15095677](https://www.data.go.kr/data/15095677/openapi.do) |
| 의약품 임상시험 정보 (승인 기본정보) | 15056835 | `1471000/MdcinClincTestInfoService02` / `getMdcinClincTestInfoList02` [검증] | Daily or weekly lists of approved clinical trial protocols (typical article: "한미약품 오락솔 등 6건 임상계획 승인") | [data.go.kr 15056835](https://www.data.go.kr/data/15056835/openapi.do); story example [데일리팜](https://dailypharm.com/user/news/208522) |
| 의약품 임상시험 계획 상세정보 | 15090589 | `1471000/ClncExamPlanDtlService03` / `getClncExamPlanDtlInq03` [검증] | Trial phase, indication, sponsor detail | [data.go.kr 15090589](https://www.data.go.kr/data/15090589/openapi.do) |
| 임상시험 계획 시험책임자 / 선정기준 / 제외기준 | 15090384 / 15090368 / 15090376 | `1471000/ClncExamPlanTestPscgService04` (시험책임자) [검증]; the other two exist in the catalog (endpoints not checked) | Which hospitals and investigators take part | [data.go.kr 15090384](https://www.data.go.kr/data/15090384/openapi.do) |
| 의약품임상시험 실시기관 정보 | 15058129 | Exists in the catalog (endpoint not checked) | Designation of trial sites | data.go.kr search results (see above) |
| 바이오의약품 해외임상승인현황 | 15106956 | `1471000/BioMdcinOvseaClncAprvStus` / `getBioMdcinOvseaClncAprvStus` [검증] | Overseas trials by Korean biotechs | [data.go.kr 15106956](https://www.data.go.kr/data/15106956/openapi.do) |
| **의약품 회수·판매중지 정보** | 15059114 | `1471000/MdcinRtrvlSleStpgeInfoService05` / `getMdcinRtrvlSleStpgelList05`, `getMdcinRtrvlSleStpgeItem05`, `...EtcList05` [검증] | Breaking: recalls (impurities, quality nonconformance) and sales suspensions | [data.go.kr 15059114](https://www.data.go.kr/data/15059114/openapi.do) |
| **의약품안전성서한 정보** | 15059182 | `1471000/DrugSafeLetterService02` / `getDrugSafeLetterList02` [검증] | Breaking: safety letters and quick-response notices | [data.go.kr 15059182](https://www.data.go.kr/data/15059182/openapi.do) |
| **의약품 행정처분 정보** | 15058457 | `1471000/MdcinExaathrService04` / `getMdcinExaathrList04` [검증] | Manufacturing or sales suspensions and approval revocations (e.g. GMP violations, rebates) | [data.go.kr 15058457](https://www.data.go.kr/data/15058457/openapi.do) |
| 의약품 생산수입공급중단정보 | 15057899 | `1471000/MdcinPrdctnIncmeSuplyService2` / `getMdcinPrdctnIncmeSuplyList` [검증] | Drug shortages and supply-interruption reports (e.g. pediatric antipyretics, antibiotics) | [data.go.kr 15057899](https://www.data.go.kr/data/15057899/openapi.do) |
| 의약품 재심사 정보 | 15058034 | `1471000/MdcinRejdgeService02` / `getMdcinRdjdgeList02` [검증] | When new drugs leave re-examination (PMS), i.e. when generics can launch | [data.go.kr 15058034](https://www.data.go.kr/data/15058034/openapi.do) |
| 희귀의약품 정보 | 15057935 | `1471000/RareMdcinInfoService03` / `getRareMdcinList02` [검증] | Orphan drug designations | [data.go.kr 15057935](https://www.data.go.kr/data/15057935/openapi.do) |
| 의약품 특허정보 (허가-특허연계 목록) | 15057623 | `1471000/MdcinPatentInfoService2` / `getMdcinPatentInfoList2` [검증] | Patent challenges and first-generic exclusivity | [data.go.kr 15057623](https://www.data.go.kr/data/15057623/openapi.do) |
| 의약품 국내 특허현황 | 15117409 | `1471000/DrugDmstPtntStusService` [검증] | Same as above | [data.go.kr 15117409](https://www.data.go.kr/data/15117409/openapi.do) |
| FDA Paragraph IV / Orange Book patents / domestic patent litigation | 15058137 / 15057931 / 15056710 | `1471000/ParagraphIVTrgetMdcinService02` [검증]; the others exist in the catalog | Reference data for overseas patent disputes | [data.go.kr 15058137](https://www.data.go.kr/data/15058137/openapi.do) |
| 의료기기 품목허가 정보 | 15057456 | `1471000/MdlpPrdlstPrmisnInfoService06` / `getMdlpPrdlstPrmisnList05`, `getMdlpPrdlstPrmisnItem05` [검증] | Approvals of AI and digital medical devices | [data.go.kr 15057456](https://www.data.go.kr/data/15057456/openapi.do) |
| 의료기기 회수·판매중지정보 | 15056785 | `1471000/MdlpRtrvlSleStpgeInfoService04` / `getItemNameList04` and others [검증] | Device recalls | [data.go.kr 15056785](https://www.data.go.kr/data/15056785/openapi.do) |
| 의료기기 행정처분 정보 | 15117141 | `1471000/MdeqAdmmInfoService1` [검증] | Sanctions on device companies | [data.go.kr 15117141](https://www.data.go.kr/data/15117141/openapi.do) |
| 의료기기 임상시험계획승인신청 목록·상세 | 15073889 / 15073900 | Exist in the catalog (endpoints not checked) | Device trials | data.go.kr search results |
| DUR 품목정보 | 15059486 | `1471000/DURPrdlstInfoService03` [검증] | New contraindications and age restrictions | [data.go.kr 15059486](https://www.data.go.kr/data/15059486/openapi.do) |
| e약은요 (개요정보) | 15075057 | `1471000/DrbEasyDrugInfoService` / `getDrbEasyDrugList` [검증] | Reference only (low value) | [data.go.kr 15075057](https://www.data.go.kr/data/15075057/openapi.do) |

- What the 「실시간」 label means: every MFDS dataset page lists 업데이트 주기 as "실시간". In practice the lag behind a posting on 의약품안전나라 has not been verified. — [data.go.kr 15059114](https://www.data.go.kr/data/15059114/openapi.do)
- **MFDS press-release RSS:** we found no RSS address. MFDS press releases sit on the board at `mfds.go.kr/brd/m_99/list.do` (individual items at `view.do?seq=`). The site menu offers an "전자우편구독" (email subscription) instead. [미검증: the sandbox could not reach the site] — [식약처 보도자료 view 예시](https://www.mfds.go.kr/brd/m_99/view.do?seq=45599)

#### B. 건강보험심사평가원 (HIRA): data.go.kr (기관코드 B551182)
| 데이터 | ID | 엔드포인트 | 갱신 / 조건 | 출처 |
|---|---|---|---|---|
| 약가기준정보조회서비스 (급여 의약품 상한금액 기준) | 15054445 | `B551182/dgamtCrtrInfoService1.2` / `getDgamtList` (product prices), `getCmdcDgamtList` [검증] | Labelled "실시간", but **the page was last modified 2024-06-19**. Development account 10,000/day. Terms: 공공누리 Type 1 (attribution required) | [data.go.kr 15054445](https://www.data.go.kr/data/15054445/openapi.do) |
| 의약품사용정보조회서비스 | 15047819 | `B551182/msupUserInfoService1.2` (ATC, region, use by disease) [검증] | Statistics for market and usage stories | [data.go.kr 15047819](https://www.data.go.kr/data/15047819/openapi.do) |
| 의약품성분약효정보 | 15021027 | Exists in the catalog | Reference | data.go.kr search results |
| 수가기준정보조회서비스 | 15021028 | `B551182/mdfeeCrtrInfoService` [검증] | Changes to fee schedules | [data.go.kr 15021028](https://www.data.go.kr/data/15021028/openapi.do) |
| 병원정보서비스 | 15001698 | `B551182/hospInfoServicev2` / `getHospBasisList` [검증] | Basic information on hospitals | [data.go.kr 15001698](https://www.data.go.kr/data/15001698/openapi.do) |
| **요양기관개폐업정보조회서비스** | 15051043 | `B551182/yadmOpCloInfoService2` / `getHospPharmacyOpCloList` [검증] | Openings and closures of hospitals and pharmacies (e.g. closures of regional hospitals or pediatric clinics) | [data.go.kr 15051043](https://www.data.go.kr/data/15051043/openapi.do) |
| 병원평가정보서비스 (적정성평가) | 15094093 | `B551182/hospAsmInfoService1` / `getHospAsmInfo1` [검증] | Quality assessment grades | [data.go.kr 15094093](https://www.data.go.kr/data/15094093/openapi.do) |
| 비급여진료비정보조회서비스 | 15001700 | Exists in the catalog | Disclosure of non-covered service prices | data.go.kr search results |
| 약가마스터: 의약품표준코드 (file) | 15067462 | File download. **Quarterly** (next release 2026-12-15) [검증] | Master data for mapping KD codes | [data.go.kr 15067462](https://www.data.go.kr/data/15067462/fileData.do) |
| 약가마스터: 의약품주성분 (file) | 15067461 | File download. **Annual** (file dated 20261105) [검증] | Ingredient-code mapping | [data.go.kr 15067461](https://www.data.go.kr/data/15067461/fileData.do) |

- **약제급여목록 및 급여상한금액표 (reimbursement list and price caps):** this is a 보건복지부 고시 (ministry notice), based on Article 22(1) of the Enforcement Decree of the National Health Insurance Act. HIRA publishes the related "약가파일" (price file). Since 2021-12, HIRA has published a draft price file in advance, before the 건정심 (health insurance policy committee) deliberates. The final file is published after the notice takes effect. — [데일리팜](https://dailypharm.com/user/news/44526); [law.go.kr 고시 원문 파일](https://www.law.go.kr/LSW/flDownload.do?flSeq=170127171)
- Typical stories: new listings and delistings each month, e.g. "스티바가 등 204개 품목 신규 등재…112개 품목 퇴출" and "오늘부터 빅타비 … 급여". — [데일리팜 112505](https://dailypharm.com/user/news/112505); [데일리팜 72293](https://m.dailypharm.com/user/news/72293)
- **We found no API for 약평위 (drug benefit evaluation committee) results or for the monthly 약제급여목록 file.** The download location on HIRA's website (a notice board) could not be checked from the sandbox. [미검증]
- On HIRA's 보건의료빅데이터개방시스템 (opendata.hira.or.kr), the data.go.kr file 「보건의료빅데이터개방시스템_의약품현황」 (15064658) exists. — data.go.kr search results (keyword "약제급여목록")

#### C. 국민건강보험공단 (NHIS)
- On data.go.kr, NHIS mostly offers statistics files and search APIs for long-term care facilities. Examples: 「건강보험주요통계」 (15103019, file), 「장기요양기관 평가 결과」 (15104801), 「장기요양기관 검색 서비스」 (15059029, API). — data.go.kr search results (keyword "국민건강보험공단")
- **We found no API for press releases, drug price negotiation results or 건강보험공표.** These need HTML scraping of the nhis.or.kr board. The site could not be reached from the sandbox. [미검증]

#### D. 보건복지부 · 법제처 (입법예고·행정예고·고시)
- **입법예고 (proposed legislation):**
  - 「법제처_정부입법예고」 (15058407) and 「법제처_정부행정예고」 (15056627) are listed on data.go.kr as type **LINK**: real-time, free, traffic set by the providing agency. The actual API runs on 국민참여입법센터 (opinion.lawmaking.go.kr), which requires registering an ID (OC) and an IP. — [data.go.kr 15056627](https://www.data.go.kr/data/15056627/openapi.do); [국민참여입법센터 API 문답](https://opinion.lawmaking.go.kr/advc/stmInq/24173)
  - 「행정안전부_관보_입법예고」 (15109162) is a REST API: `apis.data.go.kr/1741000/ApiPblancLgsltService` / `getApiPblancLgsltList`, 10,000 calls/day. [검증] — [data.go.kr 15109162](https://www.data.go.kr/data/15109162/openapi.do)
- **국가법령정보 공동활용 (law.go.kr DRF):**
  - Endpoint `https://www.law.go.kr/DRF/lawSearch.do?OC={ID}&target=law|admrul&type=XML|JSON`, plus `lawService.do` for full text.
  - A live call with an unregistered OC returned "사용자 정보 검증에 실패…서버장비의 IP주소 및 도메인주소를 등록해 주세요". **You must register the server IP or domain in advance.** [검증]
  - The guide list on open.law.go.kr includes "행정규칙 목록 조회", "행정규칙 본문 조회", "행정규칙 신구법 비교", "법령 변경이력 목록 조회" and others. [검증]
  - The parameter `knd` filters by type: 1=훈령, 2=예규, 3=고시.
  - Sources: [open.law.go.kr 가이드](https://open.law.go.kr/LSO/openApi/guideList.do); [knd 파라미터 예시(비공식 MCP 코드)](https://glama.ai/mcp/servers/rabqatab/LexLink-ko-mcp/tools/admrul_search)
- Matching problem: 행정예고 titles do not always match the 행정규칙 (administrative rule) titles that follow, so pairing a proposal with its final rule is hard. — [국민참여입법센터 문답](https://opinion.lawmaking.go.kr/advc/stmInq/24173)
- **보도자료 of 보건복지부, 질병관리청 and 식약처:**
  - The 정책브리핑 RSS service, which used to carry them, **was discontinued on 2026-07-01**. The stated reason: "콘텐츠 저작권 등 권리 보호에 따른 제공방식 변경" (a change in delivery method to protect copyright and other rights). [검증] — [정책브리핑 공지](https://www.korea.kr/etc/noticeView.do?newsId=132038885)
  - In the curl test, the old address `korea.kr/rss/dept_*.xml` returned 404 or timed out. [검증]
  - **Replacement:** 「문화체육관광부_정책브리핑_정책뉴스_API」 (15095335), `apis.data.go.kr/1371000/policyNewsService2`, REST. Development account only **1,000 calls/day**. Terms: 공공누리 Type 1. Page modified 2026-11-10. [검증] — [data.go.kr 15095335](https://www.data.go.kr/data/15095335/openapi.do)
  - Whether this API also carries 보도자료 (press releases), not just 정책뉴스 (policy news), is **not verified**. The data.go.kr search result for 「문화체육관광부_e브리핑」 (15101213, LINK) also appears. — [data.go.kr 15101213](https://www.data.go.kr/data/15101213/openapi.do)
  - The MOHW press-release board (`mohw.go.kr/board.es?mid=a10503000000&bid=0027`) returned HTTP 200. It is HTML that requires JS redirect handling. [검증: reachable]
- No API or RSS was found for 건정심 (health insurance policy committee) results. Results are published as MOHW press releases. [미검증]

#### E. 질병관리청 (KDCA)
- 「질병관리청_전수신고 감염병 발생현황」 (15139178): `apis.data.go.kr/1790387/EIDAPIService01`, labelled real-time, development account **1,000 calls/day**, 공공누리 Type 1. [검증] — [data.go.kr 15139178](https://www.data.go.kr/data/15139178/openapi.do)
- 「질병관리청_임상연구 DB」 (CRIS) (3033869): `apis.data.go.kr/1352159/crisinfodataview/list`, 10,000 calls/day. **Terms: 공공누리 Type 2 (attribution, no commercial use).** For a commercial outlet this is a terms issue. [검증] — [data.go.kr 3033869](https://www.data.go.kr/data/3033869/openapi.do)
- 「질병관리청_임상연구 등록통계」 (3074275) also exists. — [data.go.kr 3074275](https://www.data.go.kr/en/data/3074275/openapi.do)
- No API was found for KDCA press releases. RSS ended with the 정책브리핑 shutdown. Use HTML scraping or the 정책브리핑 API. [미검증]

#### F. 국회 (열린국회정보 open.assembly.go.kr)
- **국회의원 발의법률안 API:**
  - URL: `https://open.assembly.go.kr/portal/openapi/nzmimeepazxkubdpn?Type=json&pIndex=1&pSize=N&AGE=22[&COMMITTEE=보건복지위원회][&KEY=…]`
  - A live call **without a KEY returned results normally**. For AGE=22 the list_total_count was 20,818, and the newest bill was proposed on 2026-11-13. [검증]
  - **COMMITTEE=보건복지위원회 filtering works:** total of 1,859 bills. Recent results included bill numbers 2222746 (응급의료법) and 2222711 (첨단재생바이오법), proposed 2026-11-12. [검증]
  - Response fields: BILL_ID, BILL_NO, BILL_NAME, COMMITTEE, PROPOSE_DT, PROC_RESULT, PROPOSER, DETAIL_LINK (likms), MEMBER_LIST.
  - Right after a bill is proposed, COMMITTEE can be null because the bill has not yet been referred. **Collect the whole list without the committee filter, then classify by keyword.**
- Without a key we asked for pSize=3 and got 5 rows back. This suggests a sample mode limited to about 5 rows, so **get a free KEY for production use**. The tutorial says getting a key "takes about 5 minutes". — [assembly tutorial](https://kyusik-yang.github.io/assembly-tutorial/)
- data.go.kr lists these as LINK-type datasets, free and real-time: 「의안정보 통합 API」 (15126134), 「의안 상세정보」 (15126096), 「의안별 표결현황」 (15126044), 「법률안 심사 및 처리(최근 본회의처리 의안)」 (15125996), and others. — [data.go.kr 15125946](https://data.go.kr/data/15125946/openapi.do); [data.go.kr 15126134](https://data.go.kr/data/15126134/openapi.do)
- For 회의록 (meeting minutes), 국정감사 (audit) materials and the broadcast service: service codes were not verified. [미검증]

#### G. 임상시험 (ClinicalTrials.gov · CRIS · KoNECT)
- **ClinicalTrials.gov API v2:**
  - Live call `https://clinicaltrials.gov/api/v2/studies?query.locn=Korea&sort=LastUpdatePostDate:desc&fields=…` returned JSON. The newest update was 2026-11-13, and paging uses nextPageToken. No authentication. [검증]
  - Rate limit: third-party docs say "about 50 requests per minute per IP", but the official docs do not confirm this. Back off on 429 responses. — [intuitionlabs 가이드](https://intuitionlabs.ai/articles/clinicaltrials-gov-api-v2-pipeline); [api_reference 사본](https://cdn.jsdelivr.net/npm/@saibolla/ada@0.1.3/skills/clinicaltrials-database/references/api_reference.md)
- **CRIS:** available through the 질병관리청 data.go.kr API above, with Type 2 terms (no commercial use). CRIS is a WHO ICTRP primary registry. — [WHO ICTRP](https://www.who.int/clinical-trials-registry-platform/network/primary-registries/republic-of-korea-clinical-research-information-service-(cris))
- **KHIDI 임상시험 계획승인 목록:** the page `khidi.or.kr/mdtis/clncTestPlanAprv/clncTestPlanAprvList` exists (HTML). — [KHIDI](https://www.khidi.or.kr/mdtis/clncTestPlanAprv/clncTestPlanAprvList)
- KoNECT: no API was found. [미검증]

#### H. 특허 (KIPRIS Plus)
- **특허청 has been renamed 지식재산처.** data.go.kr lists KIPRIS Plus datasets under the name "지식재산처_KIPRISPlus_…", e.g. 15065443 「특허권 존속기간 연장등록 공보」. The ministry list on korea.kr also shows "지식재산처". — [data.go.kr 검색 결과 15065443](https://www.data.go.kr/data/15065443/openapi.do); [정책브리핑 기관목록](https://www.korea.kr/etc/noticeView.do?newsId=132038885)
- KIPRIS Plus free quotas differ by API. For example, one API allows 1,000 free calls per month. Calls above the quota and bulk data go through plus.kipris.or.kr, which charges fees or offers free-support programs. We did not find a general fee schedule. — [data.go.kr 15075967](https://www.data.go.kr/data/15075967/openapi.do); [KIPRIS Plus 관련 보도](https://bizhankook.com/articles/3079.html)
- For drug-patent stories, the MFDS 「의약품 특허정보」 API is free and is the more practical first choice (see table A).

#### I. 공정위 · 금융 · 기타
- On data.go.kr, 「공정거래위원회_결정문 목록 조회」 (15103246) and 「결정문 본문 조회」 (15103247) are LINK-type, free, real-time. The bulk 「결정문」 file is 15103301. [검증: existence] — [data.go.kr 15103246](https://www.data.go.kr/data/15103246/openapi.do)
- FTC rebate cases: under the FTC guideline, the decision text is sent to MOHW and MFDS within 30 days of the ruling. Example stories cover the JW중외제약 case (305억원 fine) and other pharma rebate sanctions. — [데일리팜 335784](https://dailypharm.com/user/news/335784); [데일리팜 21242](https://www.dailypharm.com/user/news/21242)
- KRX: 「금융위원회_KRX상장종목정보」 (15094775) and 「주식시세정보」 (15094808) are on data.go.kr. Direct access to KIND (kind.krx.co.kr) returned **403 Access Denied** (Akamai), so scraping KIND is hard. Market actions (trading halts, investment warnings) are covered in large part by DART filings and the KRX disclosure feed. — [data.go.kr 15094775](https://www.data.go.kr/en/data/15094775/openapi.do)
- No API or RSS was found for 감사원 (Board of Audit), 국민권익위원회, court rulings, or the press releases of 대한의사협회, 대한병원협회 and 한국제약바이오협회. [미검증]

#### J. 해외 (FDA · EMA · PubMed · medRxiv)
- **openFDA:**
  - `https://api.fda.gov/drug/drugsfda.json` returned 200 JSON. [검증]
  - Rate limits: without a key, 240 requests/minute and 1,000/day per IP. With a key, 240 requests/minute and 120,000/day per key. [검증]
  - The response includes a disclaimer: "Do not rely on openFDA to make decisions regarding medical care".
  - Sources: [open.fda.gov authentication](https://open.fda.gov/apis/authentication/); [terms](https://open.fda.gov/terms/)
- **FDA press-release RSS:** `https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/press-releases/rss.xml` returned 200 rss+xml. The newest item was a new-drug approval. [검증]
- **EMA news RSS:** `https://www.ema.europa.eu/en/news.xml` returned 200 rss+xml. [검증]
- **PubMed E-utilities:**
  - `esearch.fcgi?db=pubmed&term=Korea[ad]&reldate=1&retmode=json` returned 459 papers with a Korean affiliation added in one day. [검증]
  - Rate guidance commonly cited as 3/sec without a key and 10/sec with a key. This comes from a secondary citation and was not checked on the NCBI page. — [intuitionlabs](https://intuitionlabs.ai/articles/clinicaltrials-gov-api-v2-pipeline)
- medRxiv: the home page returned 200. The API (api.medrxiv.org) was not tested. [미검증]

### Inferences
- **Easiest to add next (data.go.kr key already held, same pattern as DART and ALIO):** MFDS recalls and sales suspensions (15059114), safety letters (15059182), administrative sanctions (15058457), clinical trial approvals (15056835/15090589), drug approvals (15095677), and supply interruptions (15057899). These six can share one ServiceKey. One poll every 10–30 minutes uses only a few hundred of the 10,000 daily calls.
- The Assembly bill API works without a key and returns a reliable PROPOSE_DT and BILL_NO, which makes it a good **incremental monitor** keyed on BILL_NO.
- Since 정책브리핑 RSS ended, any RSS-based monitoring has to be replaced. Options: the 정책뉴스 API at 1,000/day (an operational account can be requested), or direct HTML scraping of each ministry's board.
- data.go.kr service names include a version suffix (06→07→08). When the suffix rises, the old version is retired with error code 12 (`NO_OPENAPI_SERVICE_ERROR`). The monitor needs an alarm for this error code and a periodic re-check of the latest version on the catalog page.
- Hospital opening and closure data (yadmOpCloInfoService2) can feed a new monitoring type, e.g. alerts on "지역 소아과/분만병원 폐업".

### Gaps
- MFDS press-release RSS, MOHW RSS, and NHIS, HIRA and KDCA board URLs and HTML structure could not be checked: the sites were unreachable from the sandbox.
- **We could not find the exact board URL or file format for the monthly 약제급여목록 file, or where 약평위 results are posted.**
- The lag between the "실시간" label on data.go.kr and the actual posting on the source site has not been measured.
- Service codes for Assembly minutes, 국정감사 and the broadcast service; official KoNECT and medRxiv APIs; whether the 정책뉴스 API includes press releases.
- Official docs for the ClinicalTrials.gov rate limit; the official general fee schedule for KIPRIS Plus.

---

## Q2. 의료전문지 기자에게 가장 가치 높은 "속보성" 아이템은 어느 정보원에서 나오나

### Takeaway
Ranking by how often trade outlets report each kind of item: MFDS clinical trial approvals and drug approvals, recalls and sales suspensions, and safety letters (all available by API); HIRA and MOHW reimbursement listings and price changes (notices and files); bills proposed in the Assembly's 보건복지위원회 (API); and FTC rebate sanctions (decision texts and press releases). Reimbursement decisions are the most valuable of these yet the hardest to automate.

### Cited Findings
- Clinical trial approval stories: daily round-ups such as "한미약품 오락솔 등 6건 임상계획 승인". — [데일리팜 208522](https://dailypharm.com/user/news/208522)
- Statistics on trial approvals are also a story type: in 2024 there were 664 pharma-sponsored trials, of which 305 were domestically developed. — [WebSearch summary: 의약일보 등](https://www.medicaldaily.co.kr/post/11180) (the figure was not checked in the original article)
- Reimbursement listings: monthly new-listing and delisting stories, plus "오늘부터 … 급여" stories. — [데일리팜 112505](https://dailypharm.com/user/news/112505); [데일리팜 72293](https://m.dailypharm.com/user/news/72293)
- Advance price files: HIRA publishes the draft file while the 건정심 deliberation is still under way. — [데일리팜 44526](https://dailypharm.com/user/news/44526)
- Rebate sanctions: FTC fines (e.g. "송년회 경품에 영화관 대관…공정위, 제약사 리베이트 제재"). — [데일리팜 335784](https://dailypharm.com/user/news/335784)
- Bills referred to 보건복지위원회 keep coming: in two days, 2026-11-11 and 2026-11-12, the bills included amendments to the 응급의료법 and 첨단재생바이오법, an amendment to the 화장품법, and a full rewrite of the AIDS prevention act. — [열린국회정보 API 실호출](https://open.assembly.go.kr/portal/openapi/nzmimeepazxkubdpn?Type=json&pIndex=1&pSize=3&AGE=22&COMMITTEE=%EB%B3%B4%EA%B1%B4%EB%B3%B5%EC%A7%80%EC%9C%84%EC%9B%90%ED%9A%8C)

### Inferences
- Suggested priority order:
  1. MFDS recalls, safety letters and sanctions (breaking news, APIs available)
  2. MFDS clinical trial approvals and drug approvals (daily round-ups, APIs available)
  3. Assembly 보건복지위 bills (API available)
  4. 입법예고 and 행정예고 (관보 API or 국민참여입법센터)
  5. HIRA hospital openings/closures and quality assessments (API)
  6. Reimbursement list and 약평위 results, MOHW, NHIS and KDCA press releases (HTML scraping)
  7. ClinicalTrials.gov Korean trials, FDA/EMA RSS, PubMed papers with Korean authors
- Like the existing DART and ALIO monitors, a classify-then-alert pipeline should key items on company names (listed pharma and bio firms) and on product or ingredient names. This lets one filter link a company across DART filings, MFDS approvals and trials, and reimbursement listings.

### Gaps
- No quantitative data on which source drives the most articles at 청년의사, 메디게이트, 히트뉴스 and others. Getting it would require a separate analysis of article samples.
- 학회 calendars and association press releases are not structured data. We found no automated source for them.

---

## Q3. 자동수집 관련 법적·약관상 제약

### Takeaway
Most MFDS APIs on data.go.kr carry "이용허락범위 제한 없음". HIRA, the KDCA infectious-disease API and the 정책뉴스 API carry 공공누리 Type 1 (attribution). **CRIS (임상연구 DB) carries Type 2, which bans commercial use**, so a commercial newspaper needs to review it. 정책브리핑 ended RSS for copyright reasons, which means bulk redistribution of the full text needs care. law.go.kr requires IP registration. openFDA gives no warranty under its terms.

### Cited Findings
- MFDS datasets (15059114, 15095677 and others): "이용허락범위 제한 없음". — [data.go.kr 15059114](https://www.data.go.kr/data/15059114/openapi.do)
- HIRA 약가기준 and 병원정보: "공공저작물 : 출처표시 (제 1유형)". — [data.go.kr 15054445](https://www.data.go.kr/data/15054445/openapi.do)
- KDCA 임상연구 DB (CRIS): "공공저작물 : 출처표시, 상업적 이용금지 (제 2유형)". — [data.go.kr 3033869](https://www.data.go.kr/data/3033869/openapi.do)
- 정책뉴스 API: 공공누리 Type 1. The RSS shutdown was attributed to "콘텐츠 저작권 등 권리 보호". — [data.go.kr 15095335](https://www.data.go.kr/data/15095335/openapi.do); [정책브리핑 공지](https://www.korea.kr/etc/noticeView.do?newsId=132038885)
- Traffic limits: development accounts get 10,000 calls/day; the KDCA infectious-disease API and the 정책뉴스 API get 1,000/day. — dataset pages above
- law.go.kr DRF: only a registered server IP or domain is allowed. 국민참여입법센터 likewise allows "신청한 IP에서만". — live call result; [국민참여입법센터 문답](https://opinion.lawmaking.go.kr/advc/stmInq/24173)
- openFDA: the meta field in every response has a disclaimer ("assume all results are unvalidated… may limit or otherwise restrict your access"). — [open.fda.gov/terms](https://open.fda.gov/terms/)
- The Assembly Open API has its own terms page (`/portal/policy/openUserAgreementPage.do`). We did not read the text. — [열린국회정보 데이터 페이지](https://open.assembly.go.kr/portal/data/service/selectServicePage.do/OK7XM1000938DS17215)
- KIND blocks automated access with Akamai (403). — live call result

### Inferences
- For internal alerts used as source material for reporting, Type 1 and "제한 없음" data pose little risk. Showing CRIS (Type 2) data verbatim in commercial articles or services needs separate review. Using it as an internal tip and then confirming against the registry is the cautious approach.
- Scraping HTML boards (MOHW, NHIS, HIRA): before relying on it, check robots.txt and each site's terms, and keep polling frequent but modest (e.g. every 5–10 minutes).
- If the app uses the 정책브리핑 API, store only titles and links, not full press-release text, for the alert. This stays clear of the copyright concern.

### Gaps
- We did not read the full text of the 열린국회정보, KIPRIS Plus or data.go.kr terms of use: provisions on commercial use, redistribution and caching.
- We could not check robots.txt for mfds.go.kr, hira.or.kr or nhis.or.kr, because the sites were unreachable from the sandbox.
