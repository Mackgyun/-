# 클립 요청 프롬프트 템플릿

클립 폴더를 만들고 폰트와 GSAP을 `assets/`에 복사한 뒤, 아래를 채워서 요청한다.

```bash
mkdir -p clip-NN/assets
cp assets/fonts/GmarketSansTTFBold.ttf assets/fonts/GmarketSansTTFMedium.ttf \
   assets/vendor/gsap-3.14.2.min.js clip-NN/assets/
```

```
clip-NN/index.html에 모션그래픽 컴포지션을 만들어줘.

[클립 정보]
- 문장: "<대본 문장>"   ← 화면에 이 문장을 쓰면 안 됨
- 컨셉: <카드형 / 숫자 카운터 / 게이지 / 아이콘 배치 / 스탬프 판정 / 타임라인>
- 화면 텍스트: "<자막에 없는 새 단어 1~3개>"  (없으면 "글자 없이")
- 길이: <N.N>초
- 캔버스: <1080x1920 | 1080x1080 | 1080x960>
- 워시: <번호>번 <이름>   ← references/washes.md 참고

[꼭 지킬 규칙]
1. html/body를 캔버스 크기로 고정하고 루트 div에
   data-composition-id, data-width, data-height, data-duration을 넣어줘.
2. GSAP 타임라인은 paused 상태로 정확히 1개, window.__timelines["clipNN"]에 등록.
3. 폰트는 assets/GmarketSansTTFBold.ttf를 @font-face로 선언.
   GSAP은 assets/gsap-3.14.2.min.js 로컬 사본을 참조해줘 (CDN 금지).
4. 배경은 루트가 아니라 absolute로 깐 자식 div에 칠해줘.
5. 애니메이션 최종 상태는 data-duration보다 0.1초쯤 앞에서 끝내줘.
6. 무한 반복 애니메이션과 Math.random() 금지.
7. 모든 경로는 assets/ 같은 상대경로로.
8. 캔버스 밖으로 흘리는 블롭이 있으면 그 클립에
   data-layout-allow-overflow를 붙여줘.

다 쓰면 npx hyperframes check --snapshots 까지 돌려서 통과시켜줘.
```

## 계획표 요청 (대본 전체를 한 번에)

```
아래 대본을 문장별로 나눠서 표로 만들어줘.
번호 · 문장 · 길이(초) · 캔버스 · 워시 번호 · 컨셉 6열로.

- SRT가 있으면 그 타이밍을 그대로 써줘.
- 없으면 문장당 2~3초.
- 눈길 끄는 문장과 도구 이름이 나오는 문장은 full, 부연 설명은 square.
- 이웃한 클립은 워시와 컨셉이 겹치지 않게.
- 화면 조작을 설명하는 문장은 "화면녹화 대체"로 표시하고 클립을 만들지 마.

[대본]
```
