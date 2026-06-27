type LoadingStateProps = {
  label: string;
};

export function LoadingState({ label }: LoadingStateProps) {
  return (
    <div className="pms-loading-state" role="status" aria-live="polite">
      <span aria-hidden="true" />
      <strong>{label}</strong>
    </div>
  );
}
