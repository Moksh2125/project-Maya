import React, { useEffect } from 'react';
import { motion } from 'framer-motion';
import { Mic, Activity, Cpu } from 'lucide-react';
import { useStore } from './store/useStore';
import { useMayaAudio } from './hooks/useMayaAudio';

export default function App() {
  const { isListening, isProcessing, messages, systemStatus, updateStatus } = useStore();
  const { toggleRecording } = useMayaAudio();

  // Mock status polling
  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const res = await fetch('http://localhost:8000/status');
        const data = await res.json();
        updateStatus({ cpu: data.cpu_percent, ram: data.ram_percent, online: true });
      } catch (e) {
        updateStatus({ cpu: 0, ram: 0, online: false });
      }
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="h-screen w-screen bg-gray-950 text-gray-100 flex flex-col font-sans overflow-hidden selection:bg-cyan-500/30">
      {/* Top Bar - Glassmorphism */}
      <header className="h-14 bg-gray-900/40 backdrop-blur-md border-b border-white/10 flex items-center justify-between px-6 z-10 drag-region">
        <div className="flex items-center gap-3">
          <div className={`h-2 w-2 rounded-full ${systemStatus.online ? 'bg-cyan-400 shadow-[0_0_10px_#22d3ee]' : 'bg-red-500'}`} />
          <span className="font-semibold tracking-wider text-sm text-gray-300">MAYA OS</span>
        </div>
        <div className="flex gap-4 text-xs text-gray-400">
          <span className="flex items-center gap-1"><Cpu size={14} /> CPU: {systemStatus.cpu}%</span>
          <span className="flex items-center gap-1"><Activity size={14} /> RAM: {systemStatus.ram}%</span>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 flex p-6 gap-6 relative">

        {/* Left: Chat/History Panel */}
        <div className="flex-1 bg-gray-900/30 backdrop-blur-lg border border-white/5 rounded-2xl p-4 flex flex-col">
          <div className="flex-1 overflow-y-auto space-y-4">
            {messages.length === 0 ? (
              <div className="h-full flex items-center justify-center text-gray-600 italic">
                Awaiting interaction...
              </div>
            ) : (
              messages.map((msg) => (
                <div key={msg.id} className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[80%] p-3 rounded-xl ${msg.sender === 'user'
                      ? 'bg-purple-600/20 text-purple-100 border border-purple-500/30'
                      : 'bg-cyan-900/20 text-cyan-50 border border-cyan-500/30'
                    }`}>
                    {msg.text}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right: AI Core Visualization */}
        <div className="w-96 bg-gray-900/30 backdrop-blur-lg border border-white/5 rounded-2xl flex flex-col items-center justify-center relative">

          {/* Glowing AI Core Animation */}
          <motion.div
            animate={{
              scale: isListening ? [1, 1.1, 1] : 1,
              rotate: isProcessing ? 360 : 0
            }}
            transition={{
              repeat: Infinity,
              duration: isListening ? 1.5 : 4,
              ease: "linear"
            }}
            className="relative w-48 h-48 flex items-center justify-center"
          >
            <div className="absolute inset-0 rounded-full bg-gradient-to-tr from-cyan-500 to-purple-600 opacity-20 blur-xl"></div>
            <div className="absolute inset-4 rounded-full border border-cyan-500/30 shadow-[0_0_30px_rgba(34,211,238,0.2)]"></div>
            <div className="absolute inset-8 rounded-full border border-purple-500/30"></div>
            <div className="w-16 h-16 rounded-full bg-gradient-to-tr from-cyan-400 to-purple-500 shadow-[0_0_40px_#22d3ee] flex items-center justify-center">
              <Mic size={24} className="text-gray-950" />
            </div>
          </motion.div>

          <div className="mt-12 text-center">
            <h2 className="text-xl font-light text-gray-200">
              {isListening ? "Listening...(Click to stop)" : isProcessing ? "Synthesizing..." : "Standby (Click to speak)"}
            </h2>
            <p className="text-sm text-gray-500 mt-2">Wake word active</p>
          </div>
        </div>
      </main>
    </div>
  );
}