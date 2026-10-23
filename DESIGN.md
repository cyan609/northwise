# DESIGN.md – Look, feel and layout

Read this before changing any UI. Keep the code light: plain CSS variables, inline SVG, no heavy animation libraries.

## 1. Principles
1. **Trustworthy base, friendly frame.** Layout and colours feel like a reliable public service; tone, mascot and small interactions are warm and a little playful.
2. **Serious where it counts.** Answers, citations and disclaimers are calm and clean. No mascot, jokes or decoration inside the answer text.
3. **Map first.** The map fills the whole screen. Everything else floats over it.
4. **Plain words.** No jargon in the interface. Short sentences.
5. **Not an official site.** Never imitate government logos, emblems or colour schemes. Never use SDG logos or icons.

## 2. Colour tokens (define as CSS variables on :root)
| Token | Value | Use |
|---|---|---|
| --bg | #FAF8F3 | Page and panel background |
| --surface | #FFFFFF | Cards, answer cards |
| --text | #12343B | Main text |
| --text-muted | #4F6B70 | Secondary text |
| --primary | #1F7A6B | Buttons, links, headers |
| --accent | #F28C28 | Selected map region, key highlights |
| --water | #4DA8DA | Water and wetland topics |
| --notice | #FFF1C9 | Disclaimers and refusal notes |
| --border | #D9D4C7 | Card and input borders |

Text on --bg or --surface must meet WCAG AA contrast. Never rely on colour alone to show state.

## 3. Typography
- Traditional Chinese: Noto Sans TC (fallback: system sans-serif).
- English: Nunito (rounded, friendly), fallback system sans-serif.
- Body 16px minimum on phone. Headings 20–24px. Line height 1.5.

## 4. Shape and spacing
- Radius 12px for cards, 999px for pills and chips. Soft shadow: 0 2px 8px rgba(0,0,0,0.12).
- Spacing scale: 4, 8, 12, 16, 24. Tap targets at least 48x48px.

## 5. Layout
**Whole screen = map.** Overlays:
- **Top bar (small):** at the top of the map area (not covered by the chat panel). Product name and a small pill "Unofficial guide" (zh: 非官方指南). Language toggle (EN / 繁) on the right.
- **Report card:** appears when a map label is tapped. Phone: bottom sheet, about 40% height, draggable or closable. Computer: floating card at top-right, about 360px wide. Contains title, date, project area, links (original report, English and Chinese executive summaries) and a primary button "Ask about this report". If an executive summary is unavailable, show a muted "Not available" text in its place — never omit the row silently.
- **Spoonbill button:** bottom-right on phone, bottom-left on computer; 64px round button with the black-faced spoonbill. Has a small text label "Ask" (zh: 提問) and a speech bubble on first visit only: "Ask me about the reports!". Opens the chat panel.
- **Chat panel:** phone: bottom sheet covering about 75% of the screen, map still visible above. Computer: left-side panel, about 400px wide, pushing or overlaying the left part of the map. Closing it returns to the map with state kept.
- **Chat header:** spoonbill, title, and a scope chip showing "Asking about: [report name] ✕" or "All reports". Removing the chip switches to all reports.
- **Legend / note (small):** bottom-left on phone, bottom-right on computer. "Boundaries and report areas are indicative, not official."

## 6. Map style
- Light, low-saturation base map so colours stand out. Check the tile provider's terms and keep attribution visible.
- Districts: administrative context only. Light neutral outline, no fill; never filled to indicate a selected report. Do not draw, fill or label the union of the district polygons as the official Northern Metropolis boundary.
- Selected report: its `report_areas[]` get --accent fill (about 35% opacity) **and a solid 3px outline** (so it is visible to colour-blind users). Do not fill the whole district instead.
- `geometry_status: "indicative"`: draw the report-area polygon. `geometry_status: "point_fallback"`: draw a labelled point marker instead, with no polygon and no implied extent.
- Labels: pill-shaped sticker style (white background, --primary border, short text). Hand-placed so they do not overlap. Selected label turns --accent.

## 7. Components
- **Answer card:** white surface, short plain-language answer, then citation chips (report, chapter, page; each opens the original). A small line under every answer: "AI summary. The official report prevails." (zh: AI 整理的摘要，請以官方報告為準。) on --notice.
- **Citation chips:** open the original EPD file in a new tab at the cited page (add #page=N to the link where possible) and show "Source: EPD". If the report has no verified page numbers, the chip shows chapter + section only and omits the page. Never host, embed or let users download copies of the reports from this app. Show only short excerpts, never long passages.
- **Refusal card:** --notice background, no mascot joke. Text states clearly that the report does not cover it and suggests the nearest chapter and page.
- **Suggested questions and topic shortcuts:** pill buttons inside the chat panel, with simple icons (noise, ecology, water, air, landscape, waste, heritage).
- **Loading:** spoonbill "thinking" state plus a short line such as "Flipping through the report…".
- **Onboarding:** one dismissible 3-line card on first load: tap a label; read the card; ask the spoonbill.

## 8. Mascot: black-faced spoonbill
- Cute, chibi style, not realistic: round fluffy body, oversized head, big simple eyes, black face patch, short spatula-shaped bill (keep the spatula shape so it stays recognisable), small feet. Flat shapes, few colours (white, soft cream, black, one small warm accent), optional thin rounded outline. Draw from scratch as simple SVG; do not copy any existing organisation's logo.
- States: idle, thinking (loading), head-tilt (cannot find an answer), happy (answer given). Keep each as a small SVG variation.
- Use in: chat button, chat header, loading, empty and refusal states, onboarding. Do not use inside answer text.

## 9. Tone of voice (English / 繁體中文)
- Greeting: "Hi! Tap a spot on the map, or ask me about a report." / 「你好！點一下地圖上的位置，或直接問我報告內容。」
- Loading: "Flipping through the report…" / 「正在翻查報告…」
- Cannot find: "I couldn't find that in this report. The closest part is Chapter X, page Y." / 「這份報告沒有提到這點，最接近的是第 X 章第 Y 頁。」
- Top pill: "Unofficial guide" / 「非官方指南」
- Suggested questions use everyday wording, for example "Will construction noise affect homes nearby?" / 「施工噪音會影響附近住宅嗎？」

## 10. Accessibility rules
- Keyboard accessible; visible focus outline; labels on icon buttons.
- Respect prefers-reduced-motion: turn off bounce and pulse animations.
- Text zoom to 200% must not break layouts.
- Map regions have text equivalents: every report has a text map label carrying its name, and the selected report's card states its title, date and project area, so the highlighted area can be identified without reading the map shape.

## 11. Do not
- No SDG logos or icons, no government emblems or lookalike layouts.
- No mascot or humour in answer text or disclaimers.
- No autoplay motion, no heavy animation libraries, no large image assets.
