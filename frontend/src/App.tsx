import React, { useState, useEffect, useRef, useMemo } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { MathUtils, Color, Vector3 } from 'three';
import { motion, AnimatePresence } from 'framer-motion';
import { Mic, Activity, Cpu, Home, MessageSquare, Info, Shield, Clock, Terminal } from 'lucide-react';

// ─── GLOBAL AUDIO ANALYZER ────────────────────────────────────────────────────
let audioCtx: AudioContext | null = null;
let analyser: AnalyserNode | null = null;
let dataArray: Uint8Array | null = null;

// ─── 1. GLSL SHADERS ─────────────────────────────────────────────────────────
const vertexShader = `
  varying vec2 vUv;
  varying vec3 vNormal;
  varying vec3 vPosition;
  uniform float uTime;
  uniform float uAmplitude;
  uniform float uSpeed;
  vec4 mod289(vec4 x){return x - floor(x * (1.0 / 289.0)) * 289.0;}
  vec4 perm(vec4 x){return mod289(((x * 34.0) + 1.0) * x);}
  float noise(vec3 p){
      vec3 a = floor(p); vec3 d = p - a; d = d * d * (3.0 - 2.0 * d);
      vec4 b = a.xxyy + vec4(0.0, 1.0, 0.0, 1.0);
      vec4 k1 = perm(b.xyxy); vec4 k2 = perm(k1.xyxy + b.zzww);
      vec4 c = k2 + a.zzzz; vec4 k3 = perm(c); vec4 k4 = perm(c + 1.0);
      vec4 o1 = fract(k3 * (1.0 / 41.0)); vec4 o2 = fract(k4 * (1.0 / 41.0));
      vec4 o3 = o2 * d.z + o1 * (1.0 - d.z); vec2 o4 = o3.yw * d.x + o3.xz * (1.0 - d.x);
      return o4.y * d.y + o4.x * (1.0 - d.y);
  }
  void main() {
    vUv = uv; vNormal = normal; vPosition = position;
    float n = noise(position * 1.5 + uTime * uSpeed);
    float n2 = noise(position * 3.0 - uTime * (uSpeed * 0.5));
    float displacement = (n + n2 * 0.5) * uAmplitude;
    vec3 newPosition = position + normal * displacement;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(newPosition, 1.0);
  }
`;

const fragmentShader = `
  varying vec2 vUv;
  varying vec3 vNormal;
  uniform float uTime;
  uniform vec3 uColorCyan;
  uniform vec3 uColorViolet;
  uniform float uIntensity;
  void main() {
    float intensity = pow(0.65 - dot(vNormal, vec3(0, 0, 1.0)), 2.0);
    float mixValue = (sin(vUv.x * 10.0 + uTime) + cos(vUv.y * 10.0 + uTime)) * 0.5 + 0.5;
    vec3 finalColor = mix(uColorCyan, uColorViolet, mixValue);
    vec3 glow = finalColor * intensity * uIntensity;
    gl_FragColor = vec4(glow, 1.0);
  }
`;

// ─── 2. THE AI CORE COMPONENT ────────────────────────────────────────────────
const AICore = ({ state, currentView }: { state: string, currentView: string }) => {
  const meshRef = useRef<any>(null);
  const materialRef = useRef<any>(null);
  const uniforms = useMemo(() => ({
    uTime: { value: 0 }, uAmplitude: { value: 0.1 }, uSpeed: { value: 0.5 },
    uColorCyan: { value: new Color('#47D8FF') }, uColorViolet: { value: new Color('#8A6DFF') },
    uIntensity: { value: 1.5 },
  }), []);

  useFrame((stateData) => {
    const time = stateData.clock.getElapsedTime();
    if (meshRef.current) {
      const targetScale = currentView === 'home' ? 1.0 : 0.35;
      const targetPosX = currentView === 'home' ? 0 : 2.8;
      const targetPosY = currentView === 'home' ? 0 : -1.6;
      meshRef.current.scale.lerp(new Vector3(targetScale, targetScale, targetScale), 0.04);
      meshRef.current.position.lerp(new Vector3(targetPosX, targetPosY, 0), 0.04);
      meshRef.current.rotation.y -= 0.005;
      meshRef.current.rotation.x -= 0.002;
    }

    if (materialRef.current) {
      materialRef.current.uniforms.uTime.value = time;
      let targetAmplitude = 0.05, targetSpeed = 0.2, targetIntensity = 1.2, lerpSpeed = 0.05;

      if (state === 'listening') {
        targetAmplitude = 0.3 + Math.sin(time * 5) * 0.1; targetSpeed = 1.5; targetIntensity = 2.5;
      } else if (state === 'processing') {
        targetAmplitude = 0.15; targetSpeed = 0.8; targetIntensity = 3.0;
        materialRef.current.uniforms.uColorCyan.value.lerp(new Color('#8A6DFF'), 0.05);
      } else if (state === 'speaking') {
        targetSpeed = 2.0; targetIntensity = 2.8;
        materialRef.current.uniforms.uColorCyan.value.lerp(new Color('#47D8FF'), 0.1);
        if (analyser && dataArray) {
          analyser.getByteFrequencyData(dataArray);
          let sum = 0; for (let i = 0; i < dataArray.length; i++) sum += dataArray[i];
          const average = sum / dataArray.length;
          targetAmplitude = 0.10 + (average / 255.0) * 0.8; lerpSpeed = 0.25;
        }
      } else {
        materialRef.current.uniforms.uColorCyan.value.lerp(new Color('#47D8FF'), 0.05);
      }

      materialRef.current.uniforms.uAmplitude.value = MathUtils.lerp(materialRef.current.uniforms.uAmplitude.value, targetAmplitude, lerpSpeed);
      materialRef.current.uniforms.uSpeed.value = MathUtils.lerp(materialRef.current.uniforms.uSpeed.value, targetSpeed, 0.05);
      materialRef.current.uniforms.uIntensity.value = MathUtils.lerp(materialRef.current.uniforms.uIntensity.value, targetIntensity, 0.05);
    }
  });

  return (
    <mesh ref={meshRef}>
      <icosahedronGeometry args={[2, 64]} />
      <shaderMaterial ref={materialRef} vertexShader={vertexShader} fragmentShader={fragmentShader} uniforms={uniforms} transparent />
    </mesh>
  );
};

// ─── 3. MAIN APPLICATION UI ───────────────────────────────────────────────────
export default function App() {
  const [mayaState, setMayaState] = useState<string>('standby');
  const [currentView, setCurrentView] = useState<'home' | 'live' | 'history' | 'about'>('home');
  const [messages, setMessages] = useState<{ sender: string, content: string }[]>([]);

  // ChatGPT-Style History States
  const [sessionsList, setSessionsList] = useState<any[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<number | null>(null);
  const [activeSessionData, setActiveSessionData] = useState<any | null>(null);

  const ws = useRef<WebSocket | null>(null);
  const liveChatEndRef = useRef<HTMLDivElement | null>(null);
  const historyChatEndRef = useRef<HTMLDivElement | null>(null);

  // Auto-scroll Live Chat
  useEffect(() => { liveChatEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  // Auto-scroll History Chat
  useEffect(() => { historyChatEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [activeSessionData]);

  // Fetch History Sidebar List
  useEffect(() => {
    if (currentView === 'history') {
      fetch('http://localhost:8000/history')
        .then(res => res.json())
        .then(data => {
          setSessionsList(data);
          if (data.length > 0 && !activeSessionId) {
            setActiveSessionId(data[0].id);
          }
        })
        .catch(err => console.error(err));
    }
  }, [currentView]);

  // Fetch Specific History Session Data
  useEffect(() => {
    if (activeSessionId !== null) {
      fetch(`http://localhost:8000/history/${activeSessionId}`)
        .then(res => res.json())
        .then(data => setActiveSessionData(data))
        .catch(err => console.error(err));
    }
  }, [activeSessionId]);

  // WebSockets Connection
  useEffect(() => {
    ws.current = new WebSocket('ws://localhost:8000/ws/audio');

    ws.current.onmessage = async (event) => {
      if (event.data instanceof Blob) {
        if (!audioCtx) {
          audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)();
          analyser = audioCtx.createAnalyser();
          analyser.fftSize = 64; dataArray = new Uint8Array(analyser.frequencyBinCount);
        }
        const audioUrl = URL.createObjectURL(event.data);
        const audio = new Audio(audioUrl);
        const source = audioCtx.createMediaElementSource(audio);
        source.connect(analyser); analyser.connect(audioCtx.destination);
        setMayaState('speaking');
        audio.onended = () => {
          setMayaState('standby'); source.disconnect(); URL.revokeObjectURL(audioUrl);
        };
        try { await audioCtx.resume(); await audio.play(); } catch (err) { }
        return;
      }
      try {
        const payload = JSON.parse(event.data);
        if (payload.type === 'state') setMayaState(payload.status);
        if (payload.type === 'text') setMessages(prev => [...prev, { sender: payload.sender, content: payload.content }]);
        if (payload.type === 'command' && payload.action === 'close') window.close();
      } catch (err) { }
    };
    return () => ws.current?.close();
  }, []);

  return (
    <div className="h-screen w-screen bg-[#0B0F14] overflow-hidden relative font-sans text-slate-100">

      <div className="absolute inset-0 z-0 flex items-center justify-center pointer-events-none">
        <div className="w-[800px] h-[800px] bg-[#47D8FF]/5 rounded-full blur-[120px]" />
      </div>

      <div className="absolute inset-0 z-10 cursor-crosshair" onClick={() => audioCtx?.resume()}>
        <Canvas camera={{ position: [0, 0, 6], fov: 45 }}>
          <ambientLight intensity={0.5} />
          <AICore state={mayaState} currentView={currentView} />
        </Canvas>
      </div>

      {/* ── 4-BUTTON NAVIGATION DOCK ── */}
      <div className="absolute left-6 top-1/2 -translate-y-1/2 z-50 flex flex-col gap-6 bg-[#101826]/80 backdrop-blur-md p-3 rounded-full border border-white/10 shadow-2xl">
        {/* 1. Home */}
        <button onClick={() => setCurrentView('home')} className={`p-3 rounded-full transition-all duration-300 ${currentView === 'home' ? 'bg-[#47D8FF]/20 text-[#47D8FF] shadow-[0_0_15px_rgba(71,216,255,0.3)]' : 'text-slate-500 hover:text-slate-300 hover:bg-white/5'}`} title="Home HUD">
          <Home className="w-5 h-5" />
        </button>
        {/* 2. Live Active Chat */}
        <button onClick={() => setCurrentView('live')} className={`p-3 rounded-full transition-all duration-300 ${currentView === 'live' ? 'bg-[#47D8FF]/20 text-[#47D8FF] shadow-[0_0_15px_rgba(71,216,255,0.3)]' : 'text-slate-500 hover:text-slate-300 hover:bg-white/5'}`} title="Active Session">
          <Terminal className="w-5 h-5" />
        </button>
        {/* 3. History / Archive */}
        <button onClick={() => setCurrentView('history')} className={`p-3 rounded-full transition-all duration-300 ${currentView === 'history' ? 'bg-[#8A6DFF]/20 text-[#8A6DFF] shadow-[0_0_15px_rgba(138,109,255,0.3)]' : 'text-slate-500 hover:text-slate-300 hover:bg-white/5'}`} title="Chat History">
          <Clock className="w-5 h-5" />
        </button>
        {/* 4. About */}
        <button onClick={() => setCurrentView('about')} className={`p-3 rounded-full transition-all duration-300 ${currentView === 'about' ? 'bg-[#8A6DFF]/20 text-[#8A6DFF] shadow-[0_0_15px_rgba(138,109,255,0.3)]' : 'text-slate-500 hover:text-slate-300 hover:bg-white/5'}`} title="System Info">
          <Info className="w-5 h-5" />
        </button>
      </div>

      {/* ── 1. HOME VIEW (Minimal HUD) ── */}
      <AnimatePresence>
        {currentView === 'home' && (
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 20 }} className="absolute bottom-12 left-0 w-full flex flex-col items-center justify-center z-20 pointer-events-none">
            <div className="flex items-center gap-3">
              {mayaState === 'listening' && <Mic className="w-5 h-5 text-[#47D8FF] animate-pulse" />}
              {mayaState === 'processing' && <Activity className="w-5 h-5 text-[#8A6DFF] animate-pulse" />}
              <span className="uppercase tracking-[0.2em] text-xs font-semibold text-slate-300 drop-shadow-[0_0_8px_rgba(71,216,255,0.5)]">
                {mayaState === 'standby' ? 'Standby' : mayaState + '...'}
              </span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── 2. LIVE CHAT VIEW (Current Session in RAM) ── */}
      <AnimatePresence>
        {currentView === 'live' && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95, filter: "blur(10px)" }} animate={{ opacity: 1, scale: 1, filter: "blur(0px)" }} exit={{ opacity: 0, scale: 0.95, filter: "blur(10px)" }} transition={{ duration: 0.4 }}
            className="absolute inset-0 z-20 flex items-center justify-center pl-16 py-12 pointer-events-none"
          >
            <div className="w-full max-w-4xl h-full bg-[#101826]/70 backdrop-blur-3xl border border-white/5 rounded-3xl p-8 flex flex-col shadow-2xl pointer-events-auto">
              <div className="flex items-center gap-3 mb-8 border-b border-white/10 pb-4">
                <Terminal className="w-5 h-5 text-[#47D8FF]" />
                <h2 className="text-sm uppercase tracking-widest text-slate-300 font-semibold">Active Session Log (Live)</h2>
              </div>
              <div className="flex-1 overflow-y-auto scrollbar-thin space-y-6 pr-4">
                {messages.length === 0 ? (
                  <div className="h-full flex items-center justify-center">
                    <p className="text-sm text-slate-500 font-mono tracking-widest uppercase">No voice data recorded in current session</p>
                  </div>
                ) : (
                  messages.map((msg, i) => (
                    <div key={i} className={`flex flex-col ${msg.sender === 'user' ? 'items-end' : 'items-start'}`}>
                      <span className="text-[10px] text-slate-500 font-mono mb-2 tracking-wider uppercase">
                        {msg.sender === 'user' ? 'Operator' : 'Maya'}
                      </span>
                      <div className={`text-sm leading-relaxed px-5 py-3 rounded-2xl max-w-[80%] ${msg.sender === 'user'
                          ? 'bg-[#47D8FF]/10 text-slate-200 border border-[#47D8FF]/20 rounded-tr-sm'
                          : 'bg-white/5 text-slate-300 border border-white/5 rounded-tl-sm'
                        }`}>
                        {msg.content}
                      </div>
                    </div>
                  ))
                )}
                <div ref={liveChatEndRef} />
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── 3. HISTORY VIEW (ChatGPT Style Interface) ── */}
      <AnimatePresence>
        {currentView === 'history' && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95, filter: "blur(10px)" }} animate={{ opacity: 1, scale: 1, filter: "blur(0px)" }} exit={{ opacity: 0, scale: 0.95, filter: "blur(10px)" }} transition={{ duration: 0.4 }}
            className="absolute inset-0 z-20 flex items-center justify-center pl-24 pr-12 py-12 pointer-events-none"
          >
            <div className="w-full max-w-6xl h-full flex gap-6 pointer-events-auto">

              {/* Left Panel: Sessions Sidebar */}
              <div className="w-1/3 bg-[#101826]/70 backdrop-blur-3xl border border-white/5 rounded-3xl p-6 flex flex-col shadow-2xl">
                <div className="flex items-center gap-3 mb-6 border-b border-white/10 pb-4">
                  <Clock className="w-5 h-5 text-[#8A6DFF]" />
                  <h2 className="text-sm uppercase tracking-widest text-slate-300 font-semibold">Memory Banks</h2>
                </div>
                <div className="flex-1 overflow-y-auto scrollbar-thin space-y-3 pr-2">
                  {sessionsList.length === 0 ? (
                    <p className="text-xs text-slate-500 font-mono text-center mt-10">No sessions recorded.</p>
                  ) : (
                    sessionsList.map((session) => (
                      <button
                        key={session.id}
                        onClick={() => setActiveSessionId(session.id)}
                        className={`w-full text-left p-4 rounded-2xl transition-all duration-200 border ${activeSessionId === session.id
                            ? 'bg-[#8A6DFF]/10 border-[#8A6DFF]/30 shadow-lg'
                            : 'bg-white/5 border-transparent hover:bg-white/10'
                          }`}
                      >
                        <p className="text-sm font-medium text-slate-200 mb-1">Session #{session.id}</p>
                        <p className="text-[10px] font-mono text-slate-500 uppercase tracking-wider">
                          {new Date(session.started_at).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })}
                        </p>
                      </button>
                    ))
                  )}
                </div>
              </div>

              {/* Right Panel: Active Session Chat Log */}
              <div className="w-2/3 bg-[#101826]/70 backdrop-blur-3xl border border-white/5 rounded-3xl p-8 flex flex-col shadow-2xl">
                <div className="flex items-center justify-between mb-8 border-b border-white/10 pb-4">
                  <h2 className="text-sm uppercase tracking-widest text-slate-300 font-semibold">
                    {activeSessionData ? `Transcript: Session #${activeSessionData.id}` : 'Select a Session'}
                  </h2>
                </div>

                <div className="flex-1 overflow-y-auto scrollbar-thin space-y-6 pr-4">
                  {!activeSessionData ? (
                    <div className="h-full flex items-center justify-center">
                      <MessageSquare className="w-12 h-12 text-white/5" />
                    </div>
                  ) : (
                    (activeSessionData.messages || []).map((msg: any, i: number) => (
                      <div key={i} className={`flex flex-col ${msg.sender === 'user' ? 'items-end' : 'items-start'}`}>
                        <div className="flex items-center gap-2 mb-2">
                          <span className="text-[10px] text-slate-400 font-mono tracking-wider uppercase">
                            {msg.sender === 'user' ? 'Operator' : 'Maya'}
                          </span>
                        </div>
                        <div className={`text-sm leading-relaxed px-5 py-3 rounded-2xl max-w-[80%] ${msg.sender === 'user'
                            ? 'bg-[#47D8FF]/10 text-slate-200 border border-[#47D8FF]/20 rounded-tr-sm'
                            : 'bg-white/5 text-slate-300 border border-white/5 rounded-tl-sm'
                          }`}>
                          {msg.content}
                        </div>
                      </div>
                    ))
                  )}
                  <div ref={historyChatEndRef} />
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── 4. ABOUT MAYA VIEW ── */}
      <AnimatePresence>
        {currentView === 'about' && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95, filter: "blur(10px)" }} animate={{ opacity: 1, scale: 1, filter: "blur(0px)" }} exit={{ opacity: 0, scale: 0.95, filter: "blur(10px)" }} transition={{ duration: 0.4 }}
            className="absolute inset-0 z-20 flex items-center justify-center pl-16 py-12 pointer-events-none"
          >
            <div className="w-full max-w-4xl h-full bg-[#101826]/70 backdrop-blur-3xl border border-white/5 rounded-3xl p-10 flex flex-col shadow-2xl pointer-events-auto relative overflow-hidden">
              <div className="absolute -top-32 -right-32 w-96 h-96 bg-[#8A6DFF]/10 rounded-full blur-[100px] pointer-events-none" />
              <div className="flex flex-col items-center justify-center h-full z-10">
                <div className="text-center mb-12">
                  <h1 className="text-6xl font-black tracking-[0.4em] text-transparent bg-clip-text bg-gradient-to-br from-[#47D8FF] via-white to-[#8A6DFF] drop-shadow-2xl mb-4">
                    MAYA
                  </h1>
                  <p className="text-slate-400 font-mono tracking-[0.2em] uppercase text-xs border border-white/10 px-4 py-1.5 rounded-full inline-block bg-white/5">
                    Offline AI Desktop Companion v1.0
                  </p>
                </div>
                <div className="grid grid-cols-3 gap-6 w-full max-w-3xl mb-12">
                  <div className="bg-white/5 border border-white/10 p-6 rounded-2xl text-center">
                    <Cpu className="w-6 h-6 text-[#47D8FF] mx-auto mb-4" />
                    <h3 className="text-xs font-mono uppercase tracking-wider text-slate-300 mb-1">Neural Engine</h3>
                    <p className="text-sm text-slate-500">Ollama • Gemma 3:270M</p>
                  </div>
                  <div className="bg-white/5 border border-white/10 p-6 rounded-2xl text-center">
                    <Mic className="w-6 h-6 text-[#8A6DFF] mx-auto mb-4" />
                    <h3 className="text-xs font-mono uppercase tracking-wider text-slate-300 mb-1">Speech Pipeline</h3>
                    <p className="text-sm text-slate-500">Faster-Whisper • Piper TTS</p>
                  </div>
                  <div className="bg-white/5 border border-white/10 p-6 rounded-2xl text-center">
                    <Activity className="w-6 h-6 text-pink-400 mx-auto mb-4" />
                    <h3 className="text-xs font-mono uppercase tracking-wider text-slate-300 mb-1">Visual Core</h3>
                    <p className="text-sm text-slate-500">WebGL • React Three Fiber</p>
                  </div>
                </div>
                <div className="flex items-center gap-2 text-xs text-slate-500 font-mono uppercase tracking-widest bg-black/40 px-6 py-3 rounded-full border border-white/5">
                  <Shield className="w-4 h-4 text-emerald-400" />
                  System operates 100% locally. Zero external telemetry.
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

    </div>
  );
}