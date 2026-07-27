import { useEffect, useRef } from 'react';
import { useStore } from '../store/useStore';

export function useMayaAudio() {
    const wsRef = useRef<WebSocket | null>(null);
    const audioCtxRef = useRef<AudioContext | null>(null);
    const { setListening, setProcessing, addMessage } = useStore();

    useEffect(() => {
        // AudioContext must be created/resumed after a user gesture on some browsers.
        // We create it lazily here; it will auto-resume on first audio playback.
        audioCtxRef.current = new AudioContext();

        const ws = new WebSocket('ws://localhost:8000/ws/audio');

        // IMPORTANT: request binary frames as ArrayBuffer, not Blob.
        // Blob requires an extra async read step and has no MIME type,
        // which makes new Audio() silently fail on raw WAV data.
        ws.binaryType = 'arraybuffer';

        wsRef.current = ws;

        ws.onmessage = async (event) => {
            // 1. Handle JSON Status & Chat Updates
            if (typeof event.data === 'string') {
                const data = JSON.parse(event.data);

                if (data.type === 'state') {
                    if (data.status === 'listening') {
                        setListening(true);
                        setProcessing(false);
                    } else if (data.status === 'processing') {
                        setListening(false);
                        setProcessing(true);
                    } else if (data.status === 'standby') {
                        setListening(false);
                        setProcessing(false);
                    }
                } else if (data.type === 'text') {
                    addMessage({
                        id: Date.now().toString() + Math.random(),
                        sender: data.sender,
                        text: data.content,
                    });
                }
            }
            // 2. Handle Binary Audio (WAV bytes from Piper TTS)
            else if (event.data instanceof ArrayBuffer) {
                try {
                    const ctx = audioCtxRef.current!;
                    // Resume context if suspended (browser autoplay policy)
                    if (ctx.state === 'suspended') await ctx.resume();

                    // decodeAudioData handles the WAV header and decodes to PCM
                    const audioBuffer = await ctx.decodeAudioData(event.data);
                    const source = ctx.createBufferSource();
                    source.buffer = audioBuffer;
                    source.connect(ctx.destination);
                    source.start();
                } catch (err) {
                    console.error('[Maya TTS] Audio decode/playback failed:', err);
                }
            }
        };

        ws.onerror = (e) => console.error('[Maya WS] WebSocket error:', e);

        return () => {
            ws.close();
            audioCtxRef.current?.close();
        };
    }, [addMessage, setListening, setProcessing]);

    return {};
}
