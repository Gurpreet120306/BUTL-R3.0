import { useState } from 'react';
import { ScanLine, Monitor, LoaderCircle, Eye, FileText, Sparkles, AlertCircle } from 'lucide-react';
import { api } from '../services/api';
export default function ScreenPanel({ onSaved }) {
  const [result, setResult] = useState(null), [busy, setBusy] = useState(false), [error, setError] = useState(''), [tab, setTab] = useState('Analysis');
  async function capture(analyze) {
    setBusy(true); setError(''); setResult(null);
    try { const data = await api(`/screen/${analyze ? 'analyze' : 'capture'}`, { method: 'POST', body: { include_preview: true } }); setResult(data); onSaved(); }
    catch (e) { setError(e.message); }
    finally { setBusy(false); }
  }
  const item = result?.observation;
  return <section className="panel screen-panel"><div className="panel-heading"><div><span className="eyebrow"><Monitor size={14}/> YOUR CURRENT CONTEXT</span><h2>Screen analysis</h2></div><span className={`badge ${busy ? 'purple' : ''}`}>{busy ? 'Capturing & understanding' : item ? `Captured ${new Date(item.timestamp).toLocaleTimeString()}` : 'Manual capture'}</span></div>
    <div className="screen-preview">{result?.preview_base64 ? <img src={`data:image/png;base64,${result.preview_base64}`} alt="Current manually captured active window"/> : <div className="empty-screen"><span className="scan-symbol"><ScanLine size={34}/></span><h3>A little context goes a long way.</h3><p>Capture your active window to understand what’s<br className="hidden sm:block"/> on screen and remember what matters.</p><div className="preview-chips"><span>Screen capture</span><span>Text extraction</span><span>Local AI</span></div></div>}{busy && <div className="working"><LoaderCircle className="spin"/> Reading your screen…</div>}</div>
    <div className="capture-bar"><span><Eye size={14}/> Only captures when you ask</span><div><button className="button secondary" disabled={busy} onClick={() => capture(false)}>Capture only</button><button className="button primary" disabled={busy} onClick={() => capture(true)}>{busy ? <LoaderCircle size={16} className="spin"/> : <ScanLine size={16}/>} Analyze Screen</button></div></div>
    {error && <p className="error" role="alert"><AlertCircle size={16}/>{error}</p>}
    {item && <div className="capture-detail"><div className="metadata"><span><small>APPLICATION</small>{item.application || 'Unknown'}</span><span><small>WINDOW</small>{item.window_title || 'Untitled window'}</span></div>
      <div className="tabs">{['Analysis', 'Extracted text', 'UI controls'].map(name => <button key={name} className={tab === name ? 'selected' : ''} onClick={() => setTab(name)}>{name === 'Analysis' ? <Sparkles size={14}/> : <FileText size={14}/>} {name}</button>)}</div>
      {tab === 'Analysis' ? <div className="analysis-text"><p>{item.ai_summary || item.analysis_error || 'Capture complete. Select Analyze Screen to run local AI.'}</p>{item.important_findings?.map((x,i) => <p key={i}>• {x}</p>)}{item.detected_errors?.map((x,i) => <p className="error" key={i}>{x}</p>)}<small>{item.persisted ? `Saved as ${item.observation_id}` : 'Not saved to memory'}</small></div> : <pre>{tab === 'Extracted text' ? item.extracted_text || 'No text could be extracted.' : JSON.stringify(item.ui_elements, null, 2)}</pre>}
      {item.warnings.map((x,i) => <p className="warning" key={i}>{x}</p>)}{item.memory_error && <p className="error">{item.memory_error}</p>}
    </div>}
    <div className="panel-foot"><span className="tiny-dot"/> Screenshot previews are temporary. Text redaction is best effort.</div>
  </section>;
}
