import { Info } from "lucide-react";

type PageHeaderProps = {
  title: string;
  subtitle?: string;
  metadata?: React.ReactNode;
  rightSlot?: React.ReactNode;
};

export default function PageHeader({
  title,
  subtitle,
  metadata,
  rightSlot,
}: PageHeaderProps) {
  return (
    <div className="topbar">
      <div className="page-header-content">
        <div className="page-title-row">
          <h1 className="page-heading">{title}</h1>
          {subtitle ? (
            <button
              className="page-info-button"
              type="button"
              aria-label={`About ${title}: ${subtitle}`}
              title={subtitle}
            >
              <Info aria-hidden="true" size={17} />
            </button>
          ) : null}
        </div>
        {metadata ? <div className="page-metadata">{metadata}</div> : null}
      </div>
      {rightSlot ? <div className="topbar-badges">{rightSlot}</div> : null}
    </div>
  );
}
