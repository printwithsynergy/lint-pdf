const steps = [
  {
    number: "01",
    title: "Submit",
    subtitle: "Submit your file",
    description:
      "POST your PDF (or EPS, TIFF, JPEG, PNG, AI) to the Submit endpoint with your chosen Ruleset. One request, one file, one API call.",
  },
  {
    number: "02",
    title: "Processing",
    subtitle: "500+ Checks in seconds",
    description:
      "LintPDF runs your file through the full Check suite — color spaces, fonts, images, transparency, page geometry, packaging geometry, barcode grading, compliance, and more. Processing happens asynchronously on the Queue.",
  },
  {
    number: "03",
    title: "Report",
    subtitle: "Your preflight report",
    description:
      "Retrieve your Report as JSON, XML, or a visual annotated PDF with findings overlaid on pages. Every finding includes severity, page location, and Check ID. Pass or Error — you know instantly.",
  },
];

export function HowItWorksSection() {
  return (
    <section id="how-it-works" className="bg-white py-24">
      <div className="mx-auto max-w-6xl px-6">
        <div className="text-center mb-16">
          <h2 className="text-3xl font-bold text-slate-900 md:text-4xl mb-4">
            How it works
          </h2>
          <p className="text-slate-500">Three steps from Submit to Report.</p>
        </div>

        <div className="grid gap-8 md:gap-12 md:grid-cols-3">
          {steps.map((step, i) => (
            <div
              key={step.number}
              className="relative text-center md:text-left"
            >
              {/* Connector line (desktop only) */}
              {i < steps.length - 1 && (
                <div className="absolute top-8 left-[calc(50%+2rem)] hidden h-px w-[calc(100%-4rem)] bg-gradient-to-r from-brand-400/40 to-transparent md:block" />
              )}

              <div className="mb-4 inline-flex h-16 w-16 items-center justify-center rounded-full border border-brand-200 bg-brand-50 text-2xl font-bold text-brand-700">
                {step.number}
              </div>
              <h3 className="text-xl font-semibold text-slate-900 mb-1">
                {step.title}
              </h3>
              <p className="text-sm text-brand-500 mb-3 italic">
                {step.subtitle}
              </p>
              <p className="text-sm text-slate-500 leading-relaxed">
                {step.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
