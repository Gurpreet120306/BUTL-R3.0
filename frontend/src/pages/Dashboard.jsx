import ScreenPanel from '../components/ScreenPanel';
import ChatPanel from '../components/ChatPanel';
import MemoryPanel from '../components/MemoryPanel';
export default function Dashboard({ refresh, onSaved, setPage }) {
  return <><div className="dashboard-grid"><ScreenPanel onSaved={onSaved}/><ChatPanel/></div><MemoryPanel compact refresh={refresh} onOpen={() => setPage('Memory')}/></>;
}
