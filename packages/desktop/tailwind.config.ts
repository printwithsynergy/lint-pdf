import type { Config } from "tailwindcss";

/**
 * Brand color scale — read from CSS custom properties at runtime so the
 * Onboarding flow can apply the captured tenant's `primaryColor` as the
 * dominant brand shade. Each shade falls back to the original hardcoded
 * blue palette when no theme override is present, so unbranded
 * development still looks identical to the pre-Onboarding build.
 *
 * `<alpha-value>` lets Tailwind utilities like `bg-brand-600/20` work
 * with the variable values; the runtime ThemeProvider stores colors as
 * `R G B` triples (e.g. `--brand-600: 0 116 198`).
 */
const brandShade = (shade: number, fallback: string) =>
  `rgb(var(--brand-${shade}, ${fallback}) / <alpha-value>)`;

export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: brandShade(50, "240 247 255"),
          100: brandShade(100, "224 239 254"),
          200: brandShade(200, "186 224 253"),
          300: brandShade(300, "124 200 251"),
          400: brandShade(400, "54 173 247"),
          500: brandShade(500, "12 147 232"),
          600: brandShade(600, "0 116 198"),
          700: brandShade(700, "1 93 161"),
          800: brandShade(800, "6 79 133"),
          900: brandShade(900, "11 66 110"),
          950: brandShade(950, "7 42 73"),
        },
      },
    },
  },
  plugins: [],
} satisfies Config;
