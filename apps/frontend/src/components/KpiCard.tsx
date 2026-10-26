
import Icon from './Icons';

export function KpiCard({
  label,
  value,
  sub,
  icon = 'chart',
  tone = 'neutral',
}: {
  label: string;
  value: string;
  sub?: string;
  icon?: Parameters<typeof Icon>[0]['name'];
  tone?: 'green'|'neutral'|'orange'|'red';
}) {
  return (
    <div className="kpi-card">
      <div className={`kpi-icon kpi-${tone}`}><Icon name={icon} size={20}/></div>
      <div className="kpi-copy">
        <span>{label}</span>
        <strong>{value}</strong>
        {sub && <small>{sub}</small>}
      </div>
    </div>
  );
}
