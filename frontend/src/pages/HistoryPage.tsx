import React, { useEffect, useState } from 'react';
import { ChevronLeft, MessageSquare, Trash2, Loader2 } from 'lucide-react';

interface HistoryMessage {
    sender: string;
    content: string;
    timestamp: string;
}

interface HistorySession {
    id: number;
    started_at: string;
    ended_at: string;
    messages: HistoryMessage[];
}

interface HistoryPageProps {
    onBack: () => void;
}

const API_BASE = 'http://localhost:8000';

function formatDate(iso: string): string {
    try {
        return new Date(iso).toLocaleString(undefined, {
            month: 'short',
            day: 'numeric',
            hour: 'numeric',
            minute: '2-digit',
        });
    } catch {
        return iso;
    }
}

export default function HistoryPage({ onBack }: HistoryPageProps) {
    const [sessions, setSessions] = useState<HistorySession[]>([]);
    const [selected, setSelected] = useState<HistorySession | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fetchSessions = async () => {
        setLoading(true);
        setError(null);
        try {
            const res = await fetch(`${API_BASE}/history`);
            if (!res.ok) throw new Error(`Server responded ${res.status}`);
            const data: HistorySession[] = await res.json();
            setSessions(data);
        } catch (err) {
            console.error('Failed to load chat history:', err);
            setError('Could not load chat history. Is the backend running?');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchSessions();
    }, []);

    const handleDelete = async (id: number, e: React.MouseEvent) => {
        e.stopPropagation();
        try {
            await fetch(`${API_BASE}/history/${id}`, { method: 'DELETE' });
            setSessions((prev) => prev.filter((s) => s.id !== id));
            if (selected?.id === id) setSelected(null);
        } catch (err) {
            console.error('Failed to delete session:', err);
        }
    };

    // ── Conversation view for one saved session ─────────────────────────────
    if (selected) {
        return (
            <div className="h-screen w-screen bg-slate-950 text-slate-100 flex flex-col font-sans overflow-hidden">
                <header className="h-16 bg-slate-900/60 backdrop-blur-md border-b border-slate-800/80 px-6 flex items-center gap-3 z-20">
                    <button
                        onClick={() => setSelected(null)}
                        className="p-2 rounded-md hover:bg-slate-800/70 transition-colors"
                        aria-label="Back to session list"
                    >
                        <ChevronLeft className="w-5 h-5 text-slate-300" />
                    </button>
                    <div>
                        <h1 className="text-sm font-bold tracking-wider text-slate-100 uppercase">Session Transcript</h1>
                        <p className="text-[10px] tracking-widest text-slate-400 font-mono uppercase">
                            {formatDate(selected.started_at)} — {formatDate(selected.ended_at)}
                        </p>
                    </div>
                </header>

                <main className="flex-1 overflow-y-auto p-6 space-y-4 scrollbar-thin scrollbar-thumb-slate-800">
                    {selected.messages.map((msg, i) => (
                        <div
                            key={i}
                            className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}
                        >
                            <div
                                className={`max-w-[70%] px-4 py-3 rounded-2xl text-sm leading-relaxed shadow-lg ${msg.sender === 'user'
                                        ? 'bg-gradient-to-r from-cyan-600 to-cyan-500 text-white rounded-br-none border border-cyan-400/20'
                                        : 'bg-slate-900/80 backdrop-blur-md border border-slate-800 text-slate-200 rounded-bl-none font-sans'
                                    }`}
                            >
                                {msg.content}
                            </div>
                        </div>
                    ))}
                </main>
            </div>
        );
    }

    // ── List of saved sessions ───────────────────────────────────────────────
    return (
        <div className="h-screen w-screen bg-slate-950 text-slate-100 flex flex-col font-sans overflow-hidden">
            <header className="h-16 bg-slate-900/60 backdrop-blur-md border-b border-slate-800/80 px-6 flex items-center gap-3 z-20">
                <button
                    onClick={onBack}
                    className="p-2 rounded-md hover:bg-slate-800/70 transition-colors"
                    aria-label="Back to live view"
                >
                    <ChevronLeft className="w-5 h-5 text-slate-300" />
                </button>
                <div>
                    <h1 className="text-sm font-bold tracking-wider text-slate-100 uppercase">Chat History</h1>
                    <p className="text-[10px] tracking-widest text-slate-400 font-mono uppercase">Saved on "stop"</p>
                </div>
            </header>

            <main className="flex-1 overflow-y-auto p-6 space-y-3 scrollbar-thin scrollbar-thumb-slate-800">
                {loading && (
                    <div className="h-full flex flex-col items-center justify-center text-slate-500 gap-2">
                        <Loader2 className="w-6 h-6 animate-spin" />
                        <p className="text-xs font-mono uppercase tracking-widest">Loading sessions...</p>
                    </div>
                )}

                {!loading && error && (
                    <div className="h-full flex flex-col items-center justify-center text-rose-400 gap-2 text-center">
                        <p className="text-xs font-mono uppercase tracking-widest">{error}</p>
                    </div>
                )}

                {!loading && !error && sessions.length === 0 && (
                    <div className="h-full flex flex-col items-center justify-center text-slate-600 gap-2">
                        <MessageSquare className="w-10 h-10 stroke-[1.5] opacity-40" />
                        <p className="text-xs font-mono tracking-widest uppercase">No saved sessions yet</p>
                        <p className="text-[11px] text-slate-500">Say "stop" during a live session to save it here.</p>
                    </div>
                )}

                {!loading && !error && sessions.map((session) => {
                    const firstUserMsg = session.messages.find((m) => m.sender === 'user');
                    const preview = firstUserMsg?.content ?? session.messages[0]?.content ?? '(empty session)';
                    return (
                        <div
                            key={session.id}
                            onClick={() => setSelected(session)}
                            className="bg-slate-900/60 border border-slate-800 hover:border-slate-700 rounded-xl px-4 py-3 flex items-center justify-between cursor-pointer transition-colors"
                        >
                            <div className="min-w-0">
                                <p className="text-sm text-slate-200 truncate">{preview}</p>
                                <p className="text-[10px] font-mono uppercase tracking-widest text-slate-500 mt-1">
                                    {formatDate(session.started_at)} · {session.messages.length} turns
                                </p>
                            </div>
                            <button
                                onClick={(e) => handleDelete(session.id, e)}
                                className="p-2 rounded-md hover:bg-rose-500/10 text-slate-500 hover:text-rose-400 transition-colors shrink-0"
                                aria-label="Delete session"
                            >
                                <Trash2 className="w-4 h-4" />
                            </button>
                        </div>
                    );
                })}
            </main>
        </div>
    );
}