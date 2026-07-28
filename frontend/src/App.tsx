import React, { useState, useEffect, useRef } from 'react';
import {
  Mic, Loader2, Cpu, HardDrive, Activity,
  Sparkles, Terminal
} from 'lucide-react';

interface Message {
  sender: string;
  text: string;
}

interface SysStatus {
  cpu: number;
  ram: number;
}

export default function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [mayaState, setMayaState] = useState<string>('standby'); // standby | listening | processing
  const [sysStatus, setSysStatus] = useState<SysStatus>({ cpu: 0, ram: 0 });
  const [hasInteracted, setHasInteracted] = useState<boolean>(false);
  const [wsConnected, setWsConnected] = useState<boolean>(false);

  const ws = useRef<WebSocket | null>(null);
  const chatEndRef = useRef<HTMLDivElement | null>(null);

  // Auto-scroll chat stream
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, mayaState]);

  // System status polling (Backend Telemetry)
  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const res = await fetch('http://localhost:8000/status');
        const data = await res.json();
        setSysStatus({
          cpu: Math.round(data.cpu_percent || 0),
          ram: Math.round(data.ram_percent || 0)
        });
      } catch (err) {
        console.error("Telemetry fetch error:", err);
      }
    };

    fetchStatus();
    const interval = setInterval(fetchStatus, 3000);
    return () => clearInterval(interval);
  }, []);

  // WebSocket lifecycle (Memory Safe & Strict-Mode Proof)
  useEffect(() => {
    let isMounted = true;
    let reconnectTimeout: ReturnType<typeof setTimeout>;

    const connectWS = () => {
      if (!isMounted) return; // Stop if React unmounted the component

      ws.current = new WebSocket('ws://localhost:8000/ws/audio');

      ws.current.onopen = () => {
        console.log('Connected to Maya Core Engine');
        if (isMounted) setWsConnected(true);
      };

      ws.current.onmessage = async (event) => {
        // Binary WAV stream from Piper TTS
        if (event.data instanceof Blob) {
          const audioUrl = URL.createObjectURL(event.data);
          const audio = new Audio(audioUrl);

          audio.onended = () => {
            URL.revokeObjectURL(audioUrl);
            setMayaState('standby');
          };

          try {
            await audio.play();
          } catch (err) {
            console.warn("Audio blocked. User gesture required.", err);
          }
          return;
        }

        // JSON Control payloads & text streams
        if (typeof event.data === 'string') {
          try {
            const payload = JSON.parse(event.data);
            if (payload.type === 'state') {
              setMayaState(payload.status);
            } else if (payload.type === 'text') {
              setMessages((prev) => [...prev, { sender: payload.sender, text: payload.content }]);
            }
          } catch (err) {
            console.error("Payload parse error:", err);
          }
        }
      };

      ws.current.onclose = () => {
        if (isMounted) {
          setWsConnected(false);
          // Only attempt reconnect if the component is still alive
          reconnectTimeout = setTimeout(connectWS, 2000);
        }
      };
    };

    connectWS();

    // Cleanup function: runs when React unmounts the component
    return () => {
      isMounted = false;
      clearTimeout(reconnectTimeout); // Kill any pending reconnects
      if (ws.current) {
        ws.current.onclose = null; // Remove the listener so it doesn't fire
        ws.current.close();
      }
    };
  }, []);

  const handleUserInteraction = () => {
    if (!hasInteracted) setHasInteracted(true);
  };

  return (
    <div
      className="h-screen w-screen bg-slate-950 text-slate-100 flex flex-col font-sans select-none overflow-hidden"
      onClick={handleUserInteraction}
    >
      {/* ── Header / Status Bar ────────────────────────────────────────────── */}
      <header className="h-16 bg-slate-900/60 backdrop-blur-md border-b border-slate-800/80 px-6 flex items-center justify-between z-20">
        <div className="flex items-center gap-3">
          <div className="relative flex items-center justify-center">
            <Sparkles className="w-5 h-5 text-cyan-400 animate-pulse" />
            <div className="absolute inset-0 bg-cyan-500/20 blur-md rounded-full" />
          </div>
          <div>
            <h1 className="text-base font-bold tracking-wider text-slate-100 uppercase">Maya Core</h1>
            <p className="text-[10px] tracking-widest text-slate-400 font-mono uppercase">v2.0 • Local Engine</p>
          </div>
        </div>

        {/* System Telemetry & Connection Status */}
        <div className="flex items-center gap-6 text-xs font-mono">
          <div className="flex items-center gap-2 bg-slate-800/50 px-3 py-1.5 rounded-md border border-slate-700/50">
            <Cpu className="w-3.5 h-3.5 text-cyan-400" />
            <span className="text-slate-400">CPU:</span>
            <span className="text-slate-200 font-semibold">{sysStatus.cpu}%</span>
          </div>

          <div className="flex items-center gap-2 bg-slate-800/50 px-3 py-1.5 rounded-md border border-slate-700/50">
            <HardDrive className="w-3.5 h-3.5 text-indigo-400" />
            <span className="text-slate-400">RAM:</span>
            <span className="text-slate-200 font-semibold">{sysStatus.ram}%</span>
          </div>

          <div className="flex items-center gap-2">
            <span className={`h-2 w-2 rounded-full ${wsConnected ? 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8)]' : 'bg-rose-500'}`} />
            <span className="text-slate-400 uppercase text-[11px]">{wsConnected ? 'Connected' : 'Offline'}</span>
          </div>
        </div>
      </header>

      {/* ── Main Chat & Visualizer View ──────────────────────────────────── */}
      <main className="flex-1 overflow-y-auto p-6 space-y-4 scrollbar-thin scrollbar-thumb-slate-800">
        {!hasInteracted && (
          <div className="bg-cyan-500/10 border border-cyan-500/30 text-cyan-200 text-xs py-2 px-4 rounded-lg text-center max-w-md mx-auto backdrop-blur-md">
            Click anywhere to activate audio context
          </div>
        )}

        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-slate-600 space-y-3">
            <Terminal className="w-10 h-10 stroke-[1.5] opacity-40" />
            <p className="text-xs font-mono tracking-widest uppercase">System ready. Listening for wake word...</p>
          </div>
        ) : (
          messages.map((msg, i) => (
            <div
              key={i}
              className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'} animate-in fade-in duration-300`}
            >
              <div
                className={`max-w-[70%] px-4 py-3 rounded-2xl text-sm leading-relaxed shadow-lg ${msg.sender === 'user'
                    ? 'bg-gradient-to-r from-cyan-600 to-cyan-500 text-white rounded-br-none border border-cyan-400/20'
                    : 'bg-slate-900/80 backdrop-blur-md border border-slate-800 text-slate-200 rounded-bl-none font-sans'
                  }`}
              >
                {msg.text}
              </div>
            </div>
          ))
        )}
        <div ref={chatEndRef} />
      </main>

      {/* ── Footer / Voice Orb Visualizer ────────────────────────────────── */}
      <footer className="h-44 bg-slate-900/40 backdrop-blur-lg border-t border-slate-800/80 flex flex-col items-center justify-center relative">
        {/* Glow Effects */}
        <div className="relative flex items-center justify-center">
          {mayaState === 'listening' && (
            <>
              <div className="absolute w-28 h-28 bg-cyan-500/20 rounded-full animate-ping" />
              <div className="absolute w-36 h-36 bg-cyan-500/10 rounded-full blur-xl animate-pulse" />
              <div className="relative bg-gradient-to-tr from-cyan-500 to-emerald-400 p-5 rounded-full shadow-[0_0_40px_rgba(6,182,212,0.6)] transition-all duration-300">
                <Mic className="w-7 h-7 text-slate-950 stroke-[2.5]" />
              </div>
            </>
          )}

          {mayaState === 'processing' && (
            <>
              <div className="absolute w-32 h-32 bg-amber-500/10 rounded-full blur-lg animate-pulse" />
              <div className="relative bg-gradient-to-tr from-amber-500 to-orange-400 p-5 rounded-full shadow-[0_0_40px_rgba(245,158,11,0.5)]">
                <Loader2 className="w-7 h-7 text-slate-950 animate-spin stroke-[2.5]" />
              </div>
            </>
          )}

          {mayaState === 'standby' && (
            <div className="relative bg-slate-800/80 border border-slate-700/80 p-5 rounded-full shadow-inner group hover:border-slate-600 transition-all duration-300">
              <Activity className="w-7 h-7 text-slate-400 group-hover:text-slate-300" />
            </div>
          )}
        </div>

        {/* State Label */}
        <div className="mt-4 flex items-center gap-2">
          <span className="text-[11px] font-mono tracking-widest text-slate-400 uppercase">
            {mayaState === 'listening' ? 'Listening...' : mayaState === 'processing' ? 'Processing Intent...' : 'Standby'}
          </span>
        </div>
      </footer>
    </div>
  );
}