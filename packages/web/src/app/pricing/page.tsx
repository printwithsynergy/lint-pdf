import PricingClient from "./PricingClient";

// Force every request to render fresh on the origin. Prevents the Railway /
// Fastly edge from serving prerendered HTML indefinitely under s-maxage, which
// was stranding an older tier layout on lintpdf.com/pricing after deploys.
export const dynamic = "force-dynamic";

export default function PricingPage() {
  return <PricingClient />;
}
