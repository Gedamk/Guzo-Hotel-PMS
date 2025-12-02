// dashboard_ui/src/components/AssignRoomModal.tsx

import React, { useState } from "react";
import axios from "axios";

const API_BASE = "http://127.0.0.1:8000";
const AUTH_TOKEN = "admin-secret-123";

interface AssignRoomModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAssigned: () => void;
  bookingId: number | null;
  guestName?: string | null;
  propertyCode?: string | null;
  currentRoomNumber?: string | null;
}

export const AssignRoomModal: React.FC<AssignRoomModalProps> = ({
  isOpen,
  onClose,
  onAssigned,
  bookingId,
  guestName,
  propertyCode,
  currentRoomNumber,
}) => {
  const [roomNumber, setRoomNumber] = useState<string>(currentRoomNumber || "");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen || bookingId == null) {
    return null;
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const trimmedRoom = roomNumber.trim();
    if (!trimmedRoom) {
      setError("Room number is required.");
      return;
    }

    try {
      setSubmitting(true);
      await axios.post(
        `${API_BASE}/frontdesk/assign-room`,
        {
          booking_id: bookingId,
          room_number: trimmedRoom,
        },
        {
          headers: {
            Authorization: `Bearer ${AUTH_TOKEN}`,
          },
        }
      );

      onAssigned();
      onClose();
    } catch (err: any) {
      console.error("Error assigning room:", err);
      const detail =
        err?.response?.data?.detail ||
        "Failed to assign room. Please check availability and try again.";
      setError(String(detail));
    } finally {
      setSubmitting(false);
    }
  };

  const guestLabel = guestName || "Guest";
  const propertyLabel = propertyCode || "Property";

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-40">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-5">
        <div className="flex justify-between items-center mb-3">
          <h2 className="text-lg font-semibold">Assign Room</h2>
          <button
            type="button"
            onClick={onClose}
            className="text-gray-500 hover:text-gray-800"
          >
            ✕
          </button>
        </div>

        <p className="text-sm text-gray-700 mb-3">
          <span className="font-medium">Guest:</span> {guestLabel} •{" "}
          <span className="font-medium">Property:</span> {propertyLabel}
        </p>

        {error && (
          <div className="mb-3 rounded-md bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">
            ⚠ {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1" htmlFor="roomNumber">
              Room number
            </label>
            <input
              id="roomNumber"
              type="text"
              value={roomNumber}
              onChange={(e) => setRoomNumber(e.target.value)}
              className="w-full border rounded px-2 py-1 text-sm"
              placeholder="e.g. 305"
            />
          </div>

          <div className="flex justify-end space-x-2">
            <button
              type="button"
              onClick={onClose}
              className="px-3 py-1.5 rounded border border-gray-300 text-sm text-gray-700 hover:bg-gray-100"
              disabled={submitting}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-1.5 rounded bg-blue-600 text-sm text-white font-medium hover:bg-blue-700 disabled:opacity-60"
              disabled={submitting}
            >
              {submitting ? "Assigning..." : "Assign Room"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
