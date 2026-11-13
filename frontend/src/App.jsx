import { useEffect, useState } from 'react';
import { ShieldCheck, RefreshCw } from 'lucide-react';
import Sidebar from './components/Sidebar';
import StatusIndicator from './components/StatusIndicator';
import Dashboard from './pages/Dashboard';
import Memories from './pages/Memories';
import Settings from './pages/Settings';
import { api } from './services/api';
export default function App() {
  const [page, setPage] = useState('Dashboard'), [health, setHealth] = useState(null), [error, setError] = useState(''), [refresh, setRefresh] = useState(0);
  async function check() { try { setHealth(await api('/health')); setError(''); } catch(e) { setError(e.message); setHealth(null); } }
  useEffect(() => { check(); const timer = setInterval(check, 30000); return () => clearInterval(timer); }, []);
  const onSaved = () => { setRefresh(x => x + 1); check(); };
  return <div className="app-shell"><Sidebar page={page} setPage={setPage}/><main><header className="topbar"><span>Workspace <span className="slash">/</span> <strong>{page}</strong></span><div className="service-status"><StatusIndicator label="Ollama" service={health?.ollama}/><StatusIndicator label="MongoDB" service={health?.mongodb}/><button className="icon-button" aria-label="Refresh service status" onClick={check}><RefreshCw size={15}/></button></div></header><div className="page-content"><div className="page-heading"><div><div className="eyebrow">YOUR LOCAL AI WORKSPACE</div><h1>{page === 'Dashboard' ? 'A clearer view of your work.' : page === 'Memory' ? 'Pick up where you left off.' : 'Make it yours.'}</h1><p>{page === 'Dashboard' ? 'Understand your screen. Remember the details. Stay in flow.' : page === 'Memory' ? 'Your saved context, ready when you need it.' : 'Manage your local connections, capture, and privacy.'}</p></div><span className="local-badge"><ShieldCheck size={15}/> On-device & private</span></div>{error && <p className="error" role="alert">{error}</p>}{page === 'Dashboard' ? <Dashboard refresh={refresh} onSaved={onSaved} setPage={setPage}/> : page === 'Memory' ? <Memories refresh={refresh}/> : <Settings health={health} onSaved={onSaved}/>}<footer><span>BUTL-R <span className="footer-dot">·</span> Built by TheCruisers</span><span>Observe. Understand. Remember.</span></footer></div></main></div>;
}
