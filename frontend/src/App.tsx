import { useState, useEffect } from 'react'
import IronMan from './pages/IronMan'

type Agent = string
type Message = { role: 'user' | 'assistant' | 'system', content: string }

const AGENTS = [
  { id: 'ironman', name: 'Iron Man JARVIS', desc: 'Witty, voice-ready, device control' },
  { id: 'simple', name: 'Chat Simple', desc: 'Lightweight chat, no tools' },
  { id: 'native_react', name: 'ReAct', desc: 'Thought-Action-Observation loop' },
  { id: 'orchestrator', name: 'Orchestrator', desc: 'Multi-turn reasoning' },
  { id: 'morning_digest', name: 'Morning Digest', desc: 'Daily briefing' },
  { id: 'deep_research', name: 'Deep Research', desc: 'Multi-hop research with citations' },
  { id: 'code_assistant', name: 'Code Assistant', desc: 'File I/O + shell' },
]

export default function App() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [agent, setAgent] = useState('ironman')
  const [engine, setEngine] = useState('mock')
  const [loading, setLoading] = useState(false)
  const [health, setHealth] = useState<any>(null)
  const [context, setContext] = useState('')
  const [mode, setMode] = useState<'chat' | 'ironman'>('ironman')

  useEffect(() => {
    fetch('/health').then(r=>r.json()).then(setHealth).catch(()=>{})
  }, [])

  if (mode === 'ironman') {
    return (
      <div>
        <div style={{position:'absolute', top:10, right:10, zIndex:10, display:'flex', gap:8}}>
          <button onClick={()=>setMode('chat')} style={{background:'#1e293b', border:'1px solid #334155', color:'#e2e8f0', borderRadius:20, padding:'6px 12px', fontSize:12, cursor:'pointer'}}>Switch to Classic Chat</button>
        </div>
        <IronMan />
      </div>
    )
  }

  const send = async () => {
    if (!input.trim() || loading) return
    const userMsg: Message = { role: 'user', content: input }
    setMessages(m => [...m, userMsg])
    setInput('')
    setLoading(true)
    try {
      const res = await fetch('/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: userMsg.content, context, agent, engine })
      })
      const data = await res.json()
      if (data.content) {
        setMessages(m => [...m, { role: 'assistant', content: data.content }])
      } else if (data.detail) {
        setMessages(m => [...m, { role: 'assistant', content: `Error: ${data.detail}` }])
      }
    } catch (e:any) {
      setMessages(m => [...m, { role: 'assistant', content: `Network error: ${e.message}. Is backend running? Run: jarvis serve` }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ display:'flex', height:'100vh', flexDirection:'column', background:'#0f172a' }}>
      {/* Header */}
      <header style={{ padding:'12px 20px', borderBottom:'1px solid #1e293b', display:'flex', justifyContent:'space-between', alignItems:'center', background:'#0f172a' }}>
        <div style={{ display:'flex', alignItems:'center', gap:12 }}>
          <span style={{ fontWeight:800, fontSize:22, color:'#22c55e' }}>JARVIS</span>
          <span style={{ color:'#94a3b8', fontSize:13 }}>Personal AI, On Personal Devices</span>
          <span style={{ fontSize:11, padding:'2px 8px', background:'#1e293b', borderRadius:12, color: health ? '#22c55e' : '#f59e0b' }}>
            {health ? `● v${health.version || '0.1.0'} · ${health.status}` : '○ offline — run jarvis serve'}
          </span>
        </div>
        <div style={{ display:'flex', gap:8, alignItems:'center' }}>
          <select value={agent} onChange={e=>setAgent(e.target.value)} style={{ background:'#1e293b', color:'#e2e8f0', border:'1px solid #334155', borderRadius:6, padding:'6px 10px' }}>
            {AGENTS.map(a=> <option key={a.id} value={a.id}>{a.name}</option>)}
          </select>
          <select value={engine} onChange={e=>setEngine(e.target.value)} style={{ background:'#1e293b', color:'#e2e8f0', border:'1px solid #334155', borderRadius:6, padding:'6px 10px' }}>
            <option value="mock">mock (offline)</option>
            <option value="openai">openai</option>
            <option value="ollama">ollama (local)</option>
          </select>
        </div>
      </header>

      <div style={{ display:'flex', flex:1, overflow:'hidden' }}>
        {/* Sidebar */}
        <aside style={{ width:280, borderRight:'1px solid #1e293b', padding:16, display:'flex', flexDirection:'column', gap:16, background:'#0f172a' }}>
          <div>
            <h3 style={{ margin:'0 0 8px', fontSize:13, color:'#94a3b8', textTransform:'uppercase', letterSpacing:1 }}>Agents</h3>
            {AGENTS.map(a=> (
              <div key={a.id} onClick={()=>setAgent(a.id)} style={{ padding:'8px 10px', borderRadius:8, cursor:'pointer', background: agent===a.id ? '#1e293b' : 'transparent', border: agent===a.id ? '1px solid #334155' : '1px solid transparent', marginBottom:6 }}>
                <div style={{ fontWeight:600, fontSize:13 }}>{a.name}</div>
                <div style={{ fontSize:11, color:'#94a3b8' }}>{a.desc}</div>
              </div>
            ))}
          </div>

          <div>
            <h3 style={{ margin:'0 0 8px', fontSize:13, color:'#94a3b8', textTransform:'uppercase' }}>Context / Files</h3>
            <textarea value={context} onChange={e=>setContext(e.target.value)} placeholder="Paste meeting details, task context, or file contents..." style={{ width:'100%', height:120, background:'#1e293b', color:'#e2e8f0', border:'1px solid #334155', borderRadius:8, padding:10, fontSize:12, resize:'vertical' }} />
          </div>

          <div style={{ marginTop:'auto', padding:10, background:'#1e293b', borderRadius:8, fontSize:11, color:'#94a3b8' }}>
            <div>💡 Local-first: runs on device</div>
            <div>🔒 Private by default</div>
            <div>⚡ Mock works offline</div>
            <div style={{ marginTop:8 }}>
              CLI: <code>jarvis ask "hello" --mock</code><br/>
              Server: <code>jarvis serve</code><br/>
              Desktop: <code>python app.py</code>
            </div>
          </div>
        </aside>

        {/* Chat */}
        <main style={{ flex:1, display:'flex', flexDirection:'column', background:'#0f172a' }}>
          <div style={{ flex:1, overflowY:'auto', padding:20, display:'flex', flexDirection:'column', gap:16 }}>
            {messages.length===0 && (
              <div style={{ textAlign:'center', marginTop:60, color:'#94a3b8' }}>
                <div style={{ fontSize:32, marginBottom:12 }}>🤖</div>
                <div style={{ fontSize:18, fontWeight:600, color:'#e2e8f0' }}>Welcome to JARVIS</div>
                <div style={{ fontSize:13, maxWidth:460, margin:'8px auto' }}>
                  Personal AI that runs locally. Choose an agent, type a prompt, and generate. Works offline with mock engine, or set OPENAI_API_KEY / run Ollama for real inference.
                </div>
                <div style={{ display:'flex', gap:8, justifyContent:'center', marginTop:16, flexWrap:'wrap' }}>
                  {[
                    "Build a meeting brief from Q4 planning notes",
                    "Explain this Python code: for i in range(5): print(i*2)",
                    "Generate my morning digest",
                    "Research: What is Intelligence Per Watt?"
                  ].map(s=>(
                    <button key={s} onClick={()=>setInput(s)} style={{ background:'#1e293b', border:'1px solid #334155', color:'#e2e8f0', borderRadius:20, padding:'6px 12px', fontSize:12 }}>{s}</button>
                  ))}
                </div>
              </div>
            )}
            {messages.map((m,i)=>(
              <div key={i} style={{ display:'flex', justifyContent: m.role==='user' ? 'flex-end' : 'flex-start' }}>
                <div style={{ maxWidth:'75%', padding:'12px 16px', borderRadius: m.role==='user' ? '16px 16px 4px 16px' : '16px 16px 16px 4px', background: m.role==='user' ? '#22c55e' : '#1e293b', color: m.role==='user' ? '#0f172a' : '#e2e8f0', border: m.role==='user' ? 'none' : '1px solid #334155', whiteSpace:'pre-wrap', fontSize:14, lineHeight:1.5 }}>
                  {m.content}
                </div>
              </div>
            ))}
            {loading && <div style={{ color:'#94a3b8', fontSize:13 }}>Generating with {agent} via {engine}...</div>}
          </div>

          <div style={{ padding:16, borderTop:'1px solid #1e293b', display:'flex', gap:10, background:'#0f172a' }}>
            <input value={input} onChange={e=>setInput(e.target.value)} onKeyDown={e=> e.key==='Enter' && send()} placeholder={`Ask ${AGENTS.find(a=>a.id===agent)?.name || agent}...`} style={{ flex:1, background:'#1e293b', border:'1px solid #334155', color:'#e2e8f0', borderRadius:24, padding:'12px 18px', fontSize:14, outline:'none' }} />
            <button onClick={send} disabled={loading} style={{ background:'#22c55e', color:'#0f172a', border:'none', borderRadius:24, padding:'12px 20px', fontWeight:700, fontSize:14 }}>{loading ? '...' : 'Send'}</button>
          </div>
        </main>
      </div>
    </div>
  )
}
