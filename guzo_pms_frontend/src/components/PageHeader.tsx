type PageHeaderProps = {
  title: string;
  subtitle?: string;
  rightSlot?: React.ReactNode;
};

export default function PageHeader({
  title,
  subtitle,
  rightSlot,
}: PageHeaderProps) {
  return (
    <div className="topbar">
      <div>
        <h1 className="page-heading">{title}</h1>
        {subtitle ? <div className="page-subheading">{subtitle}</div> : null}
      </div>
      {rightSlot ? <div className="topbar-badges">{rightSlot}</div> : null}
    </div>
  );
}
