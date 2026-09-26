import { useState, useEffect } from 'react'

type ToolResult = { tool: string, result: string }

export default function IronMan() {
  const [messages, setMessages] = useState<{role: 'user'|'assistant', content: string}[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [systemStatus, setSystemStatus] = useState<any>(null)
  const [lights, setLights] = useState<any>(null)

  useEffect(() => {
    // Load system status
    fetch('/run', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({prompt: 'System status', agent: 'ironman', engine: 'mock'})
    }).then(r=>r.json()).then(d=>setSystemStatus(d.content)).catch(()=>{})

    // Initial greeting
    setMessages([{
      role: 'assistant',
      content: "Good evening, Sir. JARVIS online. Systems nominal, sarcasm module fully operational.\n\nTry:\n- Good morning JARVIS\n- Turn off the lights in the lab\n- What should I work on today?\n- System status\n- I am Iron Man"
    }])
  }, [])

  const send = async (text?: string) => {
    const prompt = text || input
    if (!prompt.trim() || loading) return
    setMessages(m=>[...m, {role: 'user', content: prompt}])
    setInput('')
    setLoading(true)
    try {
      const res = await fetch('/run', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({prompt, agent: 'ironman', engine: 'mock'})
      })
      const data = await res.json()
      setMessages(m=>[...m, {role: 'assistant', content: data.content || data.detail || 'Error'}])
      
      // If lights command, refresh lights
      if (prompt.toLowerCase().includes('light')) {
        // Mock lights state
        setLights({lab: prompt.toLowerCase().includes('off') ? 'off' : 'on'})
      }
    } catch (e:any) {
      setMessages(m=>[...m, {role: 'assistant', content: `Error: ${e.message}` }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{display:'flex', height:'100vh', background:'#0f172a', color:'#e2e8f0', fontFamily:'Inter, system-ui'}}>
      {/* Left - Controls */}
      <div style={{width:320, borderRight:'1px solid #1e293b', padding:16, display:'flex', flexDirection:'column', gap:16, overflowY:'auto'}}>
        <div style={{textAlign:'center'}}>
          <div style={{fontSize:28, fontWeight:800, color:'#22c55e'}}>JARVIS</div>
          <div style={{fontSize:12, color:'#94a3b8'}}>Iron Man Mode • Local-First</div>
          <div style={{marginTop:8, padding:'4px 8px', background:'#1e293b', borderRadius:12, fontSize:11, display:'inline-block'}}>
            ● Mock (offline) • Witty • Device Control
          </div>
        </div>

        <div style={{background:'#1e293b', borderRadius:12, padding:12}}>
          <div style={{fontSize:12, color:'#94a3b8', textTransform:'uppercase', marginBottom:8}}>Quick Actions</div>
          {[
            "Good morning JARVIS",
            "Turn off the lights in the lab",
            "Turn on lab lights to blue",
            "System status",
            "What should I work on today?",
            "Play some music",
            "I am Iron Man",
            "Tell me a joke"
          ].map(cmd=>(
            <button key={cmd} onClick={()=>send(cmd)} style={{width:'100%', textAlign:'left', background:'#0f172a', border:'1px solid #334155', color:'#e2e8f0', borderRadius:8, padding:'8px 10px', marginBottom:6, fontSize:12, cursor:'pointer'}}>
              {cmd}
            </button>
          ))}
        </div>

        <div style={{background:'#1e293b', borderRadius:12, padding:12}}>
          <div style={{fontSize:12, color:'#94a3b8', textTransform:'uppercase', marginBottom:8}}>Lab Systems</div>
          <div style={{fontSize:12, lineHeight:1.6}}>
            <div>💡 Lab Lights: <span style={{color: lights?.lab==='off' ? '#ef4444' : '#22c55e'}}>{lights?.lab || 'on'}</span></div>
            <div>🎵 Music: Playing (mock)</div>
            <div>🔋 Arc Reactor: 104% (kidding, 100%)</div>
            <div>🛡️ Security: Perimeter secure</div>
            <div>💾 Memory: Local FAISS</div>
          </div>
        </div>

        <div style={{background:'#1e293b', borderRadius:12, padding:12}}>
          <div style={{fontSize:12, color:'#94a3b8', textTransform:'uppercase', marginBottom:8}}>System Status</div>
          <div style={{fontSize:11, whiteSpace:'pre-wrap', color:'#94a3b8', maxHeight:120, overflowY:'auto'}}>
            {systemStatus || 'Loading diagnostics...'}
          </div>
        </div>

        <div style={{marginTop:'auto', fontSize:10, color:'#64748b', background:'#1e293b', padding:10, borderRadius:8}}>
          <div>💡 Offline mock works with no internet</div>
          <div>🔊 For voice: pip install faster-whisper + kokoro</div>
          <div>🏠 For real lights: pip install phue + set HUE_BRIDGE_IP</div>
          <div>🏠 For HA: set HASS_URL + HASS_TOKEN</div>
          <div>👁️ For vision: ollama pull llava</div>
          <div style={{marginTop:6}}>CLI: <code>jarvis ironman --engine mock</code></div>
          <div>Voice: <code>jarvis ironman --voice --engine ollama</code></div>
        </div>
      </div>

      {/* Center - Chat */}
      <div style={{flex:1, display:'flex', flexDirection:'column'}}>
        <div style={{padding:'12px 20px', borderBottom:'1px solid #1e293b', display:'flex', justifyContent:'space-between', alignItems:'center'}}>
          <div style={{fontWeight:700}}>Iron Man JARVIS — Interactive</div>
          <div style={{fontSize:11, color:'#94a3b8'}}>Witty • Proactive • Device Control • Offline Mock</div>
        </div>

        <div style={{flex:1, overflowY:'auto', padding:20, display:'flex', flexDirection:'column', gap:16}}>
          {messages.map((m,i)=>(
            <div key={i} style={{display:'flex', justifyContent: m.role==='user' ? 'flex-end' : 'flex-start'}}>
              <div style={{maxWidth:'75%', padding:'12px 16px', borderRadius: m.role==='user' ? '16px 16px 4px 16px' : '16px 16px 16px 4px', background: m.role==='user' ? '#22c55e' : '#1e293b', color: m.role==='user' ? '#0f172a' : '#e2e8f0', border: m.role==='user' ? 'none' : '1px solid #334155', whiteSpace:'pre-wrap', fontSize:14, lineHeight:1.5}}>
                {m.content}
              </div>
            </div>
          ))}
          {loading && <div style={{color:'#94a3b8', fontSize:13}}>JARVIS thinking, Sir...</div>}
        </div>

        <div style={{padding:16, borderTop:'1px solid #1e293b', display:'flex', gap:10}}>
          <input value={input} onChange={e=>setInput(e.target.value)} onKeyDown={e=> e.key==='Enter' && send()} placeholder="Ask JARVIS... (e.g., Good morning, Turn off lights, I am Iron Man)" style={{flex:1, background:'#1e293b', border:'1px solid #334155', color:'#e2e8f0', borderRadius:24, padding:'12px 18px', fontSize:14, outline:'none'}} />
          <button onClick={()=>send()} disabled={loading} style={{background:'#22c55e', color:'#0f172a', border:'none', borderRadius:24, padding:'12px 20px', fontWeight:700, fontSize:14, cursor:'pointer'}}>{loading ? '...' : 'Send'}</button>
        </div>
      </div>

      {/* Right - Tools */}
      <div style={{width:280, borderLeft:'1px solid #1e293b', padding:16, display:'flex', flexDirection:'column', gap:12, overflowY:'auto'}}>
        <div style={{fontSize:12, color:'#94a3b8', textTransform:'uppercase'}}>Device Control</div>
        
        <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:8}}>
          <button onClick={()=>send('Turn on the lights in the lab')} style={{background:'#1e293b', border:'1px solid #334155', color:'#e2e8f0', borderRadius:8, padding:10, fontSize:12}}>💡 Lab On</button>
          <button onClick={()=>send('Turn off the lights in the lab')} style={{background:'#1e293b', border:'1px solid #334155', color:'#e2e8f0', borderRadius:8, padding:10, fontSize:12}}>🌑 Lab Off</button>
          <button onClick={()=>send('Turn on lab lights to blue at 50%')} style={{background:'#1e293b', border:'1px solid #334155', color:'#e2e8f0', borderRadius:8, padding:10, fontSize:12}}>🔵 Blue 50%</button>
          <button onClick={()=>send('Turn on lab lights to red')} style={{background:'#1e293b', border:'1px solid #334155', color:'#e2e8f0', borderRadius:8, padding:10, fontSize:12}}>🔴 Red</button>
          <button onClick={()=>send('Play some music')} style={{background:'#1e293b', border:'1px solid #334155', color:'#e2e8f0', borderRadius:8, padding:10, fontSize:12}}>🎵 Play</button>
          <button onClick={()=>send('System status')} style={{background:'#1e293b', border:'1px solid #334155', color:'#e2e8f0', borderRadius:8, padding:10, fontSize:12}}>🖥️ System</button>
        </div>

        <div style={{fontSize:12, color:'#94a3b8', textTransform:'uppercase', marginTop:12}}>Memory</div>
        <button onClick={()=>send('What should I work on today?')} style={{width:'100%', background:'#0f172a', border:'1px solid #334155', color:'#e2e8f0', borderRadius:8, padding:'8px 10px', fontSize:12, textAlign:'left'}}>📅 What should I work on?</button>
        <button onClick={()=>send('Who are you?')} style={{width:'100%', background:'#0f172a', border:'1px solid #334155', color:'#e2e8f0', borderRadius:8, padding:'8px 10px', fontSize:12, textAlign:'left'}}>🤖 Who are you?</button>

        <div style={{fontSize:12, color:'#94a3b8', textTransform:'uppercase', marginTop:12}}>How to get real devices</div>
        <div style={{fontSize:11, color:'#64748b', background:'#0f172a', padding:10, borderRadius:8, lineHeight:1.5}}>
          <div><b>Hue:</b> pip install phue</div>
          <div>Set HUE_BRIDGE_IP, press button on bridge, run setup</div>
          <div style={{marginTop:6}}><b>Home Assistant:</b></div>
          <div>Set HASS_URL + HASS_TOKEN (long-lived token)</div>
          <div style={{marginTop:6}}><b>Vision:</b> ollama pull llava</div>
          <div><b>Wake word:</b> pip install openwakeword</div>
          <div><b>Voice:</b> pip install faster-whisper kokoro</div>
        </div>
      </div>
    </div>
  )
}
