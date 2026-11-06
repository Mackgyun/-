# 디자인 원칙 (v3, 2026-11)

청년의사 브리핑 화면을 다시 설계하며 참고한 레퍼런스와, 실제로 적용한 결정을 정리합니다.

## 레퍼런스 분석

| 레퍼런스 | 핵심 | 적용 |
| --- | --- | --- |
| [Linear 2026 리프레시](https://linear.app/now/behind-the-latest-design-refresh) | "얻지 않은 주목을 다투지 않는다", "구조는 선이 아니라 느낌으로". 사이드바를 한 단계 어둡게, 구분선 축소 | 사이드바 배경을 본문과 구분, 목록은 구분선 없이 여백·배경으로 구분 |
| [Linear 패턴 분석](https://www.925studios.co/blog/linear-design-breakdown-saas-ui-2026) | 4px 격자, 명령 메뉴(Ctrl K), 점진적 노출(마우스 올림 → 펼침 → 상세), 즉시 반영, 스켈레톤 | 4px 간격 체계, 명령 팔레트, 행에 마우스를 올리면 동작 버튼, 확인 처리 즉시 반영, 불러오는 동안 스켈레톤 |
| [Superhuman](https://blakecrosley.com/guides/design/superhuman) | 키보드 분류(J/K, E, Z), 분류된 받은편지함, 5초 실행 취소, 색은 상태·포커스에만, 안 읽은 줄 왼쪽 막대 | J/K·E·C·O·D·Z 단축키, 미확인·중요·내 출입처·담당 미지정 분류, 실행 취소 토스트, 새 공시는 굵은 글씨 |
| [토스 라이팅 원칙](https://velog.io/@jbee/%ED%86%A0%EC%8A%A4%EC%9D%98-8%EA%B0%80%EC%A7%80-%EB%9D%BC%EC%9D%B4%ED%8C%85-%EC%9B%90%EC%B9%99%EB%93%A4) | 잡초 뽑기, 빈 문장 제거, 핵심 메시지 | 문구 원칙 문서(`ux-writing.md`) 참고 |
| Apple Liquid Glass·Material 3 Expressive ([비교](https://orangeloops.com/2025/12/liquid-glass-vs-material-3-expressive-next%e2%80%91gen-ui-design-compared)) | 반투명은 겹치면 읽기 어려움, 움직임은 체계로 | v3에서 반투명을 모두 없앰(아래 참고), 움직임은 짧은 페이드 한 가지 |
| [WCAG 2.2](https://www.w3.org/WAI/standards-guidelines/wcag/new-in-22/) | 포커스가 가려지지 않을 것(2.4.11), 터치 대상 24px 이상(2.5.8) | 화면을 덮던 하단 질문창 제거, scroll-padding으로 고정 머리말 아래 포커스 보장, 버튼 최소 28px(휴대폰 44px) |

## 레이아웃
- PC: 사이드바(236px) | 목록 | 상세(440px). 1240px 미만에서 상세는 오른쪽에서 겹쳐 열림
- 휴대폰(820px 미만): 하단 탭 5개(미확인, 중요, 질문, 담당, 메뉴), 상세는 전체 화면
- 미확인 화면 맨 위: 한 문장 요약, 숫자 한 줄(누르면 해당 목록), 정기 브리핑(접힘). 카드로 감싸지 않음

## 토큰
- 색: 흰 바탕 + 중립 회색 + 청년의사 남색(#0b4a8b) 한 가지. 빨강(중요)·호박색(일반)·초록(담당)은 상태 표시에만
- 글꼴: Pretendard Variable (SIL OFL, `static/fonts`), 크기 12·13·14·16·20·24
- 간격: 4·8·12·16·20·24·32px / 모서리 4·6·8px / 목록 한 줄 40px(촘촘 34px, 휴대폰 60px)
- 다크 모드: 시스템 설정을 따르고 설정에서 바꿀 수 있음
- 아이콘: 1.4px 선 SVG는 메뉴에만. 목록·명령 팔레트·링크에는 기호(▲●○✦↗★)를 쓰지 않고 글자로 표시
- 숫자: 접수번호는 고정폭 글꼴, 시각·금액은 숫자 폭 고정(tabular-nums)

## 단축키
J/K 이동 · Enter 열기 · E 확인 처리 · C 담당 · O 원문 · D 초안 · Z 실행 취소 · / 검색 · 1~6 목록 전환 · Ctrl K 또는 . 명령 팔레트 · Esc 닫기

## AI가 만든 티가 나는 화면 요소 걷어내기 (v3)

AI 코딩 도구가 만든 화면에 반복해서 나타나는 특징을 정리한 글들을 참고해, 이 앱에 있던 항목을 찾아 바꿨습니다.

| 흔한 특징 | 있던 곳 | 바꾼 것 |
| --- | --- | --- |
| 크림·베이지 계열 기본 배경 | 전체 바탕(#f7f7f5), 따뜻한 회색 | 흰 바탕, 중립 회색. 다크 모드도 중립 회색 |
| 반투명 유리(backdrop-filter) | 상단 머리말, 명령 팔레트, 휴대폰 하단 탭 | 모두 불투명 단색 |
| 알약 모양(완전히 둥근) 배지·버튼 | 오늘 요약 숫자, AI 질문 버튼, 설정의 태그, 질문 답변 도구 표시 | 4px 모서리 태그 또는 글자 링크 |
| 카드 안에 큰 숫자를 늘어놓는 요약 | 오늘 요약 카드 + 숫자 칩 5개 + 날짜 머리글 | 카드 없이 문장 한 줄과 "미확인 5 · 중요 3 …" 한 줄 |
| 제목 위 작은 머리글(eyebrow) | 상세 패널 제목 위 "▲ 중요 · DART" | 제목 아래 한 줄에 회사명·등급·출처 |
| 의미 없는 점·막대 장식 | 안 읽은 줄 왼쪽 파란 막대, 처리 이력 타임라인 점 | 안 읽은 줄은 굵은 글씨, 처리 이력은 수집·담당·기사화 항목 표 |
| 장식용 기호 아이콘 | 등급 ▲●○, AI ✦, 외부 링크 ↗, 감시 기업 ★ | 글자(중요·일반·기록), 링크는 밑줄 |
| 큰 둥근 모서리 + 큰 그림자 | 말풍선 14px(한쪽만 각진 모양), 팔레트 14px, 로그인 16px | 모서리 4·6·8px, 그림자는 떠 있는 층에만 작게 |
| 반짝이는 로딩 효과 | 스켈레톤 shimmer 애니메이션 | 움직이지 않는 회색 칸 |
| 튀어나오는 등장 효과 | 팔레트·토스트 확대 애니메이션 | 짧은 페이드 |

유지한 것: 상태 점(수집 정상·오류를 실제로 나타냄), 사이드바 SVG 아이콘, Pretendard 글꼴(Inter 기본값이 아님), 남색 한 가지 강조색(보라·그라데이션 없음).

참고한 글
- [Impeccable: AI slop 목록](https://www.impeccable.style/slop)
- [The Fountain Institute: 바이브 코딩 UI의 7가지 신호](https://www.thefountaininstitute.com/blog/signs-vibe-coded-ui)
- [925studios: AI slop design tells](https://www.925studios.co/blog/ai-slop-design-tells)
- [Mania Design: Spot the slop](https://www.mania.design/blog/spot-the-slop-a-ui-designers-guide-to-fixing-ai-defaults/)
- [The purple gradient problem](https://medium.com/@infoinletdev.five/the-purple-gradient-problem-why-ai-ui-all-looks-alike-and-how-to-fix-it-0c995c5c5c79)
- [Why every AI-built website looks the same (Tailwind indigo-500)](https://dev.to/alanwest/why-every-ai-built-website-looks-the-same-blame-tailwinds-indigo-500-3h2p)
- [vibecodekit: AI slop design](https://vibecodekit.dev/ai-slop-design), [smoothui: AI design slop](https://smoothui.dev/blog/ai-design-slop)
- [avoid-ai-design](https://github.com/funboy322/avoid-ai-design), [You don't have to make AI slop](https://matthewblode.com/blog/you-dont-have-to-make-ai-slop)
