import { Link, useSearchParams } from "react-router-dom";
import { Clock } from "lucide-react";
import PageHeader from "../../components/PageHeader";

export default function ComingSoonPage() {
  const [params] = useSearchParams();
  const feature = params.get("feature") || "This PMS workflow";

  return (
    <div className="page-grid coming-soon-page">
      <PageHeader
        title={`${feature} Coming Soon`}
        subtitle="This Opera-style menu item is reserved for a planned Guzo PMS workflow screen."
      />
      <section className="card coming-soon-card">
        <Clock aria-hidden="true" size={34} />
        <div>
          <h2>{feature}</h2>
          <p>
            The navigation entry is available so hotel teams can see the full workflow map.
            The dedicated screen is not active yet.
          </p>
        </div>
        <Link className="primary-btn" to="/dashboard">
          Back to Dashboard
        </Link>
      </section>
    </div>
  );
}
