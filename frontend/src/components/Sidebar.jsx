import { Bot, LayoutDashboard, Database, Settings, ShieldCheck, ArrowUpRight } from 'lucide-react';
export default function Sidebar({ page, setPage }) {
  return <aside className="sidebar">
    <a className="brand" href="#" onClick={e => { e.preventDefault(); setPage('Dashboard'); }}><span className="brand-icon"><Bot size={26}/></span><span>BUTL-R<small>BY THECRUISERS</small></span></a>
    <div className="nav-label">WORKSPACE</div>
    <nav aria-label="Main navigation">{[[LayoutDashboard, 'Dashboard'], [Database, 'Memory'], [Settings, 'Settings']].map(([Icon, name]) => <button key={name} onClick={() => setPage(name)} className={page === name ? 'nav-item active' : 'nav-item'} aria-current={page === name ? 'page' : undefined}><Icon size={18}/>{name}{page === name && <span className="nav-dot"/>}</button>)}</nav>
    <div className="sidebar-bottom"><div className="privacy-note"><ShieldCheck size={20}/><strong>Local by design</strong><p>Your screen. Your memories.<br/>Everything stays on this device.</p><span>NO CLOUD CONNECTION <ArrowUpRight size={12}/></span></div><div className="team"><div className="avatar">TC</div><div>TheCruisers<small>Development workspace</small></div><span className="tiny-dot"/></div></div>
  </aside>;
}
