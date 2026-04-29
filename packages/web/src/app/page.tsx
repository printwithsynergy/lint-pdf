import { HeroSection } from "@/components/HeroSection";
import { FeaturesSection } from "@/components/FeaturesSection";
import { WebViewerSection } from "@/components/WebViewerSection";
import { HotFolderSection } from "@/components/HotFolderSection";
import { AIFeaturesSection } from "@/components/AIFeaturesSection";
import { HowItWorksSection } from "@/components/HowItWorksSection";
import { CompetitorComparisonSection } from "@/components/CompetitorComparisonSection";
import { PricingSection } from "@/components/PricingSection";
import { TryItCTA } from "@/components/TryItCTA";
import { CTASection } from "@/components/CTASection";
import { isSaasMode } from "@/lib/site-mode";

export default function Home() {
  // SaaS-funnel sections (comparison chart, pricing, try-it CTA, signup
  // CTA) are gated to SaaS mode. The remaining product-description
  // sections render in both modes; WebViewerSection internally hides its
  // pricing-promo block in OSS mode.
  const saasMode = isSaasMode();

  return (
    <main>
      <HeroSection />
      <FeaturesSection />
      <WebViewerSection />
      <HotFolderSection />
      <AIFeaturesSection />
      <HowItWorksSection />
      {saasMode && <CompetitorComparisonSection />}
      {saasMode && <PricingSection />}
      {saasMode && <TryItCTA />}
      {saasMode && <CTASection />}
    </main>
  );
}
