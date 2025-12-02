// src/components/HousekeepingBoard.tsx

import React, { useEffect, useMemo, useState } from "react";
import axios from "axios";

const API_BASE = "http://127.0.0.1:8000";
const AUTH_TOKEN = "admin-secret-123";

type HousekeepingRoom = {
  room_number: string;
  property_code: string;
  floor: number | null;
  hk_status: string; // "occupied_clean", "vacant_clean", etc.
  business_date: string;
  is_occupied: boolean;
  guest_name?: string | null;
  check_in_date?: string | null;
  check_out_date?: string | null;
};

interface HousekeepingBoardProps {
  /**
   * Business date in YYYY-MM-DD.
   * If not provided, defaults to today's date.
   */
  businessDate?: string;
}

const HOTEL_NAME_BY_PROPERTY: Record<string, string> = {
  DRE001: "Dream Big Hotel",
  "N&N002": "N&N Luxury Hotel",
};

type HKFilter =
  | "all"
  | "vacant_clean"
  | "vacant_dirty"
  | "occupied_clean"
  | "occupied_dirty"
  | "out_of_order"
  | "in_service";

const formatHKStatus = (hk: string): string => {
  switch (hk) {
    case "occupied_clean":
      return "Occupied / Clean";
    case "occupied_dirty":
      return "Occupied / Dirty";
    case "vacant_clean":
      return "Vacant / Clean";
    case "vacant_dirty":
      return "Vacant / Dirty";
    case "out_of_order":
      return "Out of Order";
    case "in_service":
      return "In Service";
    default:
      return hk;
  }
};

const formatGuestStay = (room: HousekeepingRoom): string => {
  if (!room.guest_name || !room.check_in_date || !room.check_out_date) {
    return "No guest in-house";
  }
  return `${room.guest_name}${room.check_in_date && room.check_out_date ? `${room.check_in_date} → ${room.check_out_date}` : ""}`;
};

const HousekeepingBoard: React.FC<HousekeepingBoardProps> = ({
  businessDate,
}) => {
  const [rooms, setRooms] = useState<HousekeepingRoom[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const [propertyFilter, setPropertyFilter] = useState<string>("all");
  const [floorFilter, setFloorFilter] = useState<string>("all");
  const [hkFilter, setHKFilter] = useState<HKFilter>("all");

  const todayIso = new Date().toISOString().slice(0, 10);
  const effectiveBusinessDate = businessDate || todayIso;

  const loadRooms = async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await axios.get<HousekeepingRoom[]>(
        `${API_BASE}/rooms/status-board`,
        {
          params: {
            date: effectiveBusinessDate,
            property_code: propertyFilter === "all" ? undefined : propertyFilter,
          },
          headers: {
            Authorization: `Bearer ${AUTH_TOKEN}`,
          },
        }
      );
      setRooms(resp.data);
    } catch (e: any) {
      console.error("Error loading housekeeping rooms:", e);
      const detail =
        e.response?.data?.detail || "Error loading housekeeping rooms";
      setError(detail);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (effectiveBusinessDate) {
      loadRooms();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [effectiveBusinessDate, propertyFilter]);

  // Derived filters
  const filteredRooms = useMemo(() => {
    return rooms.filter((r) => {
      if (propertyFilter !== "all" && r.property_code !== propertyFilter) {
        return false;
      }
      if (floorFilter !== "all") {
        const floorNum = parseInt(floorFilter, 10);
        if ((r.floor ?? null) !== floorNum) return false;
      }
      if (hkFilter !== "all" && r.hk_status !== hkFilter) {
        return false;
      }
      return true;
    });
  }, [rooms, propertyFilter, floorFilter, hkFilter]);

  // Totals
  const totalRooms = rooms.length;
  const vacantClean = rooms.filter((r) => r.hk_status === "vacant_clean").length;
  const vacantDirty = rooms.filter((r) => r.hk_status === "vacant_dirty").length;
  const occupiedClean = rooms.filter((r) => r.hk_status === "occupied_clean").length;
  const occupiedDirty = rooms.filter((r) => r.hk_status === "occupied_dirty").length;
  const outOfOrder = rooms.filter((r) => r.hk_status === "out_of_order").length;
  const inService = rooms.filter((r) => r.hk_status === "in_service").length;

  const uniqueProperties = Array.from(
    new Set(rooms.map((r) => r.property_code))
  );

  const uniqueFloors = Array.from(
    new Set(rooms.map((r) => r.floor).filter((f): f is number => f !== null))
  ).sort((a, b) => a - b);

  // --- HK actions ----------------------------------------------------------

  type HKAction = "clean" | "dirty" | "out-of-order" | "in-service";

  const markRoomStatus = async (room: HousekeepingRoom, action: HKAction) => {
    const endpointMap: Record<HKAction, string> = {
      clean: "mark-clean",
      dirty: "mark-dirty",
      "out-of-order": "mark-out-of-order",
      "in-service": "mark-in-service",
    };

    try {
      await axios.post(
        `${API_BASE}/rooms/housekeeping/${endpointMap[action]}`,
        {
          room_number: room.room_number,
          property_code: room.property_code,
          business_date: effectiveBusinessDate,
        },
        {
          headers: {
            Authorization: `Bearer ${AUTH_TOKEN}`,
          },
        }
      );
      await loadRooms();
    } catch (e) {
      console.error("Error marking room status:", e);
      // We do not set global error to avoid hiding main board; just log
    }
  };

  return (
    <div className="housekeeping-board">
      <div style={{ marginBottom: "0.75rem" }}>
        <div>
          <strong>Business Date:</strong> {effectiveBusinessDate}
        </div>
      </div>

      <div style={{ display: "flex", gap: "1rem", marginBottom: "1rem" }}>
        <div>
          <label>
            Property:
            <select
              value={propertyFilter}
              onChange={(e) => setPropertyFilter(e.target.value)}
              style={{ marginLeft: "0.5rem" }}
            >
              <option value="all">All Properties</option>
              {uniqueProperties.map((pc) => (
                <option key={pc} value={pc}>
                  {HOTEL_NAME_BY_PROPERTY[pc] || pc}
                </option>
              ))}
            </select>
          </label>
        </div>

        <div>
          <label>
            Floor:
            <select
              value={floorFilter}
              onChange={(e) => setFloorFilter(e.target.value)}
              style={{ marginLeft: "0.5rem" }}
            >
              <option value="all">All</option>
              {uniqueFloors.map((f) => (
                <option key={f} value={String(f)}>
                  {f}
                </option>
              ))}
            </select>
          </label>
        </div>

        <div>
          <label>
            HK Status:
            <select
              value={hkFilter}
              onChange={(e) => setHKFilter(e.target.value as HKFilter)}
              style={{ marginLeft: "0.5rem" }}
            >
              <option value="all">All</option>
              <option value="vacant_clean">Vacant / Clean</option>
              <option value="vacant_dirty">Vacant / Dirty</option>
              <option value="occupied_clean">Occupied / Clean</option>
              <option value="occupied_dirty">Occupied / Dirty</option>
              <option value="out_of_order">Out of Order</option>
              <option value="in_service">In Service</option>
            </select>
          </label>
        </div>
      </div>

      <div style={{ marginBottom: "1rem" }}>
        <div>
          <strong>Total Rooms</strong> {totalRooms}
        </div>
        <div>Vacant / Clean: {vacantClean}</div>
        <div>Vacant / Dirty: {vacantDirty}</div>
        <div>Occupied / Clean: {occupiedClean}</div>
        <div>Occupied / Dirty: {occupiedDirty}</div>
        <div>OOO / Service: {outOfOrder}</div>
        <div>In Service: {inService}</div>
      </div>

      {loading && <p>Loading housekeeping rooms...</p>}
      {error && <p style={{ color: "red" }}>Error loading rooms: {error}</p>}

      {!loading && !error && (
        <>
          <h3>Rooms ({filteredRooms.length})</h3>
          {filteredRooms.length === 0 ? (
            <p>No rooms match the selected filters for this date.</p>
          ) : (
            <table
              style={{ width: "100%", borderCollapse: "collapse" }}
              cellPadding={4}
            >
              <thead>
                <tr>
                  <th>Room</th>
                  <th>Floor</th>
                  <th>Property</th>
                  <th>HK Status</th>
                  <th>Guest / Stay</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredRooms.map((room) => (
                  <tr key={`${room.property_code}-${room.room_number}`}>
                    <td>{room.room_number}</td>
                    <td>{room.floor ?? ""}</td>
                    <td>
                      {HOTEL_NAME_BY_PROPERTY[room.property_code] ||
                        room.property_code}
                      {room.property_code}
                    </td>
                    <td>{formatHKStatus(room.hk_status)}</td>
                    <td>{formatGuestStay(room)}</td>
                    <td>
                      <button
                        onClick={() => markRoomStatus(room, "clean")}
                        style={{ marginRight: "0.25rem" }}
                      >
                        Mark Clean
                      </button>
                      <button
                        onClick={() => markRoomStatus(room, "dirty")}
                        style={{ marginRight: "0.25rem" }}
                      >
                        Mark Dirty
                      </button>
                      <button
                        onClick={() => markRoomStatus(room, "out-of-order")}
                        style={{ marginRight: "0.25rem" }}
                      >
                        OOO
                      </button>
                      <button
                        onClick={() => markRoomStatus(room, "in-service")}
                      >
                        In Service
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </>
      )}
    </div>
  );
};

export default HousekeepingBoard;
