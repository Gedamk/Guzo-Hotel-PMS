// src/components/PortfolioKPICard.tsx
import React, { useEffect, useMemo, useState } from "react";
import axios from "axios";

const API_BASE = "http://127.0.0.1:8000";
const AUTH_TOKEN = "<REDACTED_DEMO_BEARER_TOKEN>";

interface RawPortfolioRow {
  property_code: string;
  hotel_name?: string;
  rooms_total?: number;
  rooms_occupied?: number;
  occupancy_pct?: number;
  adr?: number;
  revpar?: number;
}

interface PortfolioSummary {
  totalRooms: number;
  occupiedRooms: number;
  occupancyPct: number | null;
  adr: number | null;
}

const PortfolioKPICard: React.FC = () => {
  const [rows, setRows] = useState<RawPortfolioRow[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const today = new Date();
  const year = today.getFullYear();
  const month = today.getMonth() + 1;

  useEffect(() => {
    const fetchPortfolio = async () => {
      setLoading(true);
      setError(null);
      try {
        const url = `${API_BASE}/reports/portfolio?year=${year}&month=${month}`;
        const response = await axios.get<RawPortfolioRow[]>(url, {
          headers: {
            Authorization: `Bearer ${AUTH_TOKEN}`,
          },
        });

        const data = Array.isArray(response.data)
          ? response.data
          : (response.data as any).results ?? [];
        setRows(data);
      } catch (err) {
        console.error("Error loading portfolio KPIs", err);
        setError("Unable to load portfolio KPIs.");
      } finally {
        setLoading(false);
      }
    };

    fetchPortfolio();
  }, [year, month]);

  const summary: PortfolioSummary = useMemo(() => {
    if (!rows.length) {
      return {
        totalRooms: 0,
        occupiedRooms: 0,
        occupancyPct: null,
        adr: null,
      };
    }

    let totalRooms = 0;
    let occupiedRooms = 0;
    let adrWeightedSum = 0;

    rows.forEach((row) => {
      const roomsTotal = row.rooms_total ?? 0;
      const roomsOcc = row.rooms_occupied ?? 0;
      const adr = row.adr ?? 0;

      totalRooms += roomsTotal;
      occupiedRooms += roomsOcc;
      adrWeightedSum += adr * roomsOcc;
    });

    const occupancyPct =
      totalRooms > 0 ? (occupiedRooms / totalRooms) * 100 : null;
    const adrValue =
      occupiedRooms > 0 ? adrWeightedSum / occupiedRooms : null;

    return {
      totalRooms,
      occupiedRooms,
      occupancyPct,
      adr: adrValue,
    };
  }, [rows]);

  const formatPercent = (value: number | null): string => {
    if (value === null || isNaN(value)) return "– %";
    return `${value.toFixed(1)}%`;
  };

  const formatCurrency = (value: number | null): string => {
    if (value === null || isNaN(value)) return "–";
    return value.toFixed(2);
  };

  const portfolioLabel =
    rows.length > 0
      ? rows
          .map((r) => r.hotel_name ?? r.property_code)
          .filter(Boolean)
          .join(" / ")
      : "Portfolio";

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-3 text-xs shadow-lg shadow-black/40 sm:p-4">
      <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">
        Portfolio snapshot
      </p>
      <p className="mt-1 text-sm font-semibold text-slate-50">
        Multi-property front desk overview
      </p>

      <p className="mt-1 text-xs text-slate-300">
        Live view of{" "}
          <span className="font-semibold">
            occupancy and ADR for the current month
          </span>{" "}
        across your Guzo portfolio.
      </p>

      {loading && (
        <p className="mt-3 text-[11px] text-slate-400">
          Loading KPIs from Guzo backend…
        </p>
      )}
      {error && !loading && (
        <p className="mt-3 text-[11px] text-rose-300">{error}</p>
      )}

      <div className="mt-3 grid grid-cols-2 gap-2 text-center">
        <div className="rounded-xl border border-emerald-500/40 bg-emerald-500/5 px-2 py-2">
          <p className="text-[10px] uppercase tracking-[0.16em] text-emerald-300">
            Occupancy
          </p>
          <p className="text-lg font-semibold text-emerald-100">
            {formatPercent(summary.occupancyPct)}
          </p>
          <p className="mt-1 text-[10px] text-emerald-200/80">
            {summary.totalRooms > 0
              ? `${summary.occupiedRooms}/${summary.totalRooms} rooms`
              : "No rooms loaded"}
          </p>
        </div>
        <div className="rounded-xl border border-sky-500/40 bg-sky-500/5 px-2 py-2">
          <p className="text-[10px] uppercase tracking-[0.16em] text-sky-300">
            ADR
          </p>
          <p className="text-lg font-semibold text-sky-100">
            {formatCurrency(summary.adr)}
          </p>
          <p className="mt-1 text-[10px] text-sky-200/80">
            Avg room rate (ETB)
          </p>
        </div>
      </div>

      <div className="mt-3 rounded-xl border border-slate-800 bg-slate-950/60 px-2 py-2">
        <p className="text-[11px] font-semibold text-slate-200">
          {portfolioLabel || "Portfolio"}
        </p>
        <p className="text-[11px] text-slate-400">
          Data from <span className="font-semibold">/reports/portfolio</span> for{" "}
          {year}-{month.toString().padStart(2, "0")}.
        </p>
      </div>
    </div>
  );
};

export default PortfolioKPICard;
