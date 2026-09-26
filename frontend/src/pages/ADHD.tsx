import { useState, useEffect } from 'react'

type Msg = {role: 'user'|'assistant', content: string}

export default function ADHDPage() {
  const [messages, setMessages] = useState<Msg[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [wins, setWins] = useState(0)
  const [focusTask, setFocusTask] = useState('')
  const [timer, setTimer] = useState<number|null>(null)
  const [secondsLeft, setSecondsLeft] = useState(0)

  useEffect(()=>{
    setMessages([{
      role: 'assistant',
      content: `🌅 **JARVIS ADHD Coach — Good morning, Sir.**

I'm your co-pilot for executive dysfunction, time blindness, and overwhelm. No shame, only tiny wins.

**What would help most right now?**

• Brain full? → "brain dump Q4 report, buy milk, call mom, laundry..."
• Big scary task? → "break down write Q4 report"
• Need day plan? → "plan my day MITs: email client, Q4 brief, 5-min tidy energy: medium"
• Can't start? → "focus on Q4 brief"
• Overwhelmed? → "overwhelm" — I'll ground you + pick ONE step
• Did something? → "log win opened doc" — dopamine hit
• Energy low? → "energy check"

**ADHD Rules:**
• Max 3 MITs — constraints are kindness
• One next step, not 10
• 2-min rule: If you can start in 2 min, you win
• Any progress counts, Sir.

What's on your mind?`
    }])
  }, [])

  // Timer effect
  useEffect(()=>{
    if (timer === null || secondsLeft <= 0) return
    const id = setInterval(()=> setSecondsLeft(s=> {
      if (s <= 1) {
        // Timer done
        clearInterval(id)
        setTimer(null)
        // Notify
        if (Notification && Notification.permission === 'granted') {
          new Notification('JARVIS: Focus done, Sir!', {body: `You did ${focusTask} — log win?`})
        }
        setMessages(m=> [...m, {role: 'assistant', content: `🎉 **Focus done, Sir!** ${focusTask ? `You stayed with "${focusTask}" for ${timer} min` : 'Session complete'} — that's a win.\n\nSay "log win ${focusTask}" for dopamine, or take a ${Math.ceil((timer||25)/5)} min break.`}])
        return 0
      }
      return s-1
    }), 1000)
    return ()=> clearInterval(id)
  }, [secondsLeft, timer, focusTask])

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
        body: JSON.stringify({prompt, agent: 'adhd_coach', engine: 'mock'})
      })
      const data = await res.json()
      setMessages(m=>[...m, {role: 'assistant', content: data.content || data.detail || 'Error'}])
      
      // Detect win logging
      if (prompt.toLowerCase().includes('log win') || prompt.toLowerCase().includes('win')) {
        setWins(w=>w+1)
      }
      // Detect focus
      if (prompt.toLowerCase().startsWith('focus on')) {
        const task = prompt.replace(/focus on/i, '').trim()
        setFocusTask(task)
      }
    } catch (e:any) {
      setMessages(m=>[...m, {role: 'assistant', content: `Error: ${e.message}`}])
    } finally {
      setLoading(false)
    }
  }

  const startTimer = (mins: number, task?: string) => {
    if (task) setFocusTask(task)
    setTimer(mins)
    setSecondsLeft(mins*60)
    if (Notification && Notification.permission !== 'granted') {
      Notification.requestPermission()
    }
  }

  const formatTime = (secs: number) => {
    const m = Math.floor(secs/60)
    const s = secs%60
    return `${m}:${s.toString().padStart(2,'0')}`
  }

  return (
    <div style={{display:'flex', height:'100vh', background:'#0f0f12', color:'#e4e4e7', fontFamily:'Inter, system-ui'}}>
      {/* Left */}
      <div style={{width:320, borderRight:'1px solid #27272a', padding:16, display:'flex', flexDirection:'column', gap:14, overflowY:'auto'}}>
        <div style={{textAlign:'center', padding:'8px 0'}}>
          <div style={{fontSize:24, fontWeight:800, color:'#a78bfa'}}>ADHD CO-PILOT</div>
          <div style={{fontSize:11, color:'#71717a'}}>JARVIS • No shame, only tiny wins</div>
          <div style={{marginTop:8, display:'flex', gap:6, justifyContent:'center'}}>
            <div style={{background:'#18181b', border:'1px solid #27272a', borderRadius:20, padding:'4px 10px', fontSize:11}}>🏆 Wins today: {wins}</div>
            <div style={{background:'#18181b', border:'1px solid #27272a', borderRadius:20, padding:'4px 10px', fontSize:11}}>{timer ? `⏱️ ${formatTime(secondsLeft)}` : '● Ready'}</div>
          </div>
        </div>

        {timer !== null && (
          <div style={{background:'#1e1b4b', border:'1px solid #4338ca', borderRadius:12, padding:12, textAlign:'center'}}>
            <div style={{fontSize:12, color:'#a5b4fc'}}>FOCUS ON</div>
            <div style={{fontWeight:700, margin:'4px 0', color:'#c7d2fe'}}>{focusTask || 'MIT'}</div>
            <div style={{fontSize:28, fontWeight:800, fontVariantNumeric:'tabular-nums'}}>{formatTime(secondsLeft)}</div>
            <div style={{fontSize:11, color:'#818cf8', marginTop:4}}>{timer} min session • Stay with it, Sir</div>
            <div style={{display:'flex', gap:6, marginTop:10}}>
              <button onClick={()=>{setTimer(null); setSecondsLeft(0)}} style={{flex:1, background:'#27272a', border:'1px solid #3f3f46', color:'#e4e4e7', borderRadius:8, padding:6, fontSize:11}}>Stop</button>
              <button onClick={()=>send(`distraction ${focusTask} thought`)} style={{flex:1, background:'#27272a', border:'1px solid #3f3f46', color:'#e4e4e7', borderRadius:8, padding:6, fontSize:11}}>Park Distraction</button>
            </div>
          </div>
        )}

        <div style={{background:'#18181b', borderRadius:12, padding:12}}>
          <div style={{fontSize:11, color:'#71717a', textTransform:'uppercase', marginBottom:8, letterSpacing:1}}>Quick Start</div>
          {[
            ["🧠 Brain Dump", "brain dump "],
            ["🔬 Break Down", "break down "],
            ["📅 Plan Day", "plan my day MITs: "],
            ["🎧 Focus 25m", "focus on "],
            ["⚡ Energy Check", "energy check"],
            ["🏆 Log Win", "log win "],
            ["🆘 Overwhelm SOS", "overwhelm"],
            ["⏱️ Time Estimate", "time estimate "],
          ].map(([label, cmd])=>(
            <button key={label} onClick={()=>{
              if (cmd.endsWith(' ')) setInput(cmd)
              else send(cmd)
            }} style={{width:'100%', textAlign:'left', background:'#0f0f12', border:'1px solid #27272a', color:'#e4e4e7', borderRadius:8, padding:'8px 10px', marginBottom:6, fontSize:12, cursor:'pointer'}}>
              {label}
            </button>
          ))}
        </div>

        <div style={{background:'#18181b', borderRadius:12, padding:12}}>
          <div style={{fontSize:11, color:'#71717a', textTransform:'uppercase', marginBottom:8}}>Focus Timers</div>
          <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:6}}>
            <button onClick={()=>startTimer(15, focusTask||'MIT')} style={{background:'#0f0f12', border:'1px solid #27272a', color:'#e4e4e7', borderRadius:8, padding:8, fontSize:11}}>15m sprint</button>
            <button onClick={()=>startTimer(25, focusTask||'MIT')} style={{background:'#0f0f12', border:'1px solid #27272a', color:'#e4e4e7', borderRadius:8, padding:8, fontSize:11}}>25m Pomodoro</button>
            <button onClick={()=>startTimer(45, focusTask||'MIT')} style={{background:'#0f0f12', border:'1px solid #27272a', color:'#e4e4e7', borderRadius:8, padding:8, fontSize:11}}>45m deep</button>
            <button onClick={()=>startTimer(5, 'Break')} style={{background:'#0f0f12', border:'1px solid #27272a', color:'#e4e4e7', borderRadius:8, padding:8, fontSize:11}}>5m break</button>
          </div>
          <div style={{fontSize:10, color:'#52525b', marginTop:8, lineHeight:1.4}}>
            ADHD tip: 15m for low energy, 25m medium, 45m high. Always set break alarm — you will forget.
          </div>
        </div>

        <div style={{background:'#18181b', borderRadius:12, padding:12}}>
          <div style={{fontSize:11, color:'#71717a', textTransform:'uppercase', marginBottom:8}}>Dopamine Menu (2-5 min)</div>
          <div style={{fontSize:11, lineHeight:1.6, color:'#a1a1aa'}}>
            <div>🎵 1 song loud, dance</div>
            <div>💧 Cold water + 10 breaths</div>
            <div>🚶 5-min walk no phone</div>
            <div>🧹 Tidy one surface</div>
            <div>💬 Text someone kind</div>
            <div>📸 Photo of one win</div>
          </div>
        </div>

        <div style={{marginTop:'auto', fontSize:10, color:'#52525b', background:'#18181b', padding:10, borderRadius:8}}>
          <div>💡 ADHD brain not broken, Sir. Needs different OS.</div>
          <div>• Externalize, don't memorize</div>
          <div>• Tiny steps, not big leaps</div>
            <div>• Body double &gt; willpower</div>
            <div>• Wins &gt; perfection</div>
          <div style={{marginTop:6}}>CLI: <code>jarvis ask --agent adhd_coach --mock "brain dump..."</code></div>
        </div>
      </div>

      {/* Center Chat */}
      <div style={{flex:1, display:'flex', flexDirection:'column', background:'#09090b'}}>
        <div style={{padding:'12px 20px', borderBottom:'1px solid #27272a', display:'flex', justifyContent:'space-between', alignItems:'center'}}>
          <div style={{fontWeight:700, color:'#fafafa'}}>ADHD Coach — JARVIS</div>
          <div style={{fontSize:11, color:'#71717a'}}>3 MITs max • One next step • No shame</div>
        </div>

        <div style={{flex:1, overflowY:'auto', padding:20, display:'flex', flexDirection:'column', gap:16}}>
          {messages.map((m,i)=>(
            <div key={i} style={{display:'flex', justifyContent: m.role==='user' ? 'flex-end' : 'flex-start'}}>
              <div style={{maxWidth:'78%', padding:'14px 18px', borderRadius: m.role==='user' ? '18px 18px 4px 18px' : '18px 18px 18px 4px', background: m.role==='user' ? '#a78bfa' : '#18181b', color: m.role==='user' ? '#09090b' : '#e4e4e7', border: m.role==='user' ? 'none' : '1px solid #27272a', whiteSpace:'pre-wrap', fontSize:13.5, lineHeight:1.6}}>
                {m.content}
              </div>
            </div>
          ))}
          {loading && <div style={{color:'#71717a', fontSize:13}}>JARVIS thinking, Sir...</div>}
        </div>

        <div style={{padding:16, borderTop:'1px solid #27272a', display:'flex', gap:10}}>
          <input value={input} onChange={e=>setInput(e.target.value)} onKeyDown={e=> e.key==='Enter' && send()} placeholder="What's on your mind? (brain dump, break down, focus on, log win, overwhelm...)" style={{flex:1, background:'#18181b', border:'1px solid #27272a', color:'#fafafa', borderRadius:24, padding:'12px 18px', fontSize:14, outline:'none'}} />
          <button onClick={()=>send()} disabled={loading} style={{background:'#a78bfa', color:'#09090b', border:'none', borderRadius:24, padding:'12px 20px', fontWeight:700, fontSize:14, cursor:'pointer'}}>{loading ? '...' : 'Send'}</button>
        </div>
      </div>

      {/* Right */}
      <div style={{width:280, borderLeft:'1px solid #27272a', padding:16, display:'flex', flexDirection:'column', gap:12, overflowY:'auto', background:'#0f0f12'}}>
        <div style={{fontSize:11, color:'#71717a', textTransform:'uppercase', letterSpacing:1}}>Today's MITs (max 3)</div>
        
        <div style={{display:'flex', flexDirection:'column', gap:8}}>
          <div style={{background:'#18181b', border:'1px dashed #3f3f46', borderRadius:8, padding:10}}>
            <div style={{fontSize:11, color:'#71717a'}}>MIT 1 — Hardest</div>
            <input placeholder="e.g. Open Q4 doc" style={{width:'100%', background:'transparent', border:'none', color:'#fafafa', fontSize:12, outline:'none', marginTop:4}} onKeyDown={e=> e.key==='Enter' && send(`plan my day MITs: ${(e.target as HTMLInputElement).value}`)} />
          </div>
          <div style={{background:'#18181b', border:'1px dashed #3f3f46', borderRadius:8, padding:10}}>
            <div style={{fontSize:11, color:'#71717a'}}>MIT 2 — Important</div>
            <input placeholder="e.g. Reply to 1 email" style={{width:'100%', background:'transparent', border:'none', color:'#fafafa', fontSize:12, outline:'none', marginTop:4}} />
          </div>
          <div style={{background:'#18181b', border:'1px dashed #3f3f46', borderRadius:8, padding:10}}>
            <div style={{fontSize:11, color:'#71717a'}}>MIT 3 — Bonus</div>
            <input placeholder="e.g. 5-min tidy" style={{width:'100%', background:'transparent', border:'none', color:'#fafafa', fontSize:12, outline:'none', marginTop:4}} />
          </div>
        </div>

        <button onClick={()=>send('plan my day MITs: ' + (document.querySelectorAll('input')[1] as any)?.value)} style={{background:'#27272a', border:'1px solid #3f3f46', color:'#e4e4e7', borderRadius:8, padding:8, fontSize:12}}>Generate Day Plan</button>

        <div style={{fontSize:11, color:'#71717a', textTransform:'uppercase', marginTop:12}}>ADHD Toolkit</div>
        <div style={{display:'grid', gridTemplateColumns:'1fr', gap:6}}>
          <button onClick={()=>send('energy check')} style={{background:'#18181b', border:'1px solid #27272a', color:'#e4e4e7', borderRadius:8, padding:8, fontSize:11, textAlign:'left'}}>⚡ Energy Check → Task Matching</button>
          <button onClick={()=>send('time estimate write report I think 30m')} style={{background:'#18181b', border:'1px solid #27272a', color:'#e4e4e7', borderRadius:8, padding:8, fontSize:11, textAlign:'left'}}>⏱️ Time Blindness Antidote</button>
          <button onClick={()=>send('dopamine menu')} style={{background:'#18181b', border:'1px solid #27272a', color:'#e4e4e7', borderRadius:8, padding:8, fontSize:11, textAlign:'left'}}>🍽️ Dopamine Menu</button>
          <button onClick={()=>send('habit stack existing: make coffee new: open MIT doc')} style={{background:'#18181b', border:'1px solid #27272a', color:'#e4e4e7', borderRadius:8, padding:8, fontSize:11, textAlign:'left'}}>🔗 Habit Stack</button>
          <button onClick={()=>send('if then if: overwhelmed then: 4 breaths + ONE step')} style={{background:'#18181b', border:'1px solid #27272a', color:'#e4e4e7', borderRadius:8, padding:8, fontSize:11, textAlign:'left'}}>🧩 If-Then Planning</button>
          <button onClick={()=>send('transition from: email to: Q4 report')} style={{background:'#18181b', border:'1px solid #27272a', color:'#e4e4e7', borderRadius:8, padding:8, fontSize:11, textAlign:'left'}}>🔄 Transition Helper</button>
          <button onClick={()=>send('weekly review')} style={{background:'#18181b', border:'1px solid #27272a', color:'#e4e4e7', borderRadius:8, padding:8, fontSize:11, textAlign:'left'}}>📅 Weekly Review</button>
          <button onClick={()=>send('shutdown wins: opened doc, 25m focus tomorrow: Q4 brief, email, tidy')} style={{background:'#18181b', border:'1px solid #27272a', color:'#e4e4e7', borderRadius:8, padding:8, fontSize:11, textAlign:'left'}}>🌙 Shutdown Ritual</button>
          <button onClick={()=>send('show wins')} style={{background:'#18181b', border:'1px solid #27272a', color:'#e4e4e7', borderRadius:8, padding:8, fontSize:11, textAlign:'left'}}>🏆 Show Wins & Streak</button>
          <button onClick={()=>send('show distractions')} style={{background:'#18181b', border:'1px solid #27272a', color:'#e4e4e7', borderRadius:8, fontSize:11, padding:8, textAlign:'left'}}>📊 Distraction Patterns</button>
          <button onClick={()=>send('overwhelm')} style={{background:'#27272a', border:'1px solid #ef4444', color:'#fca5a5', borderRadius:8, padding:8, fontSize:11, textAlign:'left'}}>🆘 Overwhelm SOS</button>
        </div>

        <div style={{fontSize:11, color:'#71717a', textTransform:'uppercase', marginTop:12}}>Why this works for ADHD</div>
        <div style={{fontSize:11, color:'#52525b', background:'#18181b', padding:10, borderRadius:8, lineHeight:1.5}}>
          <div><b>Executive dysfunction:</b> 2-min micro-steps, not big tasks</div>
          <div style={{marginTop:6}}><b>Time blindness:</b> Realistic estimates + visual timer + buffers</div>
          <div style={{marginTop:6}}><b>Working memory:</b> Externalize — capture fast, organize later</div>
          <div style={{marginTop:6}}><b>Overwhelm:</b> 3 MITs max, ONE next step, grounding</div>
          <div style={{marginTop:6}}><b>Dopamine:</b> Tiny wins, streaks, dopamine menu, celebration</div>
          <div style={{marginTop:6}}><b>Hyperfocus:</b> Break alarms, body double, transition buffers</div>
          <div style={{marginTop:6}}><b>RSD:</b> No shame, only data. Warm, witty, Sir.</div>
        </div>
      </div>
    </div>
  )
}
