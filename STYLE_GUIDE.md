# LintPDF Style Guide — Pre-Migration Reference

> **Purpose:** Feed this to Pixie Dust so its default components match LintPDF's original custom styling. Use as the base with Think Neverland brand color overrides.

> **Known Issue:** Pixie Dust's `LoginPage` component has broken default logo links. The logo `src` resolves to a broken image path. Pixie Dust needs to either use `getBranding().brandLogoUrl` for the logo source or accept a `logoUrl` prop.

---

## Brand Color Palette

LintPDF uses a custom blue brand scale defined in `globals.css`:

```css
--brand-50:  #eff6ff;
--brand-100: #dbeafe;
--brand-200: #bfdbfe;
--brand-300: #93c5fd;
--brand-400: #60a5fa;
--brand-500: #3b82f6;
--brand-600: #2563eb;
--brand-700: #1d4ed8;
--brand-800: #1e40af;
--brand-900: #1e3a8a;   /* primary button bg, logo text, headings */
--brand-950: #172554;
```

### CSS Variable Theme (HSL)

```css
:root {
  --primary: 224 69% 40%;
  --primary-foreground: 0 0% 100%;
  --secondary: 200 20% 96%;
  --secondary-foreground: 224 76% 33%;
  --accent: 217 91% 60%;
  --accent-foreground: 224 76% 33%;
  --destructive: 0 84% 60%;
  --destructive-foreground: 0 0% 98%;
  --muted: 200 20% 96%;
  --muted-foreground: 210 9% 46%;
  --background: 0 0% 100%;
  --foreground: 220 30% 10%;
  --card: 0 0% 100%;
  --card-foreground: 220 30% 10%;
  --border: 210 13% 91%;
  --input: 210 13% 91%;
  --ring: 224 69% 40%;
}

.dark {
  --background: 220 20% 5%;
  --foreground: 0 0% 98%;
  --card: 220 18% 8%;
  --card-foreground: 0 0% 98%;
  --primary: 224 69% 50%;
  --primary-foreground: 0 0% 100%;
  --secondary: 220 15% 15%;
  --secondary-foreground: 0 0% 90%;
  --muted: 220 14% 14%;
  --muted-foreground: 210 10% 60%;
  --accent: 217 91% 60%;
  --accent-foreground: 0 0% 100%;
  --destructive: 0 70% 50%;
  --destructive-foreground: 0 0% 98%;
  --border: 220 15% 18%;
  --input: 220 15% 18%;
  --ring: 224 69% 50%;
}
```

### Semantic Status Colors

| Status | Background | Text | Use |
|--------|-----------|------|-----|
| Error | `bg-red-100` | `text-red-700` | Preflight errors, form validation |
| Warning | `bg-yellow-100` | `text-yellow-700` | Warnings, pending states |
| Success | `bg-green-100` | `text-green-700` | Complete, saved states |
| Info | `bg-blue-100` | `text-blue-700` | Processing, advisory |

---

## Typography

### Font Stack

```
Sans: Inter (Google Fonts, variable weight, swap display)
Mono: JetBrains Mono (Google Fonts, variable weight, swap display)
Fallback: system-ui, -apple-system, sans-serif
```

### Heading Hierarchy

| Level | Class | Use |
|-------|-------|-----|
| Page title | `text-2xl font-bold` or `text-[22px] font-bold tracking-tight` | Top of each page |
| Section heading | `text-lg font-semibold` | Card/section titles |
| Card title | `text-sm font-semibold` | Within cards, tables |
| Label | `text-sm font-medium` | Form labels, column headers |
| Body | `text-sm` | Default body text |
| Help/muted | `text-sm text-muted-foreground` | Secondary text |
| Small | `text-xs text-muted-foreground` | Timestamps, metadata |

---

## Component Patterns

### Buttons

```
Primary:    bg-brand-900 px-4 py-2.5 text-sm font-semibold text-white rounded-lg shadow-sm hover:bg-brand-800 disabled:opacity-50
Secondary:  rounded-md border px-4 py-2 text-sm hover:bg-muted
Small:      rounded border px-2 py-1 text-xs hover:bg-muted
Destructive: rounded border border-destructive/30 px-2 py-1 text-xs text-destructive hover:bg-destructive/10
Full-width: w-full rounded-lg bg-brand-900 px-4 py-2.5 text-sm font-semibold text-white
```

### Inputs

```
Text/Email: w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm shadow-sm
            placeholder:text-slate-400
            focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500

Select:     w-full rounded-md border px-3 py-2 text-sm

Textarea:   w-full rounded-md border px-3 py-2 text-sm font-mono

File:       text-sm file:mr-3 file:rounded file:border-0 file:bg-primary/10
            file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-primary
            hover:file:bg-primary/20

Color:      h-8 w-8 cursor-pointer rounded border  (paired with text input for hex value)
```

### Cards

```
Standard:    rounded-lg border bg-card p-4
Large:       rounded-2xl border border-slate-200/60 bg-white p-8 shadow-lg shadow-brand-900/5
Highlighted: rounded-lg border p-3 border-primary bg-primary/5  (active/selected state)
Alert:       rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-center  (success)
Error:       rounded-md bg-destructive/10 p-3 text-sm text-destructive
Empty state: rounded-lg border border-dashed p-8 text-center text-muted-foreground
```

### Badges

```
Status:   rounded px-1.5 py-0.5 text-xs font-medium bg-{color}-100 text-{color}-700
Role:     rounded bg-muted px-1.5 py-0.5 text-xs
Built-in: rounded bg-muted px-1.5 py-0.5 text-xs  (with "built-in" text)
Default:  rounded bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary
```

### Tables

```html
<table className="w-full text-sm">
  <thead>
    <tr className="border-b text-left text-muted-foreground">
      <th className="pb-2 font-medium">Header</th>
    </tr>
  </thead>
  <tbody>
    <tr className="border-b last:border-0">
      <td className="py-2">Cell</td>
    </tr>
  </tbody>
</table>
```

### Loading Skeletons

```
Line:  h-4 animate-pulse rounded bg-muted
Block: h-10 w-full animate-pulse rounded bg-muted
Card:  rounded-lg border p-4 space-y-3 + skeleton lines inside
```

---

## Layout

### Page Structure

```
Container: p-8 max-w-5xl (dashboard pages)
           p-8 max-w-4xl (settings pages)
           p-8 max-w-2xl (form-focused pages like profile, appearance)

Header:    flex items-center justify-between (page title left, primary action right)

Sections:  mt-6 between major sections
           mt-4 between sub-sections
           mt-2 between tightly related elements
```

### Dashboard Shell

```
Sidebar: bg-muted/30 border-r
Main:    flex-1 overflow-auto
Toolbar: border-b bg-background px-4 py-2
```

### Login Page

```
Centered:  flex min-h-screen items-center justify-center bg-white p-4
Card:      max-w-[420px] rounded-2xl border border-slate-200/60 bg-white p-8 shadow-lg
Logo:      h-12 w-12 centered above card
Brand:     text-xl font-semibold tracking-tight text-brand-900
Gradient:  fixed inset-0 bg-gradient-to-b from-white via-brand-50/30 to-white
```

---

## Admin Toolbar

```
Toolbar bg:       bg-violet-600 text-white px-4 py-2 text-sm
Admin badge:      rounded bg-violet-500 px-2 py-0.5 text-xs font-bold
Impersonation:    bg-amber-500 text-amber-950 px-4 py-2 text-sm (yellow banner)
Dropdown menu:    absolute right-0 top-full z-50 mt-1 w-80 rounded-lg border bg-white shadow-xl
```

---

## Animation

```
Skeleton pulse: animate-pulse (Tailwind built-in)
Hover:          transition-colors (on buttons, links, table rows)
Focus:          focus:ring-1 focus:ring-brand-500
```

---

## Known Pixie Dust Issues

1. **Broken logo links:** `LoginPage` component renders a broken `<img>` for the logo. It should use `getBranding().brandLogoUrl` from AppSettings or accept a `logoUrl` prop. Currently shows the broken image icon with "AtlasMCP" alt text.

2. **App name showing "AtlasMCP":** The LoginPage is reading a default app name instead of using `getBranding().brandName` from AppSettings. Should show "LintPDF" (the value in AppSettings).

3. **Theme mismatch:** Pixie Dust's default theme uses a purple/dark scheme. LintPDF's theme is blue brand palette on white background. The CSS variables above need to be injected or the theme-kit `defineTheme()` needs to be wired.

---

## Think Neverland Brand Overrides

When applying Think Neverland branding over Pixie Dust defaults:

- Replace Pixie Dust's default purple with the brand-900 blue (`#1e3a8a`)
- Keep the white/light background (not Pixie Dust's dark default)
- Use Inter + JetBrains Mono font stack
- Apply the full brand-50 through brand-950 scale from globals.css
- Maintain the subtle `shadow-brand-900/5` shadow for elevated cards
- Keep status colors semantic (red=error, amber=warning, green=success, blue=info)
