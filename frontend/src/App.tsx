
import type { ComponentType } from 'react';
import { CONTRACT_VERSION } from './client/contractVersion';
import { useEffect, useMemo, useState } from 'react';
import { AppProvider, useApp } from './appContext';
import Icon from './components/Icons';
import { LoginGate } from './components/LoginGate';
import { clearToken, getToken } from './auth';
import DashboardPage from './features/dashboard/Page';
import OrdersPage from './features/orders/Page';
import WarehousesPage from './features/warehouses/Page';
import WarehouseManagementPage from './features/warehouse/Page';
import WarehouseTwinPage from './features/warehouseTwin/Page';
import VehiclesPage from './features/vehicles/Page';
import PlansPage from './features/plans/Page';
import EventsPage from './features/events/Page';
import SimulationsPage from './features/simulations/Page';
import ExperimentsPage from './features/experiments/Page';
import PostgresPage from './features/postgres/Page';
import ClosedLoopPage from './features/closedLoop/Page';
import AgentPage from './features/agent/Page';

type NavItem = { key: string; title: string; icon: string };
const groups: { label: string; items: NavItem[] }[] = [
  { label: '总览', items: [{ key: 'dashboard', title: '总览', icon: 'grid' }] },
  { label: '业务数据', items: [{ key: 'orders', title: '订单与库存', icon: 'package' }, { key: 'vehicles', title: '运输计划', icon: 'truck' }, { key: 'postgres', title: '本机数据库调度', icon: 'database' }] },
  { label: '仓储管理', items: [{ key: 'warehouseTwin', title: '单仓三维视图', icon: 'warehouse' }, { key: 'warehouseOps', title: '仓储运营', icon: 'warehouse' }, { key: 'warehouses', title: '仓储排程', icon: 'clock' }] },
  { label: '调度', items: [{ key: 'agent', title: '调度助手', icon: 'bot' }, { key: 'closedLoop', title: '仓运闭环', icon: 'route' }, { key: 'plans', title: '联合调度', icon: 'route' }, { key: 'events', title: '异常处置', icon: 'alert' }, { key: 'simulations', title: '仿真回放', icon: 'play' }] },
  { label: '评测', items: [{ key: 'experiments', title: '对照实验', icon: 'chart' }] },
];

const pageMap: Record<string, ComponentType> = {
  dashboard: DashboardPage, orders: OrdersPage, warehouseTwin: WarehouseTwinPage, warehouseOps: WarehouseManagementPage, warehouses: WarehousesPage, vehicles: VehiclesPage,
  plans: PlansPage, closedLoop: ClosedLoopPage, agent: AgentPage, postgres: PostgresPage, events: EventsPage, simulations: SimulationsPage, experiments: ExperimentsPage,
};

function Shell({ onSignOut }: { onSignOut: () => void }) {
  const [active, setActive] = useState('dashboard');
  const [collapsed, setCollapsed] = useState(false);
  const { connection, bootPhase, snapshotVersion, scenarioId, anomaly } = useApp();
  const Page = pageMap[active];
  const bootLabel = { idle: '等待初始化', checking: '检查连接', importing: '导入数据', planning: '计算方案', ready: '数据已同步', failed: '初始化失败' }[bootPhase];

  useEffect(() => {
    const onNavigate = (e: Event) => {
      const key = (e as CustomEvent<string>).detail;
      if (key && pageMap[key]) setActive(key);
    };
    window.addEventListener('twin:navigate', onNavigate);
    return () => window.removeEventListener('twin:navigate', onNavigate);
  }, []);

  const title = useMemo(() => groups.flatMap((g) => g.items).find((i) => i.key === active)?.title ?? '总览', [active]);
  const eventLive = anomaly.phase === 'submitting' || anomaly.phase === 'accepted';

  return (
    <div className={`app-shell ${collapsed ? 'sidebar-collapsed' : ''}`}>
      <aside className="sidebar">
        <div className="brand-row"><div className="brand-logo">冷</div>{!collapsed && <div><strong>县域冷链调度</strong><span>仓储与运输协同</span></div>}<button className="icon-btn collapse-btn" onClick={() => setCollapsed((v) => !v)} aria-label={collapsed ? "展开导航" : "折叠导航"} aria-expanded={!collapsed}><Icon name="chevron" size={18} /></button></div>
        {!collapsed && <div className="operator-card"><div className="operator-avatar">调</div><div><strong>调度运营台</strong><small>FastAPI / OR-Tools / SimPy</small></div><span className={`live-dot ${connection === 'ok' ? 'online' : ''}`} /></div>}
        <nav aria-label="主导航">
          {groups.map((g) => <div key={g.label} className="nav-group"><div className="nav-group-label">{!collapsed && g.label}</div>{g.items.map((item) => <button key={item.key} className={`nav-item ${active === item.key ? 'active' : ''}`} onClick={() => setActive(item.key)} aria-label={item.title} aria-current={active === item.key ? "page" : undefined} title={collapsed ? item.title : undefined}><Icon name={item.icon} size={18} />{!collapsed && <span>{item.title}</span>}{item.key === 'events' && eventLive && !collapsed && <em className="nav-alert-dot" />}{!collapsed && active === item.key && <i />}</button>)}</div>)}
        </nav>
        {!collapsed && <div className="sidebar-footer"><div className="connection-line"><span className={`live-dot ${connection === 'ok' ? 'online' : ''}`} />{connection === 'ok' ? (bootPhase === 'ready' ? '后端已连接，数据已同步' : `后端已连接，${bootLabel}`) : connection === 'bad' ? '后端未连接' : '正在连接后端'}</div><small>契约 {CONTRACT_VERSION}{snapshotVersion ? `，快照第 ${snapshotVersion} 版` : ''}</small></div>}
      </aside>
      <main className="main-content">
        <header className="topbar">
          <div><div className="breadcrumb">智慧冷链数字孪生平台 / <span>{title}</span></div><h1>{title}</h1></div>
          <div className="top-actions">
            <span className="env-badge">{scenarioId ? `场景 ${scenarioId}` : '本地'}</span>
            <span className={`env-badge ${connection === 'ok' ? 'badge-ok' : connection === 'bad' ? 'badge-bad' : ''}`}>{connection === 'ok' ? '后端在线' : connection === 'bad' ? '后端离线' : '正在连接'}</span>
            <button className="btn btn-ghost btn-sm" onClick={onSignOut}>退出</button>
          </div>
        </header>
        <div className="content-wrap"><Page /></div>
        <footer className="app-footer"><span>场景快照与本机数据库数据分开展示。路线为模拟结果，不能直接用于派车。</span></footer>
      </main>
    </div>
  );
}

export default function App() {
  const [authed, setAuthed] = useState(Boolean(getToken()));
  if (!authed) return <LoginGate onSuccess={() => setAuthed(true)} />;
  return <AppProvider><Shell onSignOut={() => { clearToken(); setAuthed(false); }} /></AppProvider>;
}
