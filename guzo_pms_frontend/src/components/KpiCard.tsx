type KpiCardProps = {
  label: string;
  value: string;
  helpText?: string;
};

export default function KpiCard({ label, value, helpText }: KpiCardProps) {
  return (
    <div className="card">
      <div className="kpi-title">{label}</div>
      <div className="kpi-value">{value}</div>
      {helpText ? <div className="kpi-subtitle">{helpText}</div> : null}
    </div>
  );
}
