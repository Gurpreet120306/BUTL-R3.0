import { useState } from 'react';
import { Bot, Send, LoaderCircle, MessageSquare, Database } from 'lucide-react';
import { api } from '../services/api';
export default function ChatPanel() {
  const [messages, setMessages] = useState([]), [question, setQuestion] = useState(''), [busy, setBusy] = useState(false), [error, setError] = useState('');
  async function send(e) {
    e.preventDefault(); const text = question.trim(); if (!text || busy) return;
    setBusy(true); setError(''); setQuestion(''); setMessages(m => [...m, { role: 'user', text }]);
    try { const data = await api('/assistant/ask', { method: 'POST', body: { question: text } }); setMessages(m => [...m, { role: 'assistant', text: data.answer, ids: data.source_observation_ids, warning: data.memory_error }]); }
    catch(e) { setError(e.message); setQuestion(text); }
    finally { setBusy(false); }
  }
  return <section className="panel chat-panel"><div className="panel-heading"><div><span className="eyebrow"><MessageSquare size={14}/> GROUNDED IN YOUR MEMORY</span><h2>Ask BUTL-R</h2></div><span className="assistant-avatar"><Bot size={21}/></span></div>
    <div className="chat-messages" aria-live="polite">{messages.length === 0 && <div className="chat-empty"><div className="orb"><Bot size={30}/></div><h3>Your context, connected.</h3><p>Ask about a past error, a screen you saved,<br/>or what you were working on.</p><div className="suggestions">{['What error did I encounter earlier?', 'What was I working on recently?'].map(q => <button key={q} onClick={() => setQuestion(q)}>{q}<span>↗</span></button>)}</div></div>}{messages.map((m,i) => <div key={i} className={`message ${m.role}`}><small>{m.role === 'user' ? 'YOU' : 'BUTL-R'}</small><p>{m.text}</p>{m.ids?.length > 0 && <div className="source-list"><Database size={12}/><span>Retrieved context: {m.ids.join(', ')}</span></div>}{m.warning && <p className="warning">{m.warning}</p>}</div>)}{busy && <p className="muted flex items-center gap-2"><LoaderCircle className="spin" size={16}/> Thinking locally…</p>}</div>
    {error && <p className="error" role="alert">{error}</p>}<form className="chat-form" onSubmit={send}><textarea aria-label="Ask BUTL-R" placeholder="Ask about your saved context…" value={question} maxLength={4000} rows={2} onChange={e => setQuestion(e.target.value)} onKeyDown={e => { if(e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(e); } }}/><button aria-label="Send question" disabled={busy || !question.trim()} type="submit"><Send size={18}/></button></form><p className="chat-disclaimer">Local AI can make mistakes. Check the supporting memories.</p>
  </section>;
}
