// src/components/AssignRoomModal.tsx
import React, { useState } from "react";

interface AssignRoomModalProps {
  bookingId: number;
  guestName: string;
  onConfirm: (room: string) => void;
  onCancel: () => void;
  loading?: boolean;
  error?: string | null;
}

const AssignRoomModal: React.FC<AssignRoomModalProps> = ({
  bookingId,
  guestName,
  onConfirm,
  onCancel,
  loading = false,
  error = null,
}) => {
  const [room, setRoom] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!room.trim() || loading) return;
    onConfirm(room.trim());
  };

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/60">
      <div className="w-full max-w-sm rounded-2xl border border-slate-700 bg-slate-900 p-4 shadow-xl">
        <h3 className="text-sm font-semibold text-slate-100">
          Assign Room
        </h3>
        <p className="mt-1 text-[11px] text-slate-400">
          Booking #{bookingId} · {guestName}
        </p>

        <form onSubmit={handleSubmit} className="mt-3 space-y-3">
          <div>
            <label className="mb-1 block text-[11px] text-slate-300">
              Room number
            </label>
            <input
              type="text"
              value={room}
              onChange={(e) => setRoom(e.target.value)}
              placeholder="e.g. 205, 305B..."
              className="w-full rounded-md border border-slate-700 bg-slate-950 px-2 py-1.5 text-xs text-slate-100 outline-none focus:border-emerald-500"
              disabled={loading}
            />
          </div>

          {error && (
            <p className="text-[11px] text-rose-300">
              {error}
            </p>
          )}

          <div className="flex justify-end gap-2 pt-1">
            <button
              type="button"
              onClick={onCancel}
              className="rounded-full border border-slate-700 px-3 py-1 text-[11px] text-slate-300 hover:bg-slate-800"
              disabled={loading}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="rounded-full bg-emerald-600 px-3 py-1 text-[11px] font-semibold text-slate-950 hover:bg-emerald-500 disabled:opacity-60"
              disabled={loading}
            >
              {loading ? "Assigning..." : "Assign room"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default AssignRoomModal;
