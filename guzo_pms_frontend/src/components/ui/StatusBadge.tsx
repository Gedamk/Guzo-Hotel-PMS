export type BadgeVariant = "success" | "warning" | "danger" | "info" | "neutral";

const STATUS_LABELS: Record<string, string> = {
  pending_request: "Pending Request",
  deposit_requested: "Deposit Requested",
  deposit_required: "Deposit Required",
  deposit_paid: "Deposit Paid",
  paid: "Paid",
  guaranteed: "Guaranteed",
  confirmed: "Confirmed",
  converted: "Converted",
  in_house: "In-House",
  checked_in: "Checked In",
  checked_out: "Checked Out",
  no_show: "No-show",
  cancelled: "Cancelled",
  room_tbd: "Room TBD",
  room_not_ready: "Room Not Ready",
  ready: "Ready",
  blocked: "Blocked",
  warning: "Warning",
  active: "Active",
  inactive: "Inactive",
  enabled: "Enabled",
  disabled: "Disabled",
  online: "Online",
  configured: "Configured",
  manual_export_ready: "Manual Export Ready",
  vacant_clean: "Vacant Clean",
  vacant_inspected: "Vacant Inspected",
  inspected: "Inspected",
  occupied_clean: "Occupied Clean",
  vacant_dirty: "Vacant Dirty",
  occupied_dirty: "Occupied Dirty",
  out_of_order: "Out of Order",
  out_of_service: "Out of Service",
  maintenance: "Maintenance",
  in_service: "In Service",
  service_in_progress: "Cleaning in Progress",
  open: "Open",
  closed: "Closed",
};

const STATUS_VARIANT: Record<string, BadgeVariant> = {
  pending: "warning",
  pending_request: "warning",
  pending_guarantee: "warning",
  deposit_requested: "warning",
  deposit_required: "warning",
  deposit_paid: "success",
  paid: "success",
  guaranteed: "success",
  confirmed: "success",
  converted: "success",
  in_house: "info",
  checked_in: "info",
  checked_out: "neutral",
  no_show: "danger",
  "no-show": "danger",
  cancelled: "danger",
  failed: "danger",
  out_of_order: "danger",
  room_tbd: "warning",
  room_not_ready: "danger",
  ready: "success",
  blocked: "danger",
  warning: "warning",
  active: "success",
  inactive: "neutral",
  enabled: "success",
  disabled: "neutral",
  online: "success",
  configured: "success",
  manual_export_ready: "info",
  vacant_clean: "success",
  vacant_inspected: "success",
  inspected: "success",
  occupied_clean: "success",
  vacant_dirty: "danger",
  occupied_dirty: "danger",
  maintenance: "warning",
  in_service: "success",
  service_in_progress: "warning",
  open: "info",
  closed: "neutral",
  out_of_service: "warning",
};

function normalizeStatus(status: string) {
  return String(status || "unknown").trim().toLowerCase().replace(/\s+/g, "_");
}

function labelFromStatus(status: string) {
  const normalized = normalizeStatus(status);
  if (STATUS_LABELS[normalized]) return STATUS_LABELS[normalized];
  return String(status || "Unknown")
    .replace(/[_-]+/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function variantForStatus(status: string): BadgeVariant {
  return STATUS_VARIANT[normalizeStatus(status)] || "neutral";
}

export function StatusBadge({
  status,
  label,
  variant,
}: {
  status: string;
  label?: string;
  variant?: BadgeVariant;
}) {
  const finalVariant = variant || variantForStatus(status);
  return (
    <span className={`status-badge status-badge--${finalVariant}`}>
      {label || labelFromStatus(status)}
    </span>
  );
}
