# LintPDF Dashboard Style Guide — Complete Reference

> **Purpose:** Complete styling reference for Pixie Dust theme customization. Every color, spacing, border, font, and component pattern extracted from LintPDF's pre-migration dashboard (commit `79bdb5e`).
>
> **Known Pixie Dust Issues:**
> 1. `LoginPage` renders broken logo image — uses wrong default path, should use `getBranding().brandLogoUrl`
> 2. Shows "AtlasMCP" instead of app name — should use `getBranding().brandName`
> 3. Default purple/dark theme doesn't match downstream apps — needs theme override system

---

## 1. CSS Theme Variables

### Light Mode (`:root`)

```css
--background: 0 0% 100%;
--foreground: 220 30% 10%;
--card: 0 0% 100%;
--card-foreground: 220 30% 10%;
--popover: 0 0% 100%;
--popover-foreground: 220 30% 10%;
--primary: 224 69% 40%;
--primary-foreground: 0 0% 100%;
--secondary: 200 20% 96%;
--secondary-foreground: 224 76% 33%;
--muted: 200 20% 96%;
--muted-foreground: 210 9% 46%;
--accent: 217 91% 60%;
--accent-foreground: 224 76% 33%;
--destructive: 0 84% 60%;
--destructive-foreground: 0 0% 98%;
--border: 210 13% 91%;
--input: 210 13% 91%;
--ring: 224 69% 40%;
--radius: 0.5rem;
```

### Dark Mode (`.dark`)

```css
--background: 220 20% 5%;
--foreground: 0 0% 98%;
--card: 220 20% 5%;
--card-foreground: 0 0% 98%;
--popover: 220 20% 5%;
--popover-foreground: 0 0% 98%;
--primary: 224 69% 40%;
--primary-foreground: 0 0% 100%;
--secondary: 220 14% 14%;
--secondary-foreground: 0 0% 98%;
--muted: 220 14% 14%;
--muted-foreground: 210 9% 65%;
--accent: 217 91% 60%;
--accent-foreground: 0 0% 98%;
--destructive: 0 63% 31%;
--destructive-foreground: 0 0% 98%;
--border: 220 14% 14%;
--input: 220 14% 14%;
--ring: 224 69% 40%;
```

### Brand Palette

```css
--color-brand-50:  #eff6ff;
--color-brand-100: #dbeafe;
--color-brand-200: #bfdbfe;
--color-brand-300: #93c5fd;
--color-brand-400: #60a5fa;
--color-brand-500: #3b82f6;
--color-brand-600: #2563eb;
--color-brand-700: #1d4ed8;
--color-brand-800: #1e40af;
--color-brand-900: #1e3a8a;
--color-brand-950: #172554;
```

### Radius Scale

```css
--radius-sm: 4px;
--radius-md: 8px;
--radius-lg: 12px;
--radius-xl: 16px;
```

### Font Stack

```css
--font-sans: var(--font-inter), system-ui, -apple-system, sans-serif;
--font-mono: var(--font-jetbrains-mono), "Fira Code", ui-monospace, monospace;
```

Fonts: Inter (variable, swap) + JetBrains Mono (variable, swap) via Google Fonts.

---

## 2. Page Layout

### Root Body
```
min-h-screen bg-background font-sans antialiased
```

### Dashboard Pages
```
main: p-8 max-w-5xl     (standard pages: preflight, reports)
main: p-8 max-w-4xl     (settings: billing, account, team, api-keys, webhooks, usage, health)
main: p-8 max-w-6xl     (wide tables: admin/tenants, admin/jobs, admin/trials)
main: p-8 max-w-2xl     (narrow forms: profile, appearance)
main: p-8               (minimal: waitlist)
```

### Page Header Pattern
```
div: flex items-center justify-between
  h1: font-display text-2xl font-bold
  p:  mt-1 text-sm text-muted-foreground
  [optional primary action button on right]
```

### Section Spacing
```
mt-6  between major sections
mt-4  between sub-sections / after error messages
mt-3  between form fields within a section
mt-2  between tightly related elements
mt-1  between label and input
```

### Login Page
```
main: flex min-h-screen items-center justify-center bg-white p-4
background: pointer-events-none fixed inset-0 bg-gradient-to-b from-white via-brand-50/30 to-white
wrapper: relative z-10 w-full max-w-[420px]
logo: mb-8 flex flex-col items-center gap-3
  img: h-12 w-12
  span: text-xl font-semibold tracking-tight text-brand-900
card: rounded-2xl border border-slate-200/60 bg-white p-8 shadow-lg shadow-brand-900/5
title: text-[22px] font-bold tracking-tight text-slate-900
subtitle: mt-2 text-sm leading-relaxed text-slate-500
footer: mt-6 text-center text-xs text-slate-400
```

---

## 3. Buttons

### Primary (main actions)
```
rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50
```

### Primary Full-Width (login page)
```
w-full rounded-lg bg-brand-900 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-brand-800 disabled:cursor-not-allowed disabled:opacity-50
```

### Secondary (alternatives, cancel)
```
rounded-md border px-4 py-2 text-sm hover:bg-muted
```

### Small (table actions, inline)
```
rounded border px-2 py-1 text-xs hover:bg-muted
```

### Small Destructive (delete, revoke)
```
rounded border border-destructive/30 px-2 py-1 text-xs text-destructive hover:bg-destructive/10
```

### Pagination
```
rounded border px-3 py-1 text-sm disabled:opacity-50
```

### Admin Toolbar (violet)
```
rounded bg-violet-600 px-2 py-1 text-xs font-medium text-white hover:bg-violet-500
rounded bg-violet-500 px-3 py-1 text-xs font-medium hover:bg-violet-400
```

### Filter Toggles
```
active:   rounded px-2 py-1 text-xs font-medium transition-colors bg-foreground text-background
inactive: rounded px-2 py-1 text-xs font-medium transition-colors bg-muted text-muted-foreground hover:bg-muted/80
```

---

## 4. Form Inputs

### Standard Text/Email Input
```
mt-1 w-full rounded-md border px-3 py-2 text-sm
```

### Login Page Input (detailed)
```
mt-1 block w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm placeholder:text-slate-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500
```

### 6-Digit Code Input
```
h-12 w-10 rounded-lg border border-slate-200 bg-white text-center text-lg font-semibold text-slate-900 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500
```

### Select Dropdown
```
block w-full rounded border bg-background px-2 py-1.5 text-sm
```
or
```
rounded-md border px-3 py-2 text-sm
```

### File Input
```
block w-full text-sm file:mr-3 file:rounded file:border-0 file:bg-primary/10 file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-primary hover:file:bg-primary/20
```

### Color Picker
```
input[type=color]: h-9 w-12 rounded border
paired with: text input for hex value
```

### Search Input (toolbar)
```
w-full rounded border px-2 py-1.5 text-sm text-gray-900
```

### Labels
```
block text-sm font-medium text-slate-700    (login page)
block text-sm font-medium                   (dashboard forms)
block text-xs font-medium text-muted-foreground mb-1  (upload form)
```

### Help Text
```
mt-0.5 text-xs text-muted-foreground
```

---

## 5. Cards & Containers

### Standard Card
```
rounded-lg border bg-card p-4
rounded-lg border p-4
```

### Section Card
```
rounded-lg border p-4 space-y-4
rounded-lg border bg-card p-4 space-y-4
```

### Large Card (login)
```
rounded-2xl border border-slate-200/60 bg-white p-8 shadow-lg shadow-brand-900/5
```

### Highlighted Card (selected/current)
```
rounded-lg border p-3 border-primary bg-primary/5
```

### Empty State
```
rounded-lg border border-dashed p-8 text-center text-muted-foreground
```

### Pending/Invite Item
```
rounded-lg border border-dashed p-3
```

### Collapsible Card
```
rounded-lg border bg-card overflow-hidden
```

### Feature Card (admin hub, brands)
```
rounded-lg border p-4 hover:bg-muted/50 transition-colors
```

### Accent Feature Card
```
rounded-lg border border-brand-200 bg-brand-50/30 p-4 hover:bg-brand-50/60 transition-colors
```

---

## 6. Badges & Status Indicators

### Status Badge Base
```
rounded px-1.5 py-0.5 text-xs font-medium
```

### Status Colors
```
pending:    bg-yellow-100 text-yellow-700
processing: bg-blue-100 text-blue-700
complete:   bg-green-100 text-green-700
failed:     bg-red-100 text-red-700
active:     bg-green-100 text-green-700
contacted:  bg-purple-100 text-purple-700
```

### Role/Tag Badge
```
rounded bg-muted px-1.5 py-0.5 text-xs
```

### Admin Badge
```
rounded bg-violet-500 px-2 py-0.5 text-xs font-bold
```

### Super Admin Info Badge
```
rounded bg-violet-50 px-3 py-2 text-sm text-violet-700
```

### Status Dots
```
active: inline-block h-2 w-2 rounded-full bg-green-500
large:  inline-block h-3 w-3 rounded-full bg-green-500  (or bg-red-500)
```

---

## 7. Alert & Message Patterns

### Error (destructive)
```
mt-4 rounded-md bg-destructive/10 p-3 text-sm text-destructive
  [optional dismiss: button.className = "ml-2 underline"]
```

### Success
```
mt-4 rounded-md bg-green-50 p-3 text-sm text-green-700
```
or
```
rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-center
  p: text-sm font-medium text-emerald-700
```

### Error (login)
```
rounded-lg border border-red-200 bg-red-50 p-3
  p: text-sm text-red-700
```

### New Key Banner
```
rounded-md border border-green-200 bg-green-50 p-4
  p: text-sm font-medium text-green-800
  code: flex-1 rounded bg-white px-3 py-2 text-sm font-mono
```

### Test Result
```
mt-2 rounded px-2 py-1 text-xs bg-green-50 text-green-700
```

### Inline Success Text
```
text-sm text-green-600
```

---

## 8. Tables

### Table Structure
```
container: mt-6 overflow-x-auto
table: w-full text-sm
thead tr: border-b text-left text-muted-foreground
th: pb-2 font-medium
tbody tr: border-b  (last:border-0)
td: py-2
td (name): py-2 font-medium
td (code): py-2 text-xs
td (actions): py-2 text-right
```

### Table Links
```
font-medium hover:underline
text-primary hover:underline
```

### Inline Code
```
code: text-xs text-muted-foreground
```

---

## 9. Pagination

```
container: mt-4 flex items-center justify-between
prev/next: rounded border px-3 py-1 text-sm disabled:opacity-50
info: text-sm text-muted-foreground
```

---

## 10. List Item Patterns

### Member Row
```
container: flex items-center justify-between rounded-lg border p-3
avatar: flex h-8 w-8 items-center justify-center rounded-full bg-muted text-xs font-medium
name: font-medium
email: text-xs text-muted-foreground
role select: rounded border px-2 py-1 text-xs
remove btn: rounded border border-destructive/30 px-2 py-1 text-xs text-destructive hover:bg-destructive/10
```

### API Key Row
```
container: flex items-center justify-between rounded-lg border p-3
label: font-medium
prefix: code text-xs text-muted-foreground
meta: mt-0.5 flex gap-3 text-xs text-muted-foreground
revoke: rounded border border-destructive/30 px-2 py-1 text-xs text-destructive hover:bg-destructive/10
```

### Webhook Row
```
container: rounded-lg border p-4
status dot: inline-block h-2 w-2 rounded-full bg-green-500
url: code truncate text-sm
events: rounded bg-muted px-1.5 py-0.5 text-xs  (per event)
metadata: mt-1 text-xs text-muted-foreground
actions: ml-4 flex shrink-0 gap-1
  edit: rounded border px-2 py-1 text-xs hover:bg-muted
  delete: rounded border border-destructive/30 px-2 py-1 text-xs text-destructive hover:bg-destructive/10
  test: rounded border px-2 py-1 text-xs hover:bg-muted disabled:opacity-50
```

### Report Row
```
container: flex items-center justify-between rounded-lg border p-3
file: font-medium hover:underline
meta: mt-0.5 flex gap-2 text-xs text-muted-foreground
pass: text-green-600
fail: text-red-600
actions: flex gap-1
  view: rounded border px-2 py-1 text-xs hover:bg-muted
  download: rounded border px-2 py-1 text-xs hover:bg-muted
```

### Invoice Row
```
container: flex items-center justify-between rounded border p-2 text-sm
date: font-medium
amount: ml-2 text-muted-foreground
status: rounded px-1.5 py-0.5 text-xs bg-green-100 text-green-700
link: text-primary hover:underline
```

---

## 11. Grid Patterns

```
2-col: grid gap-4 sm:grid-cols-2
3-col: grid gap-4 sm:grid-cols-3
5-col: grid gap-3 sm:grid-cols-5   (plan comparison)
form:  grid gap-3 sm:grid-cols-2   (form fields)
stats: grid gap-2 text-sm sm:grid-cols-3
features: grid gap-1 text-sm sm:grid-cols-2
```

---

## 12. Progress Bars (Usage Page)

```
container: flex items-center justify-between text-sm
label: font-medium
value: text-muted-foreground
bar bg: mt-1 h-2 overflow-hidden rounded-full bg-muted
bar fill: h-full rounded-full transition-all
  normal: bg-primary
  warning (80%+): bg-yellow-500
  danger (95%+): bg-destructive
```

---

## 13. Loading Skeletons

```
line: h-4 animate-pulse rounded bg-muted
block: h-10 w-full animate-pulse rounded bg-muted
card: rounded-lg border p-6 space-y-3  (+ skeleton lines)
table header: border-b bg-muted/30 px-4 py-3 flex gap-4
table row: border-b last:border-0 px-4 py-3 flex gap-4
dashboard: p-8 max-w-4xl  (container for skeleton page)
```

---

## 14. Super Admin Toolbar

### Toolbar Bar
```
bg-violet-600 text-white px-4 py-2 text-sm flex items-center justify-between
```

### Admin Badge
```
rounded bg-violet-500 px-2 py-0.5 text-xs font-bold
```

### Impersonation Banner
```
bg-amber-500 text-amber-950 px-4 py-2 text-sm flex items-center justify-between
label: font-semibold
tenant: text-amber-800
stop btn: rounded bg-amber-900 px-3 py-1 text-xs font-medium text-amber-50 hover:bg-amber-800 disabled:opacity-50
```

### Tenant Picker Dropdown
```
container: absolute right-0 top-full z-50 mt-1 w-80 rounded-lg border bg-white shadow-xl
search: w-full rounded border px-2 py-1.5 text-sm text-gray-900
list: max-h-64 overflow-y-auto
empty: p-3 text-center text-xs text-gray-500
item: flex w-full items-center justify-between px-3 py-2 text-left text-sm text-gray-900 hover:bg-gray-50 disabled:opacity-50
  name: font-medium
  slug: text-xs text-gray-500
```

---

## 15. Responsive Breakpoints

All responsive behavior uses `sm:` prefix (640px+):

```
sm:grid-cols-2   (form fields, grids, feature lists)
sm:grid-cols-3   (admin hub cards, stat grids, health cards)
sm:grid-cols-5   (plan comparison)
sm:col-span-2    (full-width form fields)
```

---

## 16. Transition & Animation

```
transition-colors    (buttons, links, cards)
transition-all       (progress bars)
transition-transform (chevron rotation on accordions)
animate-pulse        (skeleton loading)
hover:bg-muted       (interactive elements)
hover:bg-muted/30    (subtle hover on table rows)
hover:bg-muted/50    (card hover)
hover:underline      (links)
disabled:opacity-50  (all disabled states)
disabled:cursor-not-allowed  (login button)
```

---

## 17. Text Color Reference

| Token | Usage |
|-------|-------|
| `text-foreground` | Default body text |
| `text-muted-foreground` | Secondary text, labels, metadata |
| `text-primary-foreground` | Text on primary buttons |
| `text-destructive` | Error messages, destructive labels |
| `text-slate-900` | Login page headings |
| `text-slate-700` | Login page labels |
| `text-slate-500` | Login page subtitles |
| `text-slate-400` | Login page placeholders, footer |
| `text-brand-900` | Brand name text |
| `text-green-600` / `text-green-700` | Success text |
| `text-red-600` / `text-red-700` | Error/failed text |
| `text-yellow-600` / `text-yellow-700` | Warning text |
| `text-blue-600` / `text-blue-700` | Info/processing text |
| `text-violet-700` | Super admin badge |
| `text-violet-200` | Toolbar secondary text |
| `text-amber-950` | Impersonation banner text |
| `text-amber-800` | Impersonation tenant name |

---

## 18. Background Color Reference

| Token | Usage |
|-------|-------|
| `bg-background` | Page background |
| `bg-white` | Login page, card content |
| `bg-card` | Card backgrounds |
| `bg-muted` | Badges, avatar circle, skeleton pulse |
| `bg-muted/30` | Table header, subtle hover, sidebar |
| `bg-muted/50` | Card hover state |
| `bg-primary` | Primary buttons |
| `bg-primary/5` | Highlighted card (selected state) |
| `bg-primary/10` | File input button, subtle accent |
| `bg-destructive/10` | Error alert background |
| `bg-green-50` | Success alert |
| `bg-green-100` | Success badge |
| `bg-red-50` | Error alert (login) |
| `bg-red-100` | Error badge |
| `bg-yellow-100` | Warning badge |
| `bg-blue-100` | Processing/info badge |
| `bg-purple-100` | Contacted badge |
| `bg-emerald-50` | Success alert (login) |
| `bg-violet-50` | Super admin info badge |
| `bg-violet-500` | Admin toolbar badge |
| `bg-violet-600` | Admin toolbar background |
| `bg-amber-500` | Impersonation banner |
| `bg-amber-900` | Impersonation stop button |
| `bg-brand-50/30` | Login gradient via, feature card accent |
| `bg-brand-900` | Login submit button |

---

## 19. Border Reference

| Pattern | Usage |
|---------|-------|
| `border` | Standard card/container border |
| `border-b` | Table row separator |
| `border-dashed` | Empty state, pending invite |
| `border-slate-200/60` | Login card border |
| `border-brand-200` | Accent feature card |
| `border-destructive/30` | Destructive button border |
| `border-emerald-200` | Success alert border |
| `border-red-200` | Error alert border |
| `border-green-200` | New key banner border |
| `border-primary` | Highlighted card border |
