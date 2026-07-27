import { create } from 'zustand';

interface Message {
  id: string;
  sender: 'user' | 'maya';
  text: string;
}

interface MayaState {
  isListening: boolean;
  isProcessing: boolean;
  messages: Message[];
  systemStatus: { cpu: number; ram: number; online: boolean };
  setListening: (val: boolean) => void;
  setProcessing: (val: boolean) => void;
  addMessage: (msg: Message) => void;
  updateStatus: (status: any) => void;
}

export const useStore = create<MayaState>((set) => ({
  isListening: false,
  isProcessing: false,
  messages: [],
  systemStatus: { cpu: 0, ram: 0, online: false },

  setListening: (val) => set({ isListening: val }),
  setProcessing: (val) => set({ isProcessing: val }),
  addMessage: (msg) => set((state) => ({ messages: [...state.messages, msg] })),
  updateStatus: (status) => set({ systemStatus: status }),
}));