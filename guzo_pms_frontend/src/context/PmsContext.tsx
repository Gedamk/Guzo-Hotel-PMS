import { createContext, useContext, useMemo, useState } from "react";
import {
  DEFAULT_BUSINESS_DATE,
  DEFAULT_PROPERTY_CODE,
  getPropertyName,
} from "../config/pms";
import type { PmsContextState } from "../types/pms";

type PmsContextValue = PmsContextState & {
  propertyName: string;
  setPropertyCode: (value: string) => void;
  setBusinessDate: (value: string) => void;
  refreshKey: number;
  refreshData: () => void;
};

const PmsContext = createContext<PmsContextValue | null>(null);

export function PmsProvider({ children }: { children: React.ReactNode }) {
  const [propertyCode, setPropertyCode] = useState(DEFAULT_PROPERTY_CODE);
  const [businessDate, setBusinessDate] = useState(DEFAULT_BUSINESS_DATE);
  const [refreshKey, setRefreshKey] = useState(0);

  const value = useMemo<PmsContextValue>(
    () => ({
      propertyCode,
      businessDate,
      propertyName: getPropertyName(propertyCode),
      setPropertyCode,
      setBusinessDate,
      refreshKey,
      refreshData: () => setRefreshKey((prev) => prev + 1),
    }),
    [propertyCode, businessDate, refreshKey]
  );

  return <PmsContext.Provider value={value}>{children}</PmsContext.Provider>;
}

export function usePmsContext() {
  const value = useContext(PmsContext);
  if (!value) {
    throw new Error("usePmsContext must be used within PmsProvider");
  }
  return value;
}
