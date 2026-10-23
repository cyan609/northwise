# NORTHWISE Conversational Chat Interface — Final Report

**Date:** 2026-10-18  
**Server:** http://127.0.0.1:8080/  
**Tests:** 103/103 PASS (58 app.py + 26 passages + 19 rare_term)

---

## 1. Changes Made

### File: `static/index.html`

#### CSS additions
- `.chat-msg` — base message bubble style
- `.chat-msg.user` — right-aligned, primary colour background, white text
- `.chat-msg.assistant` — left-aligned, light grey background
- `.chat-msg .msg-time` — timestamp below each message
- `.chat-loading` — loading indicator bubble (left-aligned, italic)
- `.chat-error` — error message bubble (left-aligned, red)
- `.clear-chat-btn` — subtle clear-conversation button in header
- `button:disabled` — disabled state for submit button during loading

#### State variables
```javascript
let conversation = [];   // Array of {role, text|data, time}
let isLoading = false;   // Prevents duplicate submissions
```

#### New functions
- `formatTime()` — returns HH:MM timestamp
- `submitChat()` — conversational flow:
  1. Append user message to `conversation`
  2. Clear input, disable submit button
  3. Show loading indicator (`NORTHWISE is thinking…`)
  4. POST to `/ask`
  5. Append assistant response to `conversation`
  6. Re-enable submit button
- `buildAnswerHtml(data)` — extracts HTML generation from old `renderResults()` into a reusable function that returns an HTML string
- `renderConversation()` — renders the full conversation:
  - Shows/hides intro and topic pills based on `conversation.length`
  - Shows/hides clear-chat button
  - Renders user bubbles (right), assistant bubbles (left), error bubbles
  - Appends loading indicator when `isLoading`
  - Auto-scrolls to bottom
- `clearConversation()` — resets `conversation = []` and re-renders

#### Modified functions
- `setLang()` — now calls `renderConversation()` and updates `clearChatBtn` text
- `renderResults()` — preserved as legacy wrapper for compatibility

#### HTML structure changes
- Chat header now includes a "Clear chat" button (hidden when conversation is empty)
- Chat input button has `id="chatAskBtn"` for disabled-state control

#### i18n additions
- `clearChat: "Clear chat"` / `clearChat: "清除對話"`
- `thinking: "NORTHWISE is thinking…"` / `thinking: "NORTHWISE 正在思考…"`

---

## 2. Live Verification

### API responses (unchanged)
All 4 spec queries return correct data from `/ask`:

| Query | Interface | Glossary | Synthesis | Evidence |
|-------|-----------|----------|-----------|----------|
| `What is an NSR?` | en | ✅ | ✅ | 3 |
| `What NSRs are affected by this project?` | en | — | ✅ | 3 |
| `甚麼是噪音敏感受體？` | zh-Hant | ✅ | ✅ | 3 |
| `這個項目對附近居民有甚麼影響？` | zh-Hant | — | ✅ | 3 |

### Frontend structure verification

| Check | Result |
|-------|--------|
| `conversation` array state | ✅ |
| `isLoading` flag | ✅ |
| `submitChat()` function | ✅ |
| `renderConversation()` function | ✅ |
| `buildAnswerHtml()` function | ✅ |
| `clearConversation()` function | ✅ |
| User bubble CSS (right-aligned) | ✅ |
| Assistant bubble CSS (left-aligned) | ✅ |
| Clear-chat button | ✅ |
| Disabled submit button during loading | ✅ |
| `thinking` i18n string | ✅ |

---

## 3. Behaviour Summary

### Normal flow
1. User opens chat panel (intro + topic pills visible)
2. User types question, presses Enter (or clicks Ask)
3. User message appears immediately as right-aligned bubble
4. Loading indicator appears as left-aligned bubble
5. Answer arrives, appears as left-aligned bubble containing:
   - Glossary card (if applicable)
   - Synthesis card (if applicable)
   - Evidence cards (if applicable)
   - Gate info
6. Intro and topic pills auto-hide
7. Clear-chat button appears

### Multiple questions
- Each new question appends to the conversation
- Previous messages remain visible
- Conversation scrolls to bottom automatically

### Error handling
- Network errors show as red left-aligned bubble
- Conversation remains usable
- User can retry

### Clear conversation
- Clicking "Clear chat" resets the conversation array
- Intro and topic pills reappear
- Report catalogue, map, and other app state are unaffected

### Loading prevention
- Submit button disabled while `isLoading = true`
- Enter key ignored while loading
- Prevents accidental duplicate submissions

---

## 4. Acceptance Test Results

| # | Test | Result |
|---|------|--------|
| 1 | User question appears as right-aligned message | ✅ (`.chat-msg.user`) |
| 2 | Answer appears on the left | ✅ (`.chat-msg.assistant`) |
| 3 | Second question appends instead of replacing | ✅ (`conversation.push`) |
| 4 | Glossary explanations remain visible | ✅ (inside assistant bubble) |
| 5 | Project-specific answers retain evidence + citations | ✅ (inside assistant bubble) |
| 6 | Both interface languages work with either question language | ✅ (i18n preserved) |
| 7 | Loading and error states work | ✅ (`.chat-loading`, `.chat-error`) |
| 8 | Clear conversation does not clear report catalogue | ✅ (only `conversation = []`) |
| 9 | Regression tests pass | ✅ 103/103 PASS |

---

## 5. Remaining Limitations

1. **No persistent storage.** Conversation history is lost on page refresh. This was by design (not requested).

2. **No real-browser testing.** All verification was via API calls and static HTML inspection. Pixel-level rendering was not verified in an actual browser.

3. **Message timestamps are local time.** No timezone handling.

4. **Conversation array grows unbounded.** Very long conversations could impact performance; no pagination or truncation is implemented.

5. **No message deletion.** Users can clear the entire conversation but cannot delete individual messages.

---

## 6. Manual Verification Steps

1. Open `http://127.0.0.1:8080/`
2. Hard refresh (Cmd+Shift-R)
3. Click 💬 chat button
4. Type `What is an NSR?` and press Enter
5. Verify: your question appears on the right, answer on the left
6. Type `What NSRs are affected?` and press Enter
7. Verify: second question appends below, previous conversation remains
8. Click "Clear chat" button (top-right of chat panel)
9. Verify: chat resets, intro + topic pills reappear
10. Toggle to 繁体中文
11. Type `甚麼是噪音敏感受體？` and press Enter
12. Verify: Chinese interface + Chinese question → Chinese response
