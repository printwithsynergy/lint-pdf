"use client";

import { createContext, useContext } from "react";

interface BetaContextValue {
  betaMode: boolean;
}

const BetaContext = createContext<BetaContextValue>({ betaMode: false });

export function BetaProvider({ children }: { children: React.ReactNode }) {
  const betaMode = process.env.NEXT_PUBLIC_LINTPDF_BETA_MODE === "true";
  return (
    <BetaContext.Provider value={{ betaMode }}>
      {children}
    </BetaContext.Provider>
  );
}

export function useBeta(): BetaContextValue {
  return useContext(BetaContext);
}
