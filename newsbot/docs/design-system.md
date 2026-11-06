# 디자인 원칙 (v2, 2026-11)

청년의사 브리핑 화면을 다시 설계하며 참고한 레퍼런스와, 실제로 적용한 결정을 정리합니다.

## 레퍼런스 분석

| 레퍼런스 | 핵심 | 적용 |
| --- | --- | --- |
| [Linear 2026 리프레시](https://linear.app/now/behind-the-latest-design-refresh) | "얻지 않은 주목을 다투지 않는다", "구조는 선이 아니라 느낌으로". 사이드바를 한 단계 어둡게, 구분선 축소, 따뜻한 회색 | 사이드바 배경을 본문보다 어둡게, 목록은 구분선 없이 여백·배경으로 구분, 회색 계열을 따뜻하게 |
| [Linear 패턴 분석](https://www.925studios.co/blog/linear-design-breakdown-saas-ui-2026) | 4px 격자, 명령 메뉴(Ctrl K), 점진적 노출(마우스 올림 → 펼침 → 상세), 즉시 반영, 스켈레톤 | 4px 간격 체계, 명령 팔레트, 행에 마우스를 올리면 동작 버튼, 확인 처리 즉시 반영, 불러오는 동안 스켈레톤 |
| [Superhuman](https://blakecrosley.com/guides/design/superhuman) | 키보드 분류(J/K, E, Z), 분류된 받은편지함, 5초 실행 취소, 색은 상태·포커스에만, 안 읽은 줄 왼쪽 막대 | J/K·E·C·O·D·Z 단축키, 미확인·중요·내 출입처·담당 미지정 분류, 실행 취소 토스트, 새 공시 왼쪽 막대 |
| [토스 라이팅 원칙](https://velog.io/@jbee/%ED%86%A0%EC%8A%A4%EC%9D%98-8%EA%B0%80%EC%A7%80-%EB%9D%BC%EC%9D%B4%ED%8C%85-%EC%9B%90%EC%B9%99%EB%93%A4) | 잡초 뽑기, 빈 문장 제거, 핵심 메시지 | 문구 원칙 문서(`ux-writing.md`) 참고 |
| Apple Liquid Glass·Material 3 Expressive ([비교](https://orangeloops.com/2025/12/liquid-glass-vs-material-3-expressive-next%e2%80%91gen-ui-design-compared)) | 반투명은 겹치면 읽기 어려움, 움직임은 체계로 | 반투명은 상단 머리말·명령 팔레트·하단 탭에만, 움직임은 150~200ms 한 가지 곡선 |
| [WCAG 2.2](https://www.w3.org/WAI/standards-guidelines/wcag/new-in-22/) | 포커스가 가려지지 않을 것(2.4.11), 터치 대상 24px 이상(2.5.8) | 화면을 덮던 하단 질문창 제거, scroll-padding으로 고정 머리말 아래 포커스 보장, 버튼 최소 28px(휴대폰 44px) |

## 레이아웃
- PC: 사이드바(236px) | 목록 | 상세(440px). 1240px 미만에서 상세는 오른쪽에서 겹쳐 열림
- 휴대폰(820px 미만): 하단 탭 5개(미확인, 중요, 질문, 담당, 메뉴), 상세는 전체 화면
- 미확인 화면 맨 위: 날짜, 한 문장 요약, 숫자 칩, 정기 브리핑(접힘)

## 토큰
- 색: 따뜻한 회색 + 청년의사 남색(#0b4a8b) 한 가지. 빨강(중요)·호박색(일반)·초록(담당)은 상태 표시에만
- 글꼴: Pretendard Variable (SIL OFL, `static/fonts`), 크기 12·13·14·16·20·24
- 간격: 4·8·12·16·20·24·32px / 모서리 6·8·12px / 목록 한 줄 40px(촘촘 34px, 휴대폰 60px)
- 다크 모드: 시스템 설정을 따르고 설정에서 바꿀 수 있음
- 아이콘: 1.4px 선 SVG (장식 기호 대신)

## 단축키
J/K 이동 · Enter 열기 · E 확인 처리 · C 담당 · O 원문 · D 초안 · Z 실행 취소 · / 검색 · 1~6 목록 전환 · Ctrl K 또는 . 명령 팔레트 · Esc 닫기
