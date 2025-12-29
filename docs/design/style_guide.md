# DAT Design Style Guide (Draft)

## Introduction
This is a concise, implementation-focused style guide for the Daily Activity Tracker (DAT). The goal is a clean, modern, professional UI with both **light** and **dark** themes, strong accessibility, and components that are easy to extend.

---

## 1. Design tokens
Use CSS variables (custom properties) and/or SASS variables for tokenization.

Color tokens (light):
- --bg: #FFFFFF
- --surface: #F8FAFC
- --text-primary: #0F1724
- --text-muted: #6B7280
- --accent: #0EA5A4
- --success: #16A34A
- --danger: #DC2626
- --border: #E6EAF0

Color tokens (dark):
- --bg: #0B1220
- --surface: #0F1724
- --text-primary: #E6EEF3
- --text-muted: #9CA3AF
- --accent: #4FD1C5
- --success: #34D399
- --danger: #F87171
- --border: #1F2937

Spacing scale (base 8px):
- 0, 4px, 8px, 12px, 16px, 24px, 32px, 40px

Typography
- Primary font: system stack or Inter/Roboto, fallback to system UI
- Scale: 12 (xs), 14 (sm), 16 (base), 20 (lg), 24 (xl), 32 (xxl)
- Headings: use consistent weights and margin spacing

Shadows & elevation
- soft card shadow: 0 6px 18px rgba(2, 6, 23, 0.08)
- dense shadow for emphasis: 0 10px 30px rgba(2, 6, 23, 0.12)

Border radius
- components: 8px
- chips/buttons: 6px

---

## 2. Component guidelines (summary)
- Topbar: compact, 56px height, includes theme toggle & user menu
- Sidebar: collapsible; use icon-only collapsed mode; smooth transitions; vertical scroll independent from content
- Cards: use `--surface`, soft shadow, padding scale 16px
- Tables: compact by default with optional denser mode; sticky header; zebra rows; readable fonts; cell truncation fallback with full content on hover
- Buttons: primary (accent), secondary (outline), small variants for table actions

Accessibility
- Aim for WCAG AA color contrast (4.5:1 for body text)
- Visible focus outlines for keyboard nav
- aria-labels for icon-only buttons

---

## 3. Theme behavior
- Default respects `prefers-color-scheme` unless user explicitly chooses theme via toggle
- Persist user choice in localStorage `theme = 'light'|'dark'`
- Provide utility CSS class `data-theme="dark"` for server-side rendering or testing

---

## 4. Implementation notes
- Add `css/design/theme.css` with variable sets and minimal helper classes
- Add `js/theme.js` for toggle and persistence
- Prefer small, incremental visual updates (update tokens first, then components)

---

## 5. Mockups included
- Dashboard: overview with activity table and compact cards
- Team Activities: team table list with controls
- Activity row: focus on compact row with actions

---

## 6. Next steps
1. Convert tokens into SASS variables and integrate into `app/static/css/`.
2. Implement a theme toggle in topbar and persist preference.
3. Restyle components progressively and add visual regression tests.

Feedback? Reply with any color or typography preferences and I will iterate the mockups.