import { useState, useEffect, useRef } from 'react'
import ArcReactor3D from './ArcReactor3D'

type Msg = {role: 'user'|'assistant', content: string, time?: string}

export default function IronManHUD() {
  const [messages, setMessages] = useState<Msg[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [time, setTime] = useState(new Date())
  const [arcPower, setArcPower] = useState(97)
  const [systemStatus, setSystemStatus] = useState({cpu: 12, mem: 34, net: 89, sec: 100})
  const [isListening, setIsListening] = useState(false)
  const [userName, setUserName] = useState('Eugene')
  const [tasksToday, setTasksToday] = useState<string[]>([])
  const [mits, setMits] = useState<string[]>(['Q4 Planning Brief', 'Client Email Response', 'Lab Diagnostics'])
  const [weather, setWeather] = useState<string>('Sunny 24°C • Nairobi • Light breeze')
  const [calendarEvents, setCalendarEvents] = useState<string[]>(['10:00 AM — Q4 Planning Prep', '2:00 PM — Q4 Planning Meeting', '4:30 PM — Client Call'])
  const [emails, setEmails] = useState<{from:string, subject:string, unread:boolean}[]>([
    {from:'Client', subject:'Need Q4 brief by Friday', unread:true},
    {from:'Team', subject:'Project update — on track', unread:true},
    {from:'Newsletter', subject:'Weekly digest', unread:false},
  ])
  const [energyPattern, setEnergyPattern] = useState('High focus 10-11am — MIT 1 then')
  const [onlineStatus, setOnlineStatus] = useState<{online:boolean, engine:string, mode:string, latency?:number}>({online: typeof navigator !== "undefined" ? navigator.onLine : true, engine: 'auto', mode: 'CHECKING'})
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const waveformRef = useRef<HTMLCanvasElement>(null)
  const audioContextRef = useRef<AudioContext | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)

  // Online/offline detection + auto engine
  useEffect(()=>{
    const checkOnline = async () => {
      const isOnline = typeof navigator !== "undefined" ? navigator.onLine : true
      let engine = 'mock'
      let mode = 'BASIC OFFLINE'
      let latency: number | undefined

      if (isOnline) {
        try {
          const start = Date.now()
          const res = await fetch('/run', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({prompt: 'network_status check', agent: 'ironman', engine: 'mock'})
          })
          const data = await res.json()
          if (data.content) {
            const content = data.content as string
            if (content.includes('ONLINE')) {
              engine = content.includes('openai') ? 'openai' : content.includes('ollama') ? 'ollama' : 'mock'
              mode = engine === 'openai' ? 'FULL STACK ONLINE' : engine === 'ollama' ? 'FULL LOCAL ONLINE' : 'ONLINE BUT BASIC'
            }
          }
          latency = Date.now() - start
        } catch {
          engine = 'mock'
          mode = 'ONLINE BUT BASIC'
        }
      }

      setOnlineStatus({online: isOnline, engine, mode, latency})
      setSystemStatus(s=> ({...s, net: isOnline ? 89 : 0}))
    }

    checkOnline()
    if (typeof window !== "undefined") {
      window.addEventListener('online', checkOnline)
      window.addEventListener('offline', checkOnline)
    }
    const id = setInterval(checkOnline, 30000)

    return ()=>{
      if (typeof window !== "undefined") {
        window.removeEventListener('online', checkOnline)
        window.removeEventListener('offline', checkOnline)
      }
      clearInterval(id)
    }
  }, [])

  // Clock + arc reactor pulse
  useEffect(()=>{
    const id = setInterval(()=> {
      setTime(new Date())
      setArcPower(p => Math.min(100, Math.max(94, p + (Math.random()-0.5)*0.8)))
      setSystemStatus(s=> ({
        cpu: Math.max(5, Math.min(90, s.cpu + (Math.random()-0.5)*3)),
        mem: Math.max(20, Math.min(80, s.mem + (Math.random()-0.5)*2)),
        net: Math.max(70, Math.min(100, s.net + (Math.random()-0.5)*2)),
        sec: 100
      }))
    }, 1000)
    return ()=> clearInterval(id)
  }, [])

  // Arc reactor canvas
  useEffect(()=>{
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    let animId: number
    let rotation = 0
    const draw = () => {
      const w = canvas.width, h = canvas.height
      ctx.clearRect(0,0,w,h)
      const cx = w/2, cy = h/2
      rotation += 0.005

      // Outer glow
      const grad = ctx.createRadialGradient(cx,cy,0,cx,cy,80)
      grad.addColorStop(0, 'rgba(34,197,94,0.8)')
      grad.addColorStop(0.3, 'rgba(34,197,94,0.3)')
      grad.addColorStop(0.6, 'rgba(34,197,94,0.1)')
      grad.addColorStop(1, 'rgba(34,197,94,0)')
      ctx.fillStyle = grad
      ctx.beginPath()
      ctx.arc(cx,cy,80,0,Math.PI*2)
      ctx.fill()

      // Outer ring
      ctx.strokeStyle = `rgba(34,197,94,${0.8 + Math.sin(rotation*3)*0.2})`
      ctx.lineWidth = 2
      ctx.beginPath()
      ctx.arc(cx,cy,55,0,Math.PI*2)
      ctx.stroke()

      // Rotating segments
      for (let i=0;i<3;i++) {
        const angle = rotation + i*Math.PI*2/3
        ctx.strokeStyle = 'rgba(34,211,238,0.9)'
        ctx.lineWidth = 3
        ctx.beginPath()
        ctx.arc(cx,cy,42, angle, angle+Math.PI/2.5)
        ctx.stroke()
      }

      // Inner core
      ctx.fillStyle = `rgba(34,197,94,${0.9 + Math.sin(rotation*5)*0.1})`
      ctx.beginPath()
      ctx.arc(cx,cy,18,0,Math.PI*2)
      ctx.fill()
      ctx.fillStyle = 'rgba(255,255,255,0.9)'
      ctx.beginPath()
      ctx.arc(cx,cy,8,0,Math.PI*2)
      ctx.fill()

      // Tick marks
      ctx.strokeStyle = 'rgba(34,197,94,0.4)'
      ctx.lineWidth = 1
      for (let i=0;i<36;i++) {
        const a = i*Math.PI/18
        const r1 = i%3===0 ? 65 : 60
        const r2 = 70
        ctx.beginPath()
        ctx.moveTo(cx+Math.cos(a)*r1, cy+Math.sin(a)*r1)
        ctx.lineTo(cx+Math.cos(a)*r2, cy+Math.sin(a)*r2)
        ctx.stroke()
      }

      animId = requestAnimationFrame(draw)
    }
    draw()
    return ()=> cancelAnimationFrame(animId)
  }, [])

  // Real voice waveform from mic + mock fallback
  useEffect(()=>{
    const canvas = waveformRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    let animId: number

    const drawMock = () => {
      const w = canvas.width, h = canvas.height
      ctx.clearRect(0,0,w,h)
      ctx.strokeStyle = isListening ? 'rgba(239,68,68,0.9)' : 'rgba(34,197,94,0.9)'
      ctx.lineWidth = 2
      ctx.beginPath()
      for (let x=0;x<w;x++) {
        const y = h/2 + Math.sin(x*0.05 + Date.now()*0.01)*Math.random()*20 + Math.sin(x*0.02)*10
        if (x===0) ctx.moveTo(x,y)
        else ctx.lineTo(x,y)
      }
      ctx.stroke()
      if (isListening || Math.random()>0.3) {
        animId = requestAnimationFrame(drawMock)
      }
    }

    const drawReal = () => {
      if (!analyserRef.current) {
        drawMock()
        return
      }
      const analyser = analyserRef.current
      const bufferLength = analyser.frequencyBinCount
      const dataArray = new Uint8Array(bufferLength)
      const w = canvas.width, h = canvas.height

      const draw = () => {
        if (!isListening) {
          ctx.clearRect(0,0,w,h)
          return
        }
        analyser.getByteTimeDomainData(dataArray)
        ctx.clearRect(0,0,w,h)
        ctx.strokeStyle = 'rgba(239,68,68,0.9)'
        ctx.lineWidth = 2
        ctx.beginPath()
        const sliceWidth = w / bufferLength
        let x = 0
        for (let i=0;i<bufferLength;i++) {
          const v = dataArray[i] / 128.0
          const y = v * h/2
          if (i===0) ctx.moveTo(x,y)
          else ctx.lineTo(x,y)
          x += sliceWidth
        }
        ctx.stroke()
        animId = requestAnimationFrame(draw)
      }
      draw()
    }

    if (isListening && analyserRef.current) {
      drawReal()
    } else {
      drawMock()
    }

    return ()=> cancelAnimationFrame(animId)
  }, [isListening])

  // Fetch weather, calendar, email on load
  useEffect(()=>{
    // Weather via wttr.in or mock
    fetch('/run', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({prompt: 'weather in Nairobi', agent: 'ironman', engine: 'mock'})
    }).then(r=>r.json()).then(d=>{
      if (d.content) {
        const firstLine = d.content.split('\n')[0]
        setWeather(firstLine.replace(/\*\*/g,'').slice(0,60))
      }
    }).catch(()=>{})

    // Calendar
    fetch('/run', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({prompt: 'calendar today', agent: 'ironman', engine: 'mock'})
    }).then(r=>r.json()).then(d=>{
      if (d.content && d.content.includes('•')) {
        const events = d.content.split('\n').filter((l:string)=> l.includes('•')).map((l:string)=> l.replace(/.*•/,'').trim()).slice(0,3)
        if (events.length>0) setCalendarEvents(events)
      }
    }).catch(()=>{})
  }, [])

  // Initial greeting - Good Morning Eugene
  useEffect(()=>{
    const hour = new Date().getHours()
    const greeting = hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening'
    
    // Try to get name from localStorage or config
    const savedName = localStorage.getItem('jarvis_user_name') || 'Eugene'
    setUserName(savedName)
    
    // Load tasks from localStorage (ADHD tasks)
    const savedTasks = localStorage.getItem('jarvis_today_tasks')
    if (savedTasks) {
      try { setTasksToday(JSON.parse(savedTasks)) } catch {}
    }
    
    const savedMits = localStorage.getItem('jarvis_mits')
    if (savedMits) {
      try { setMits(JSON.parse(savedMits)) } catch {}
    }

    // Good morning message like Iron Man
    setTimeout(()=>{
      setMessages([{
        role: 'assistant',
        content: `${greeting}, ${savedName}. It's ${new Date().toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})} on ${new Date().toLocaleDateString([], {weekday:'long', month:'long', day:'numeric'})}.\n\nArc reactor at ${arcPower.toFixed(1)}% — kidding, Sir, we're at 100%. All systems nominal. Lab secure, perimeter clear.\n\n**Today's Alignment — 3 MITs to make today a win:**\n${mits.map((m,i)=> `${i+1}. ${m}`).join('\n')}\n\n**Schedule:** You have 3 meetings today, including Q4 planning at 2 PM. I've prepared a brief — shall I display it?\n\n**Energy:** Based on your pattern, you're usually high focus 10-11am. Recommend tackling MIT 1 then.\n\n**What would you like to do first, Sir?**\n\n• Say "Show my tasks" for full list\n• "Focus on Q4 brief" to start Pomodoro with body double\n• "Brain dump" if mind feels full\n• "System diagnostics" for full report`,
        time: new Date().toLocaleTimeString()
      }])
    }, 500)
  }, [])

  const send = async (text?: string) => {
    const prompt = text || input
    if (!prompt.trim() || loading) return
    
    const userMsg: Msg = {role: 'user', content: prompt, time: new Date().toLocaleTimeString()}
    setMessages(m=>[...m, userMsg])
    setInput('')
    setLoading(true)

    // Simulate listening
    setIsListening(true)
    setTimeout(()=> setIsListening(false), 800)

    try {
      // Determine agent: if ADHD keywords, use adhd_coach, else ironman, if briefing use proactive
      const lower = prompt.toLowerCase()
      const isBriefing = lower.includes('good morning') || lower.includes('briefing') || lower.includes('today') || lower.includes('alignment')
      const isAdhd = lower.includes('brain dump') || lower.includes('break down') || lower.includes('focus on') || lower.includes('mit') || lower.includes('overwhelm') || lower.includes('energy') || lower.includes('win') || lower.includes('plan my day')
      let agent = 'ironman'
      if (isBriefing) agent = 'ironman'
      else if (isAdhd) agent = 'adhd_coach'

      // For briefing, use proactive_briefing tool via ironman agent with special prompt
      let finalPrompt = prompt
      if (isBriefing && lower.includes('good morning')) {
        finalPrompt = `proactive briefing for ${userName} with weather, calendar, email, tasks`
      }

      const res = await fetch('/run', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({prompt: finalPrompt, agent, engine: 'mock'})
      })
      const data = await res.json()
      
      // If tasks mentioned, update tasks
      if (lower.includes('mit') || lower.includes('task')) {
        // Try to extract tasks
        const tasks = prompt.split(/,|\n/).map(t=>t.replace(/mits?:?/i,'').trim()).filter(t=>t.length>3 && t.length<60).slice(0,3)
        if (tasks.length>0) {
          setMits(tasks)
          localStorage.setItem('jarvis_mits', JSON.stringify(tasks))
        }
      }

      // TTS speak response (short)
      try {
        if ('speechSynthesis' in window) {
          const utter = new SpeechSynthesisUtterance((data.content || '').split('\n').slice(0,2).join('. ').slice(0,200))
          utter.rate = 1.1
          // Try British voice
          const voices = speechSynthesis.getVoices()
          const british = voices.find(v=> v.name.toLowerCase().includes('british') || v.name.toLowerCase().includes('uk'))
          if (british) utter.voice = british
          speechSynthesis.speak(utter)
        }
      } catch {}

      setMessages(m=>[...m, {role: 'assistant', content: data.content || data.detail || 'Error, Sir. Systems glitching.', time: new Date().toLocaleTimeString()}])
    } catch (e:any) {
      setMessages(m=>[...m, {role: 'assistant', content: `Comms down, Sir. ${e.message}. Running offline mock.`, time: new Date().toLocaleTimeString()}])
    } finally {
      setLoading(false)
    }
  }

  const startVoice = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({audio:true})
      const audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)()
      const analyser = audioCtx.createAnalyser()
      const source = audioCtx.createMediaStreamSource(stream)
      source.connect(analyser)
      analyser.fftSize = 2048
      audioContextRef.current = audioCtx
      analyserRef.current = analyser
      setIsListening(true)
      
      // Simple speech recognition if available
      const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
      if (SpeechRecognition) {
        const rec = new SpeechRecognition()
        rec.continuous = false
        rec.interimResults = false
        rec.lang = 'en-US'
        rec.onresult = (event:any) => {
          const transcript = event.results[0][0].transcript
          setInput(transcript)
          send(transcript)
          setIsListening(false)
          stream.getTracks().forEach(t=>t.stop())
        }
        rec.onerror = () => {
          setIsListening(false)
          stream.getTracks().forEach(t=>t.stop())
        }
        rec.onend = () => {
          setIsListening(false)
        }
        rec.start()
      } else {
        // No speech recognition, just show waveform for 3 sec
        setTimeout(()=>{
          setIsListening(false)
          stream.getTracks().forEach(t=>t.stop())
        }, 3000)
      }
    } catch (e) {
      console.error('Mic failed', e)
      setIsListening(!isListening)
    }
  }

  return (
    <div style={{height:'100vh', background:'#020208', color:'#22c55e', fontFamily:'"JetBrains Mono", "Share Tech Mono", monospace', overflow:'hidden', position:'relative'}}>
      {/* Background grid */}
      <div style={{position:'absolute', inset:0, backgroundImage: `linear-gradient(rgba(34,197,94,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(34,197,94,0.03) 1px, transparent 1px)`, backgroundSize:'40px 40px'}} />
      
      {/* Scanline effect */}
      <div style={{position:'absolute', inset:0, background: 'repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(34,197,94,0.03) 2px, rgba(34,197,94,0.03) 4px)', pointerEvents:'none'}} />

      {/* Header HUD */}
      <div style={{position:'relative', display:'flex', justifyContent:'space-between', alignItems:'center', padding:'12px 24px', borderBottom:'1px solid rgba(34,197,94,0.3)', background:'rgba(2,2,8,0.9)', backdropFilter:'blur(10px)', zIndex:10}}>
        <div style={{display:'flex', alignItems:'center', gap:20}}>
          <div style={{display:'flex', alignItems:'center', gap:10}}>
            <div style={{width:10, height:10, borderRadius:'50%', background:'#22c55e', boxShadow:'0 0 10px #22c55e', animation:'pulse 2s infinite'}} />
            <span style={{fontWeight:800, letterSpacing:2, fontSize:18}}>J.A.R.V.I.S</span>
            <span style={{fontSize:10, opacity:0.6, border:'1px solid #22c55e', padding:'2px 6px', borderRadius:4}}>MARK XLII</span>
          </div>
          <div style={{fontSize:11, opacity:0.7}}>
            SHILATECH • {time.toLocaleTimeString()} • {time.toLocaleDateString()}
          </div>
        </div>
        
        <div style={{display:'flex', alignItems:'center', gap:16, fontSize:11}}>
          <div>USER: {userName.toUpperCase()}</div>
          <div style={{display:'flex', alignItems:'center', gap:6}}>
            <button onClick={()=> setShowDecision(v=>!v)} title="Click to decide Full Stack vs Basic — interactive, Sir" style={{
              padding:'3px 8px', 
              background: onlineStatus.online ? 'rgba(34,197,94,0.2)' : 'rgba(239,68,68,0.2)', 
              border:`1px solid ${onlineStatus.online ? '#22c55e' : '#ef4444'}`, 
              borderRadius:4,
              color: onlineStatus.online ? '#22c55e' : '#fca5a5',
              display:'flex', alignItems:'center', gap:4,
              cursor:'pointer'
            }}>
              <span style={{width:6, height:6, borderRadius:'50%', background: onlineStatus.online ? '#22c55e' : '#ef4444', display:'inline-block', boxShadow: `0 0 5px ${onlineStatus.online ? '#22c55e' : '#ef4444'}`}} />
              {forcedMode==='basic' && onlineStatus.online ? `ONLINE BASIC LOCAL • CLICK` : onlineStatus.online ? `ONLINE ${onlineStatus.engine.toUpperCase()} ${onlineStatus.latency ? onlineStatus.latency+'ms' : ''} • FULL • CLICK TO DECIDE` : 'OFFLINE BASIC • SHILATECH'}
            </button>
            <span style={{padding:'3px 8px', background:'rgba(34,197,94,0.2)', border:'1px solid #22c55e', borderRadius:4, fontSize:9}}>{onlineStatus.mode}</span>
          </div>
          <div style={{display:'flex', gap:8}}>
            <span style={{padding:'3px 8px', background:'rgba(34,197,94,0.2)', border:'1px solid #22c55e', borderRadius:4}}>CPU {systemStatus.cpu.toFixed(0)}%</span>
            <span style={{padding:'3px 8px', background:'rgba(34,211,238,0.2)', border:'1px solid #22d3ee', borderRadius:4, color:'#22d3ee'}}>MEM {systemStatus.mem.toFixed(0)}%</span>
            <span style={{padding:'3px 8px', background:'rgba(34,197,94,0.2)', border:'1px solid #22c55e', borderRadius:4}}>ARC {arcPower.toFixed(1)}%</span>
          </div>
          <div style={{width:120, height:4, background:'rgba(34,197,94,0.2)', borderRadius:2, overflow:'hidden'}}>
            <div style={{width:`${arcPower}%`, height:'100%', background:'#22c55e', boxShadow:'0 0 10px #22c55e', transition:'width 0.5s'}} />
          </div>
        </div>
      </div>

      {showDecision && onlineStatus.online && (
        <div style={{position:'absolute', top:52, left:'50%', transform:'translateX(-50%)', zIndex:50, width:640, maxWidth:'90vw', border:'1px solid #22c55e', borderRadius:8, background:'rgba(0,0,0,0.9)', backdropFilter:'blur(10px)', padding:16, boxShadow:'0 0 40px rgba(34,197,94,0.3)'}}>
          <div style={{fontSize:12, letterSpacing:1, color:'#22c55e', marginBottom:12, display:'flex', justifyContent:'space-between'}}><span>ONLINE — INTERACTIVE DECISION — SHILATECH</span><button onClick={()=>setShowDecision(false)} style={{background:'none', border:'none', color:'#666', cursor:'pointer'}}>✕</button></div>
          <div style={{fontSize:11, opacity:0.7, marginBottom:12}}>Same circular interface, Sir. JARVIS stays interactive like offline — you decide Full Stack vs Basic.</div>
          <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:12}}>
            <button onClick={()=>decideMode('1')} style={{border:'1px solid #22c55e', borderRadius:6, padding:12, background:'rgba(34,197,94,0.1)', textAlign:'left', cursor:'pointer', color:'#22c55e'}}>
              <div style={{fontWeight:800, fontSize:11}}>1. FULL STACK ONLINE</div>
              <div style={{fontSize:10, opacity:0.7, marginTop:6, color:'#aaa'}}>OpenAI if key set — prompt HTTPS encrypted, best quality, no RAM for i5-6300U 8GB. Or Ollama local — LLM stays device even online, only search online. Badge ONLINE FULL STACK.</div>
            </button>
            <button onClick={()=>decideMode('2')} style={{border:'1px solid #eab308', borderRadius:6, padding:12, background:'rgba(234,179,8,0.1)', textAlign:'left', cursor:'pointer', color:'#eab308'}}>
              <div style={{fontWeight:800, fontSize:11}}>2. BASIC OFFLINE LOCAL EVEN ONLINE</div>
              <div style={{fontSize:10, opacity:0.7, marginTop:6, color:'#aaa'}}>Nothing leaves device, 100% private, SHILATECH secure. mock or tinyllama 1.1B local. Same interface, only badge changes to BASIC LOCAL.</div>
            </button>
          </div>
        </div>
      )}
      <div style={{display:'flex', height:'calc(100vh - 52px)', position:'relative', zIndex:1}}>
        {/* Left Panel - Arc Reactor + Systems */}
        <div style={{width:280, borderRight:'1px solid rgba(34,197,94,0.2)', background:'rgba(2,2,8,0.8)', backdropFilter:'blur(10px)', padding:16, display:'flex', flexDirection:'column', gap:16, overflowY:'auto'}}>
          {/* Arc Reactor — 3D */}
          <div style={{textAlign:'center', padding:'10px 0', border:'1px solid rgba(34,197,94,0.3)', background:'rgba(34,197,94,0.05)', borderRadius:8}}>
            <ArcReactor3D size={160} power={arcPower} />
            <div style={{fontSize:9, opacity:0.6, marginTop:4}}>OUTPUT: 3.2 GJ/s • TEMP: 284K • HOVER BOOST</div>
          </div>
          {/* Hidden canvas ref for legacy */}
          <canvas ref={canvasRef} width={1} height={1} style={{display:'none'}} />

          {/* Today's Alignment */}
          <div style={{border:'1px solid rgba(34,197,94,0.3)', borderRadius:8, padding:12, background:'rgba(34,197,94,0.05)'}}>
            <div style={{fontSize:11, letterSpacing:1, opacity:0.7, marginBottom:8, display:'flex', justifyContent:'space-between'}}>
              <span>TODAY'S ALIGNMENT • 3 MITS</span>
              <span style={{color:'#22d3ee'}}>● LIVE</span>
            </div>
            {mits.map((mit,i)=>(
              <div key={i} style={{display:'flex', gap:8, padding:'8px 0', borderBottom: i<mits.length-1 ? '1px solid rgba(34,197,94,0.1)' : 'none'}}>
                <div style={{width:20, height:20, borderRadius:'50%', border:'1px solid #22c55e', display:'flex', alignItems:'center', justifyContent:'center', fontSize:10, flexShrink:0}}>{i+1}</div>
                <div style={{fontSize:12, lineHeight:1.3}}>{mit}</div>
              </div>
            ))}
            <button onClick={()=>send('plan my day MITs: ' + mits.join(', '))} style={{width:'100%', marginTop:10, background:'rgba(34,197,94,0.2)', border:'1px solid #22c55e', color:'#22c55e', borderRadius:4, padding:'6px', fontSize:10, letterSpacing:1, cursor:'pointer'}}>RE-ALIGN DAY</button>
          </div>

          {/* System Diagnostics */}
          <div style={{border:'1px solid rgba(34,211,238,0.3)', borderRadius:8, padding:12, background:'rgba(34,211,238,0.05)'}}>
            <div style={{fontSize:11, letterSpacing:1, opacity:0.7, marginBottom:8, color:'#22d3ee'}}>SYSTEM DIAGNOSTICS</div>
            {[
              {label:'NEURAL NET', val: systemStatus.cpu, color:'#22c55e'},
              {label:'MEMORY CORE', val: systemStatus.mem, color:'#22d3ee'},
              {label:'COMMS ARRAY', val: systemStatus.net, color:'#a78bfa'},
              {label:'SECURITY', val: systemStatus.sec, color:'#22c55e'},
            ].map(s=>(
              <div key={s.label} style={{marginBottom:8}}>
                <div style={{display:'flex', justifyContent:'space-between', fontSize:9, opacity:0.7}}>
                  <span>{s.label}</span><span>{s.val.toFixed(0)}%</span>
                </div>
                <div style={{height:4, background:'rgba(255,255,255,0.1)', borderRadius:2, overflow:'hidden', marginTop:2}}>
                  <div style={{width:`${s.val}%`, height:'100%', background:s.color, boxShadow:`0 0 5px ${s.color}`}} />
                </div>
              </div>
            ))}
          </div>

          {/* Quick Actions - Iron Man Style */}
          <div style={{border:'1px solid rgba(168,85,247,0.3)', borderRadius:8, padding:12, background:'rgba(168,85,247,0.05)'}}>
            <div style={{fontSize:11, letterSpacing:1, opacity:0.7, marginBottom:8, color:'#a78bfa'}}>QUICK PROTOCOLS</div>
            <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:6}}>
              {[
                ['BRAIN DUMP', 'brain dump '],
                ['BREAK DOWN', 'break down '],
                ['FOCUS 25M', 'focus on '],
                ['ENERGY CHK', 'energy check'],
                ['LOG WIN', 'log win '],
                ['OVERWHELM', 'overwhelm'],
                ['SYS DIAG', 'System status'],
                ['GOOD MORNING', `Good morning ${userName}`],
              ].map(([label, cmd])=>(
                <button key={label} onClick={()=> cmd.endsWith(' ') ? setInput(cmd) : send(cmd)} style={{background:'rgba(2,2,8,0.8)', border:'1px solid rgba(168,85,247,0.3)', color:'#a78bfa', borderRadius:4, padding:'6px 4px', fontSize:9, letterSpacing:0.5, cursor:'pointer', textAlign:'center'}}>
                  {label}
                </button>
              ))}
            </div>
          </div>

          <div style={{fontSize:9, opacity:0.5, textAlign:'center', lineHeight:1.4, border:'1px solid rgba(34,197,94,0.1)', padding:8, borderRadius:4}}>
            JARVIS v0.1.9 • ADHD Co-Pilot + Iron Man<br/>
            Local-first • FAISS • Voice ready<br/>
            SHILATECH • Malibu Point 10880
          </div>
        </div>

        {/* Center - Main HUD Chat */}
        <div style={{flex:1, display:'flex', flexDirection:'column', background:'rgba(2,2,8,0.6)', backdropFilter:'blur(5px)', position:'relative'}}>
          {/* Holographic top bar */}
          <div style={{padding:'10px 20px', borderBottom:'1px solid rgba(34,197,94,0.2)', display:'flex', justifyContent:'space-between', alignItems:'center', background:'rgba(34,197,94,0.03)'}}>
            <div style={{display:'flex', alignItems:'center', gap:12}}>
              <div style={{fontSize:12, letterSpacing:1}}>MAIN HUD • INTERACTIVE • VOICE: {isListening ? '● LISTENING' : '○ STANDBY'}</div>
              {isListening && <canvas ref={waveformRef} width={120} height={24} style={{width:120, height:24, border:'1px solid rgba(34,197,94,0.3)', borderRadius:4}} />}
            </div>
            <div style={{fontSize:10, opacity:0.6}}>ENCRYPTED CHANNEL • MARK XLII • {userName.toUpperCase()}</div>
          </div>

          {/* Messages - Holographic */}
          <div style={{flex:1, overflowY:'auto', padding:20, display:'flex', flexDirection:'column', gap:16, perspective:'1000px'}}>
            {messages.map((m,i)=>(
              <div key={i} style={{display:'flex', justifyContent: m.role==='user' ? 'flex-end' : 'flex-start', transform: `rotateX(${m.role==='assistant' ? 1 : -1}deg)`}}>
                <div style={{
                  maxWidth:'78%',
                  padding:'14px 18px',
                  borderRadius: m.role==='user' ? '12px 12px 2px 12px' : '12px 12px 12px 2px',
                  background: m.role==='user' ? 'rgba(34,197,94,0.15)' : 'rgba(2,2,8,0.8)',
                  border: `1px solid ${m.role==='user' ? 'rgba(34,197,94,0.5)' : 'rgba(34,211,238,0.3)'}`,
                  color: m.role==='user' ? '#86efac' : '#22d3ee',
                  boxShadow: m.role==='user' ? '0 0 20px rgba(34,197,94,0.2), inset 0 0 20px rgba(34,197,94,0.05)' : '0 0 20px rgba(34,211,238,0.15), inset 0 0 20px rgba(34,211,238,0.05)',
                  whiteSpace:'pre-wrap',
                  fontSize:13,
                  lineHeight:1.6,
                  position:'relative',
                  backdropFilter:'blur(10px)'
                }}>
                  {/* Holographic corner brackets */}
                  <div style={{position:'absolute', top:-1, left:-1, width:12, height:12, borderTop:'2px solid currentColor', borderLeft:'2px solid currentColor', opacity:0.6}} />
                  <div style={{position:'absolute', top:-1, right:-1, width:12, height:12, borderTop:'2px solid currentColor', borderRight:'2px solid currentColor', opacity:0.6}} />
                  <div style={{position:'absolute', bottom:-1, left:-1, width:12, height:12, borderBottom:'2px solid currentColor', borderLeft:'2px solid currentColor', opacity:0.6}} />
                  <div style={{position:'absolute', bottom:-1, right:-1, width:12, height:12, borderBottom:'2px solid currentColor', borderRight:'2px solid currentColor', opacity:0.6}} />
                  
                  <div style={{fontSize:9, opacity:0.5, marginBottom:6, letterSpacing:1}}>{m.role==='user' ? `EUGENE • ${m.time || ''}` : `JARVIS • ${m.time || ''} • ENCRYPTED`}</div>
                  {m.content}
                </div>
              </div>
            ))}
            {loading && (
              <div style={{display:'flex', justifyContent:'flex-start'}}>
                <div style={{padding:'12px 18px', background:'rgba(2,2,8,0.8)', border:'1px solid rgba(34,211,238,0.3)', borderRadius:'12px 12px 12px 2px', color:'#22d3ee', fontSize:12, boxShadow:'0 0 20px rgba(34,211,238,0.15)'}}>
                  <span style={{display:'inline-block', width:8, height:8, background:'#22d3ee', borderRadius:'50%', marginRight:8, animation:'pulse 1s infinite'}} />
                  JARVIS processing, Sir...
                </div>
              </div>
            )}
          </div>

          {/* Input - Holographic */}
          <div style={{padding:16, borderTop:'1px solid rgba(34,197,94,0.3)', background:'rgba(2,2,8,0.9)', display:'flex', gap:12, alignItems:'center'}}>
            <div style={{flex:1, position:'relative'}}>
              <input 
                value={input} 
                onChange={e=>setInput(e.target.value)} 
                onKeyDown={e=> e.key==='Enter' && send()} 
                placeholder={`Ask JARVIS... (Good morning ${userName}, brain dump, break down, focus on...)`}
                style={{
                  width:'100%',
                  background:'rgba(2,2,8,0.8)',
                  border:'1px solid rgba(34,197,94,0.5)',
                  color:'#86efac',
                  borderRadius:8,
                  padding:'14px 18px 14px 40px',
                  fontSize:13,
                  fontFamily:'inherit',
                  outline:'none',
                  boxShadow:'0 0 20px rgba(34,197,94,0.1), inset 0 0 20px rgba(34,197,94,0.05)',
                  letterSpacing:0.5
                }}
              />
              <div style={{position:'absolute', left:12, top:'50%', transform:'translateY(-50%)', color:'#22c55e', fontSize:14}}>▶</div>
              <div style={{position:'absolute', right:12, top:'50%', transform:'translateY(-50%)', fontSize:10, opacity:0.5, letterSpacing:1}}>VOICE READY</div>
            </div>
            <button 
              onClick={()=>send()} 
              disabled={loading}
              style={{
                background:'rgba(34,197,94,0.2)',
                border:'1px solid #22c55e',
                color:'#22c55e',
                borderRadius:8,
                padding:'14px 24px',
                fontWeight:700,
                fontSize:12,
                letterSpacing:1,
                cursor:'pointer',
                boxShadow:'0 0 15px rgba(34,197,94,0.3)',
                transition:'all 0.2s'
              }}
            >
              {loading ? '...' : 'TRANSMIT'}
            </button>
            <button 
              onClick={startVoice}
              style={{
                background: isListening ? 'rgba(239,68,68,0.2)' : 'rgba(2,2,8,0.8)',
                border:`1px solid ${isListening ? '#ef4444' : 'rgba(34,197,94,0.3)'}`,
                color: isListening ? '#fca5a5' : '#22c55e',
                borderRadius:8,
                padding:'14px 16px',
                fontSize:12,
                cursor:'pointer',
                animation: isListening ? 'pulse 1s infinite' : 'none'
              }}
              title="Voice: Click to speak (mic + waveform + TTS)" 
            >
              🎤
            </button>
          </div>
        </div>

        {/* Right Panel - Tasks + Lab */}
        <div style={{width:300, borderLeft:'1px solid rgba(34,197,94,0.2)', background:'rgba(2,2,8,0.8)', backdropFilter:'blur(10px)', padding:16, display:'flex', flexDirection:'column', gap:12, overflowY:'auto'}}>
          <div style={{fontSize:11, letterSpacing:1, opacity:0.7, display:'flex', justifyContent:'space-between'}}>
            <span>TASK MATRIX • TODAY</span>
            <span style={{color:'#22d3ee'}}>{new Date().toLocaleDateString()}</span>
          </div>

          {/* Task List */}
          <div style={{border:'1px solid rgba(34,197,94,0.3)', borderRadius:8, padding:12, background:'rgba(34,197,94,0.03)'}}>
            <div style={{fontSize:10, opacity:0.6, marginBottom:8, letterSpacing:1}}>PRIORITY QUEUE</div>
            {tasksToday.length>0 ? tasksToday.map((task,i)=>(
              <div key={i} style={{display:'flex', gap:8, padding:'6px 0', borderBottom:'1px solid rgba(34,197,94,0.1)', fontSize:11}}>
                <div style={{width:14, height:14, border:'1px solid #22c55e', borderRadius:2, flexShrink:0, display:'flex', alignItems:'center', justifyContent:'center', fontSize:8}}>✓</div>
                <div style={{opacity:0.9}}>{task}</div>
              </div>
            )) : (
              <div style={{fontSize:11, opacity:0.6, lineHeight:1.5}}>
                No tasks loaded. Say "Good morning {userName}" for today's alignment, or "brain dump" to capture.
              </div>
            )}
            <input 
              placeholder="Add task + Enter"
              onKeyDown={e=>{
                if (e.key==='Enter') {
                  const val = (e.target as HTMLInputElement).value.trim()
                  if (val) {
                    const newTasks = [...tasksToday, val]
                    setTasksToday(newTasks)
                    localStorage.setItem('jarvis_today_tasks', JSON.stringify(newTasks))
                    ;(e.target as HTMLInputElement).value = ''
                  }
                }
              }}
              style={{width:'100%', marginTop:8, background:'rgba(2,2,8,0.8)', border:'1px solid rgba(34,197,94,0.2)', color:'#86efac', borderRadius:4, padding:'6px 8px', fontSize:10, fontFamily:'inherit', outline:'none'}}
            />
          </div>

          {/* Weather */}
          <div style={{border:'1px solid rgba(251,191,36,0.3)', borderRadius:8, padding:12, background:'rgba(251,191,36,0.05)'}}>
            <div style={{fontSize:10, opacity:0.6, marginBottom:8, letterSpacing:1, color:'#fbbf24', display:'flex', justifyContent:'space-between'}}>
              <span>WEATHER • NAIROBI</span>
              <span style={{cursor:'pointer'}} onClick={()=>send('weather in Nairobi')}>↻</span>
            </div>
            <div style={{fontSize:11, color:'#fde68a'}}>{weather}</div>
            <div style={{fontSize:9, opacity:0.6, marginTop:6}}>ADHD Tip: Sunny → 5-min walk for dopamine before MIT 1</div>
          </div>

          {/* Calendar */}
          <div style={{border:'1px solid rgba(34,211,238,0.3)', borderRadius:8, padding:12, background:'rgba(34,211,238,0.05)'}}>
            <div style={{fontSize:10, opacity:0.6, marginBottom:8, letterSpacing:1, color:'#22d3ee', display:'flex', justifyContent:'space-between'}}>
              <span>CALENDAR • TODAY</span>
              <span style={{cursor:'pointer'}} onClick={()=>send('calendar today')}>↻</span>
            </div>
            <div style={{fontSize:10, lineHeight:1.6}}>
              {calendarEvents.map((ev,i)=>(
                <div key={i} style={{display:'flex', gap:6, padding:'3px 0', borderBottom:'1px solid rgba(34,211,238,0.1)'}}>
                  <span style={{color:'#22d3ee'}}>•</span><span>{ev}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Email */}
          <div style={{border:'1px solid rgba(239,68,68,0.3)', borderRadius:8, padding:12, background:'rgba(239,68,68,0.05)'}}>
            <div style={{fontSize:10, opacity:0.6, marginBottom:8, letterSpacing:1, color:'#fca5a5', display:'flex', justifyContent:'space-between'}}>
              <span>EMAIL • {emails.filter(e=>e.unread).length} UNREAD</span>
              <span style={{cursor:'pointer'}} onClick={()=>send('email unread')}>↻</span>
            </div>
            <div style={{fontSize:10, lineHeight:1.6}}>
              {emails.slice(0,3).map((email,i)=>(
                <div key={i} style={{display:'flex', gap:6, padding:'3px 0', borderBottom:'1px solid rgba(239,68,68,0.1)'}}>
                  <span style={{color: email.unread ? '#ef4444' : '#52525b'}}>{email.unread ? '●' : '○'}</span>
                  <span style={{opacity: email.unread ? 1 : 0.6}}>{email.from}: {email.subject.slice(0,25)}</span>
                </div>
              ))}
            </div>
            <div style={{fontSize:9, opacity:0.6, marginTop:6}}>2-min rule: if reply &lt;2 min, do now</div>
          </div>

          {/* Lab Systems */}
          <div style={{border:'1px solid rgba(34,211,238,0.3)', borderRadius:8, padding:12, background:'rgba(34,211,238,0.03)'}}>
            <div style={{fontSize:10, opacity:0.6, marginBottom:8, letterSpacing:1, color:'#22d3ee'}}>LAB SYSTEMS</div>
            <div style={{fontSize:10, lineHeight:1.8}}>
              <div style={{display:'flex', justifyContent:'space-between'}}><span>💡 LAB LIGHTS</span><span style={{color:'#22c55e'}}>ON • 80% • BLUE</span></div>
              <div style={{display:'flex', justifyContent:'space-between'}}><span>🎵 AUDIO</span><span style={{color:'#22c55e'}}>PLAYING • LO-FI</span></div>
              <div style={{display:'flex', justifyContent:'space-between'}}><span>🔋 ARC</span><span style={{color:'#22c55e'}}>{arcPower.toFixed(1)}% • STABLE</span></div>
              <div style={{display:'flex', justifyContent:'space-between'}}><span>🛡️ SECURITY</span><span style={{color:'#22c55e'}}>PERIMETER SECURE</span></div>
              <div style={{display:'flex', justifyContent:'space-between'}}><span>💾 MEMORY</span><span style={{color:'#a78bfa'}}>FAISS • 342 VECS</span></div>
              <div style={{display:'flex', justifyContent:'space-between'}}><span>🧠 FOCUS</span><span style={{color:'#22c55e'}}>READY • BODY DOUBLE</span></div>
              <div style={{display:'flex', justifyContent:'space-between'}}><span>⚡ ENERGY</span><span style={{color:'#fbbf24', fontSize:9}}>{energyPattern.slice(0,20)}</span></div>
            </div>
          </div>

          {/* ADHD Quick Stats */}
          <div style={{border:'1px solid rgba(168,85,247,0.3)', borderRadius:8, padding:12, background:'rgba(168,85,247,0.05)'}}>
            <div style={{fontSize:10, opacity:0.6, marginBottom:8, letterSpacing:1, color:'#a78bfa'}}>ADHD CO-PILOT • TODAY</div>
            <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:8, fontSize:10}}>
              <div style={{background:'rgba(2,2,8,0.8)', border:'1px solid rgba(168,85,247,0.2)', borderRadius:4, padding:8, textAlign:'center'}}>
                <div style={{fontSize:18, fontWeight:800, color:'#a78bfa'}}>{tasksToday.length || mits.length}</div>
                <div style={{opacity:0.6, fontSize:9}}>TASKS</div>
              </div>
              <div style={{background:'rgba(2,2,8,0.8)', border:'1px solid rgba(168,85,247,0.2)', borderRadius:4, padding:8, textAlign:'center'}}>
                <div style={{fontSize:18, fontWeight:800, color:'#22c55e'}}>3</div>
                <div style={{opacity:0.6, fontSize:9}}>MITS MAX</div>
              </div>
              <div style={{background:'rgba(2,2,8,0.8)', border:'1px solid rgba(168,85,247,0.2)', borderRadius:4, padding:8, textAlign:'center'}}>
                <div style={{fontSize:18, fontWeight:800, color:'#22d3ee'}}>25M</div>
                <div style={{opacity:0.6, fontSize:9}}>FOCUS</div>
              </div>
              <div style={{background:'rgba(2,2,8,0.8)', border:'1px solid rgba(168,85,247,0.2)', borderRadius:4, padding:8, textAlign:'center'}}>
                <div style={{fontSize:18, fontWeight:800, color:'#fbbf24'}}>∞</div>
                <div style={{opacity:0.6, fontSize:9}}>WINS</div>
              </div>
            </div>
            <button onClick={()=>send('task learning')} style={{width:'100%', marginTop:8, background:'rgba(168,85,247,0.2)', border:'1px solid #a78bfa', color:'#a78bfa', borderRadius:4, padding:'5px', fontSize:9, letterSpacing:1, cursor:'pointer'}}>LEARN MY PATTERNS</button>
          </div>

          {/* How to get real */}
          <div style={{border:'1px solid rgba(34,197,94,0.1)', borderRadius:8, padding:10, background:'rgba(2,2,8,0.5)'}}>
            <div style={{fontSize:9, opacity:0.5, letterSpacing:1, marginBottom:6}}>REAL WORLD INTEGRATION</div>
            <div style={{fontSize:9, opacity:0.6, lineHeight:1.5}}>
              <div>🏠 Hue: pip install phue + HUE_BRIDGE_IP</div>
              <div>🏠 HA: HASS_URL + HASS_TOKEN</div>
              <div>👁️ Vision: ollama pull llava</div>
              <div>🎤 Voice: faster-whisper + kokoro</div>
              <div>🔊 Wake: openwakeword</div>
              <div style={{marginTop:6, color:'#22c55e'}}>Autostart: Settings → Startup → Enable JARVIS</div>
            </div>
          </div>

          {/* User customization */}
          <div style={{border:'1px solid rgba(34,197,94,0.2)', borderRadius:8, padding:10, background:'rgba(34,197,94,0.03)'}}>
            <div style={{fontSize:9, opacity:0.6, letterSpacing:1, marginBottom:6}}>PERSONALIZATION</div>
            <input 
              value={userName}
              onChange={e=>{
                setUserName(e.target.value)
                localStorage.setItem('jarvis_user_name', e.target.value)
              }}
              placeholder="Your name"
              style={{width:'100%', background:'rgba(2,2,8,0.8)', border:'1px solid rgba(34,197,94,0.2)', color:'#86efac', borderRadius:4, padding:'6px 8px', fontSize:11, fontFamily:'inherit', outline:'none', marginBottom:6}}
            />
            <div style={{fontSize:9, opacity:0.5}}>Name used in greetings: Good morning {userName}</div>
          </div>
        </div>
      </div>

      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Share+Tech+Mono&display=swap');
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: rgba(2,2,8,0.5); }
        ::-webkit-scrollbar-thumb { background: rgba(34,197,94,0.3); border-radius: 3px; }
        ::-webkit-scrollbar-thumb:hover { background: rgba(34,197,94,0.5); }
      `}</style>
    </div>
  )
}
