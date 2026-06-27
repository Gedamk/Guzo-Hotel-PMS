import { createContext, useContext, useEffect, useMemo, useState } from "react";
import axios from "axios";
import {
  DEFAULT_BUSINESS_DATE,
  DEFAULT_PROPERTY_CODE,
  DEFAULT_PROPERTY_OPTIONS,
} from "../config/pms";
import {
  createAdminProperty,
  fetchProperties,
  updateAdminProperty,
} from "../services/adminService";
import type { HotelProperty, PmsContextState } from "../types/pms";

const PROPERTY_STORAGE_KEY = "guzo:pms:properties";

function normalizePropertyCode(value: string) {
  return value.trim().toUpperCase().replace(/\s+/g, "");
}

function loadStoredProperties(): HotelProperty[] {
  if (typeof window === "undefined") return DEFAULT_PROPERTY_OPTIONS;
  try {
    const raw = window.localStorage.getItem(PROPERTY_STORAGE_KEY);
    if (!raw) return DEFAULT_PROPERTY_OPTIONS;
    const stored = JSON.parse(raw) as HotelProperty[];
    const byCode = new Map<string, HotelProperty>();
    [...DEFAULT_PROPERTY_OPTIONS, ...stored].forEach((property) => {
      const code = normalizePropertyCode(property.code);
      if (!code) return;
      byCode.set(code, {
        ...property,
        code,
        onboardingStatus: property.onboardingStatus || "not_started",
      });
    });
    return Array.from(byCode.values());
  } catch {
    return DEFAULT_PROPERTY_OPTIONS;
  }
}

function persistProperties(properties: HotelProperty[]) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(PROPERTY_STORAGE_KEY, JSON.stringify(properties));
}

type PmsContextValue = PmsContextState & {
  propertyName: string;
  propertyOptions: HotelProperty[];
  activeProperty: HotelProperty;
  setPropertyCode: (value: string) => void;
  setBusinessDate: (value: string) => void;
  saveProperty: (property: HotelProperty) => Promise<HotelProperty>;
  updateProperty: (code: string, changes: Partial<HotelProperty>) => Promise<HotelProperty | null>;
  syncProperty: (property: HotelProperty) => HotelProperty;
  refreshKey: number;
  refreshData: () => void;
};

const PmsContext = createContext<PmsContextValue | null>(null);

export function PmsProvider({ children }: { children: React.ReactNode }) {
  const [propertyOptions, setPropertyOptions] = useState<HotelProperty[]>(() =>
    loadStoredProperties()
  );
  const [propertyCode, setPropertyCode] = useState(DEFAULT_PROPERTY_CODE);
  const [businessDate, setBusinessDate] = useState(DEFAULT_BUSINESS_DATE);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    async function hydrateProperties() {
      try {
        const backendProperties = await fetchProperties();
        if (cancelled || !backendProperties.length) return;
        setPropertyOptions(backendProperties);
        persistProperties(backendProperties);
      } catch {
        // Keep localStorage/demo properties when the backend is unavailable.
      }
    }
    hydrateProperties();
    return () => {
      cancelled = true;
    };
  }, []);

  function handleSetPropertyCode(value: string) {
    setPropertyCode(normalizePropertyCode(value));
  }

  function upsertLocalProperty(property: HotelProperty) {
    const normalized = {
      ...property,
      code: normalizePropertyCode(property.code),
      onboardingStatus: property.onboardingStatus || "not_started",
    };
    setPropertyOptions((current) => {
      const next = current.some((item) => item.code === normalized.code)
        ? current.map((item) => (item.code === normalized.code ? normalized : item))
        : [...current, normalized];
      persistProperties(next);
      return next;
    });
    setPropertyCode(normalized.code);
    return normalized;
  }

  async function saveProperty(property: HotelProperty) {
    const normalized = {
      ...property,
      code: normalizePropertyCode(property.code),
      onboardingStatus: property.onboardingStatus || "not_started",
    };
    try {
      const saved = normalized.id
        ? await updateAdminProperty(normalized)
        : await createAdminProperty(normalized);
      upsertLocalProperty(saved);
      return saved;
    } catch (error) {
      if (axios.isAxiosError(error) && error.response) throw error;
      return upsertLocalProperty(normalized);
    }
  }

  function findLocalProperty(code: string) {
    const normalizedCode = normalizePropertyCode(code);
    return propertyOptions.find((item) => item.code === normalizedCode) || null;
  }

  function updateLocalProperty(code: string, changes: Partial<HotelProperty>) {
    const normalizedCode = normalizePropertyCode(code);
    let updated: HotelProperty | null = null;
    setPropertyOptions((current) => {
      const next = current.map((item) =>
        item.code === normalizedCode ? (updated = { ...item, ...changes, code: normalizedCode }) : item
      );
      persistProperties(next);
      return next;
    });
    return updated;
  }

  async function updateProperty(code: string, changes: Partial<HotelProperty>) {
    const current = findLocalProperty(code);
    if (!current) return null;
    const desired = { ...current, ...changes, code: current.code };
    if (!desired.id) return updateLocalProperty(code, changes);
    try {
      const saved = await updateAdminProperty(desired);
      upsertLocalProperty(saved);
      return saved;
    } catch (error) {
      if (axios.isAxiosError(error) && error.response) throw error;
      return updateLocalProperty(code, changes);
    }
  }

  const activeProperty =
    propertyOptions.find((property) => property.code === propertyCode) ||
    propertyOptions[0] ||
    DEFAULT_PROPERTY_OPTIONS[0];

  const value = useMemo<PmsContextValue>(
    () => ({
      propertyCode,
      businessDate,
      propertyName: activeProperty.name,
      propertyOptions,
      activeProperty,
      setPropertyCode: handleSetPropertyCode,
      setBusinessDate,
      saveProperty,
      updateProperty,
      syncProperty: upsertLocalProperty,
      refreshKey,
      refreshData: () => setRefreshKey((prev) => prev + 1),
    }),
    [propertyCode, businessDate, propertyOptions, activeProperty, refreshKey]
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
