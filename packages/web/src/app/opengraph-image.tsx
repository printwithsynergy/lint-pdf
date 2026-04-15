import { ImageResponse } from "next/og";

// Next.js reads these exports to wire up <meta property="og:image"> tags
// with the correct dimensions and content type. Placing this file at the
// root of the app segment makes it the site-wide default OG image, which
// is what Slack / iMessage / LinkedIn / Twitter unfurl when someone shares
// https://lintpdf.com.
export const runtime = "edge";
export const alt = "LintPDF — PDF Preflight API. 500+ checks. PDF/X-1a, PDF/X-3, PDF/X-4, PDF/A compliance.";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default async function OpengraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          background:
            "linear-gradient(135deg, #ffffff 0%, #eff6ff 45%, #dbeafe 100%)",
          fontFamily: "system-ui, sans-serif",
          position: "relative",
        }}
      >
        {/* Soft background glow to match the marketing palette */}
        <div
          style={{
            position: "absolute",
            top: -120,
            left: -120,
            width: 520,
            height: 520,
            borderRadius: "50%",
            background: "#bfdbfe",
            opacity: 0.45,
            display: "flex",
          }}
        />
        <div
          style={{
            position: "absolute",
            bottom: -140,
            right: -140,
            width: 560,
            height: 560,
            borderRadius: "50%",
            background: "#93c5fd",
            opacity: 0.35,
            display: "flex",
          }}
        />

        {/* Logo mark — the "[ ]" brackets-around-lines glyph from /logo.svg */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            width: 160,
            height: 160,
            background: "#4087F7",
            borderRadius: 32,
            marginBottom: 40,
            boxShadow: "0 20px 60px rgba(64, 135, 247, 0.35)",
          }}
        >
          <svg width="110" height="110" viewBox="0 0 1024 1024">
            <path
              d="M210 270 C210 236 236 210 270 210 H358 C380 210 398 228 398 250 C398 272 380 290 358 290 H266 V734 H358 C380 734 398 752 398 774 C398 796 380 814 358 814 H270 C236 814 210 788 210 754 V270Z"
              fill="#F2F2F2"
            />
            <path
              d="M814 270 C814 236 788 210 754 210 H666 C644 210 626 228 626 250 C626 272 644 290 666 290 H758 V734 H666 C644 734 626 752 626 774 C626 796 644 814 666 814 H754 C788 814 814 788 814 754 V270Z"
              fill="#F2F2F2"
            />
            <rect x="347" y="356" width="330" height="36" rx="18" fill="#93C5FD" />
            <rect x="392" y="455" width="240" height="36" rx="18" fill="#93C5FD" />
            <rect x="366" y="554" width="294" height="36" rx="18" fill="#93C5FD" />
          </svg>
        </div>

        <div
          style={{
            fontSize: 84,
            fontWeight: 700,
            color: "#0f172a",
            letterSpacing: "-0.02em",
            display: "flex",
          }}
        >
          LintPDF
        </div>

        <div
          style={{
            fontSize: 34,
            color: "#2563eb",
            marginTop: 12,
            fontWeight: 600,
            display: "flex",
          }}
        >
          PDF Preflight API
        </div>

        <div
          style={{
            fontSize: 22,
            color: "#475569",
            marginTop: 24,
            maxWidth: 900,
            textAlign: "center",
            display: "flex",
          }}
        >
          500+ checks · PDF/X-1a · PDF/X-3 · PDF/X-4 · PDF/A · Zero modifications
        </div>

        <div
          style={{
            position: "absolute",
            bottom: 48,
            fontSize: 20,
            color: "#2563eb",
            fontWeight: 600,
            display: "flex",
          }}
        >
          lintpdf.com
        </div>
      </div>
    ),
    size,
  );
}
