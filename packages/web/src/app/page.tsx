import { HeroSection } from "@/components/HeroSection";
import { FeaturesSection } from "@/components/FeaturesSection";
import { HotFolderSection } from "@/components/HotFolderSection";
import { AIFeaturesSection } from "@/components/AIFeaturesSection";
import { HowItWorksSection } from "@/components/HowItWorksSection";
import { CompetitorComparisonSection } from "@/components/CompetitorComparisonSection";
import { PricingSection } from "@/components/PricingSection";
import { CTASection } from "@/components/CTASection";

export default function Home() {
  return (
    <main>
      <HeroSection />
      <FeaturesSection />
      <HotFolderSection />
      <AIFeaturesSection />
      <HowItWorksSection />
      <CompetitorComparisonSection />
      <PricingSection />
      <CTASection />
    </main>
  );
}
