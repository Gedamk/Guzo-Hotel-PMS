import type { BadgeVariant } from "./StatusBadge";

export function HandoffBadge({
  label,
  variant = "neutral",
}: {
  label: string;
  variant?: BadgeVariant;
}) {
  return <span className={`handoff-badge handoff-badge--${variant}`}>{label}</span>;
}
