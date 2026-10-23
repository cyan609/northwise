# NORTHWISE — Draggable & Resizable Chat Window

## Files changed

| File | Change |
|------|--------|
| `static/index.html` | Only file modified. CSS for the floating window, resize handles and responsive layout; header markup for Minimize / Maximize / Restore / Close; ~330 lines of pointer-event and geometry JavaScript. |

No backend, retrieval, citation, language, or map logic was touched. No dependencies added.

## How to use it

### Drag
- Press and hold the **title bar** ("Ask the reports") and move the mouse.
- Dragging never starts from the message area, the text box, buttons, links, the scope chip, or a resize handle.
- The window is clamped so it can never leave the viewport, and it always stays below the top bar so the title bar remains reachable.

### Resize
- Drag any **edge** (top, bottom, left, right) or **corner** (four corners) of the window.
- Minimum size is **320 × 300 px**. Maximum is the viewport minus margins.
- Dragging the left or top edge keeps the opposite edge anchored.
- The message list scrolls on its own (`overflow-y:auto`); the header and the input row never scroll away.

### Window controls (top-right of the title bar)
| Control | Behaviour |
|---------|-----------|
| **–** Minimize | Collapses to the title bar only. The bar stays where the window was; click it (or the ❐ button) to reopen. |
| **□** Maximize | Fills the viewport below the top bar. |
| **❐** Restore | Appears only when minimized or maximized; returns to the previous size and position. |
| **×** Close | Hides the window. The floating 💬 button reopens it in full. |

The conversation is held in the existing `conversation[]` array, so resizing, dragging, minimizing, maximizing, restoring, and closing never lose messages.

### Keyboard
- `Tab` to the title bar (it is focusable) or to any control button.
- **Arrow keys** move the window by 16 px (`Alt`+arrow = 4 px).
- **Shift + Arrow keys** resize the window.
- `Enter` / `Space` on a minimized title bar restores it.
- All controls are real `<button>` elements with `aria-label` values that switch between English and Traditional Chinese with the language toggle.

### Mobile / narrow screens (≤ 720 px)
- Free dragging and resizing are disabled; the window docks to the bottom of the screen as a full-width sheet (72 vh, capped at 640 px).
- Resize handles and the maximize button are hidden; minimize/restore and close still work.
- Rotating or resizing back to desktop width restores the free-floating layout.

## Implementation notes

- `position: fixed` with JS-driven `left/top/width/height`; a single `clampChatGeom()` enforces all viewport and minimum-size rules for drag, resize, maximize, restore, and window resize.
- Pointer Events with `setPointerCapture`, so a fast drag that crosses the map still tracks correctly and never reaches Leaflet. Verified: the map centre is unchanged after dragging the window across it, and the map still pans afterwards.
- Eight resize handles are absolutely positioned **inside** the panel (the panel uses `overflow:hidden`), so they are never clipped; corners are 18 × 18 px to stay clickable inside the 12 px border radius.
- `body.chat-window-active` disables text selection during drag/resize.
- The `[hidden]` attribute needed an explicit `display:none` rule because `display:inline-flex` otherwise overrides it.

## Verification

Automated in headless Chrome (Chrome DevTools Protocol, real pointer events), **34/34 checks passed**:

- drag moves the window and preserves size
- drag beyond the left/top edge clamps to `left=8`, `top=58`
- SE-corner resize grows width/height; W-edge resize narrows while the right edge stays fixed
- resizing below the minimum clamps to 320 × 300; resizing beyond the viewport clamps inside it
- minimize collapses to a 48 px bar, hides the message area, exposes Restore
- restore returns the exact previous geometry; conversation survives
- maximize fills the viewport (1264 × 747 at 1280 × 813) and stays inside it
- restore from maximize returns to the prior size
- message list scrolls independently; the input row stays inside the panel
- pressing a header button does not drag the window
- map does not pan while dragging the window; map remains interactive afterwards
- mobile: fits 390 px screen, resize handles and maximize hidden
- desktop layout returns after leaving mobile width
- keyboard move/resize/restore and localized `aria-label`s work

Screenshots: `screenshots/chat-window-desktop.png`, `screenshots/chat-window-minimized.png`, `screenshots/chat-window-mobile.png`.

### Pre-existing console noise (not introduced here)
`GET /stage0/source-data/boundaries/hksar_18_district_boundary.json` and `/favicon.ico` return 404 because the stdlib server only serves `/`, `/reports` and `/ask`. The district layer fetch is already wrapped in `try/catch`; neither affects the chat window.
