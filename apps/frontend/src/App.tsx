
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
import SimulationsPage from './features/simulations/LiveSimulation';
import ExperimentsPage from './features/experiments/IntegrationExperiments';
import IntegrationPage, { ObservationPage, ColdChainPage } from './features/integration/Page';
import AgentPage from './features/agent/Page';
import { TransportWorkflow } from './components/TransportWorkflow';
import { ExceptionPanel } from './components/ExceptionPanel';

type NavItem = { key: string; title: string; icon: string };
// 导航只保留唯一入口：联合调度覆盖协商/指标/冷链标签，运输计划覆盖原“本机数据库调度”。
// 旧 hash（#/negotiation、#/warehouseOps 等）仍可直达，但不重复出现在菜单里。
const groups: { label: string; items: NavItem[] }[] = [
  { label: '总览', items: [{ key: 'dashboard', title: '总览', icon: 'grid' }] },
  { label: '业务数据', items: [{ key: 'orders', title: '订单与库存', icon: 'package' }, { key: 'vehicles', title: '运输计划', icon: 'truck' }] },
  { label: '仓储管理', items: [{ key: 'warehouseTwin', title: '单仓三维视图', icon: 'warehouse' }, { key: 'warehouseOps', title: '仓储运营', icon: 'warehouse' }, { key: 'warehouses', title: '仓储排程', icon: 'clock' }] },
  { label: '调度', items: [{ key: 'plans', title: '联合调度', icon: 'route' }, { key: 'agent', title: '调度助手', icon: 'bot' }, { key: 'events', title: '异常处置', icon: 'alert' }, { key: 'simulations', title: '仿真回放', icon: 'play' }] },
  { label: '评测', items: [{ key: 'experiments', title: '对照实验', icon: 'chart' }] },
];

const pageMap: Record<string, ComponentType> = {
  dashboard: DashboardPage, orders: OrdersPage, warehouseTwin: WarehouseTwinPage, warehouseOps: WarehouseManagementPage, warehouses: WarehousesPage, vehicles: TransportWorkflow,
  plans: IntegrationPage, closedLoop: IntegrationPage, agent: AgentPage, postgres: TransportWorkflow, events: ExceptionPanel, simulations: SimulationsPage, experiments: ExperimentsPage,
  negotiation: IntegrationPage, observations: ObservationPage, coldchain: ColdChainPage,
};

// 旧路由保留直达能力，标题仍按真实页面显示。
const titles: Record<string, string> = {
  dashboard: '总览', orders: '订单与库存', vehicles: '运输计划', postgres: '运输计划',
  warehouseTwin: '单仓三维视图', warehouseOps: '仓储运营', warehouses: '仓储排程',
  plans: '联合调度', closedLoop: '联合调度', negotiation: '联合调度',
  observations: '业务观测', coldchain: '冷链与交接',
  agent: '调度助手', events: '异常处置', simulations: '仿真回放', experiments: '对照实验',
};

function currentPage() {
  const key = window.location.hash.replace(/^#\/?/, '');
  return pageMap[key] ? key : 'dashboard';
}

function Shell({ onSignOut }: { onSignOut: () => void }) {
  const [active, setActive] = useState(currentPage);
  const [collapsed, setCollapsed] = useState(false);
  const { connection, bootPhase, snapshotVersion, scenarioId, anomaly } = useApp();
  const Page = pageMap[active];
  const bootLabel = { idle: '等待初始化', checking: '检查连接', importing: '导入数据', planning: '计算方案', ready: snapshotVersion ? '场景已导入' : '场景未导入', failed: '初始化失败' }[bootPhase];

  useEffect(() => {
    window.location.hash = `/${active}`;
  }, [active]);

  useEffect(() => {
    const onHash = () => setActive(currentPage());
    window.addEventListener('hashchange', onHash);
    return () => window.removeEventListener('hashchange', onHash);
  }, []);

  useEffect(() => {
    const onNavigate = (e: Event) => {
      const key = (e as CustomEvent<string>).detail;
      if (key && pageMap[key]) setActive(key);
    };
    window.addEventListener('twin:navigate', onNavigate);
    return () => window.removeEventListener('twin:navigate', onNavigate);
  }, []);

  const title = useMemo(() => titles[active] ?? '总览', [active]);
  const eventLive = anomaly.phase === 'submitting' || anomaly.phase === 'accepted';

  return (
    <div className={`app-shell ${collapsed ? 'sidebar-collapsed' : ''}`}>
      <aside className="sidebar">
        <div className="brand-row">{!collapsed && <div><strong>县域冷链调度</strong><span>仓储与运输协同</span></div>}<button className="icon-btn collapse-btn" onClick={() => setCollapsed((v) => !v)} aria-label={collapsed ? "展开导航" : "折叠导航"} aria-expanded={!collapsed}><Icon name="chevron" size={18} /></button></div>
        {!collapsed && <div className="operator-card"><div className="operator-avatar">调</div><div><strong>调度运营台</strong><small>FastAPI / OR-Tools / SimPy</small></div><span className={`live-dot ${connection === 'ok' ? 'online' : ''}`} /></div>}
        <nav aria-label="主导航">
          {groups.map((g) => <div key={g.label} className="nav-group"><div className="nav-group-label">{!collapsed && g.label}</div>{g.items.map((item) => <button key={item.key} className={`nav-item ${active === item.key ? 'active' : ''}`} onClick={() => setActive(item.key)} aria-label={item.title} aria-current={active === item.key ? "page" : undefined} title={collapsed ? item.title : undefined}><Icon name={item.icon} size={18} />{!collapsed && <span>{item.title}</span>}{item.key === 'events' && eventLive && !collapsed && <em className="nav-alert-dot" />}{!collapsed && active === item.key && <i />}</button>)}</div>)}
        </nav>
        {!collapsed && <div className="sidebar-footer"><div className="connection-line"><span className={`live-dot ${connection === 'ok' ? 'online' : ''}`} />{connection === 'ok' ? `后端已连接，${bootLabel}` : connection === 'bad' ? '后端未连接' : '正在连接后端'}</div><small>契约 {CONTRACT_VERSION}{snapshotVersion ? `，快照第 ${snapshotVersion} 版` : ''}</small></div>}
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
      </main>
    </div>
  );
}

export default function App() {
  const [authed, setAuthed] = useState(Boolean(getToken()));
  if (!authed) return <LoginGate onSuccess={() => setAuthed(true)} />;
  return <AppProvider><Shell onSignOut={() => { clearToken(); setAuthed(false); }} /></AppProvider>;
}
