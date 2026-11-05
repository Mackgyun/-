# newsbot — 청년의사 편집국 브리핑 봇 (작성 중)

DART·알리오·보도자료 메일을 24시간 확인해 텔레그램으로 알리는 봇입니다. 현재 1단계(DART → 텔레그램) 코드를 작성하는 중입니다.

## 폴더 안내
- `review/plan.md` — 회사 제안 기획서 (Claude Docs 기획서와 같은 내용)
- `review/step1_design.md` — 1단계 코드 설계
- `review/codex_review_prompt.md` — Codex(ChatGPT)에 그대로 붙여넣는 교차검증 요청문 (기획서·설계·코드 포함)
- `config/rules.toml` — 공시 중요도 규칙 (키워드, 보건의료 업종코드)
- `newsbot/` — 봇 코드 (config.py, rules.py까지 작성됨)

## 현재 상태
- [x] 설정 로딩, 중요도 규칙
- [ ] DART 수집기, DB, 텔레그램 봇, Windows 자동 시작, Docker
