// SECTION: IMPORTS
// Description: Imports icons, React hooks, and styling utilities for the RAG chatbot panel.

import {
  Bot, Send, Loader2, Upload, Trash2, FileText, ChevronDown, ChevronUp,
  Settings, Key, Cpu, Database, AlertCircle, CheckCircle2, BookOpen
} from 'lucide-react';
import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { cn } from '../lib/utils';


// SECTION: TYPES
// Description: Defines message, document, model, and status shapes used throughout the chatbot.

interface Message {
  id: string;
  role: 'user' | 'assistant';
  text: string;
  sources?: { filename: string; text: string }[];
  model?: string;
}

interface RagDocument {
  filename: string;
  chunks: number;
  size_bytes: number;
}

interface ModelInfo {
  id: string;
  label: string;
  type: string;
  requires_api_key: boolean;
  description: string;
  installed?: boolean;
}

interface RagStatus {
  api_key_configured: boolean;
  chunk_count: number;
  selected_model: string;
  gpu_available: boolean;
  gpu_name: string | null;
}


// SECTION: RAG BOT COMPONENT
// Description: Full-featured RAG chatbot with message history, source citations, settings panel, and document management.

export function RagBot() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<RagStatus | null>(null);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [documents, setDocuments] = useState<RagDocument[]>([]);
  const [expandedSources, setExpandedSources] = useState<Set<string>>(new Set());
  const [showSettings, setShowSettings] = useState(false);
  const [showDocs, setShowDocs] = useState(false);
  const [apiKeyInput, setApiKeyInput] = useState('');
  const [selectedModel, setSelectedModel] = useState('');
  const [settingsSaving, setSettingsSaving] = useState(false);
  const [settingsMsg, setSettingsMsg] = useState('');
  const [docUploading, setDocUploading] = useState(false);
  const [docMsg, setDocMsg] = useState('');
  const docInputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchStatus();
    fetchModels();
    fetchDocuments();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const fetchStatus = async () => {
    try {
      const res = await fetch('/api/rag/status');
      const data = await res.json();
      setStatus(data);
      setSelectedModel(data.selected_model || '');
    } catch (e) {
      console.error('Failed to fetch RAG status', e);
    }
  };

  const fetchModels = async () => {
    try {
      const res = await fetch('/api/rag/models');
      const data = await res.json();
      setModels(Array.isArray(data) ? data : []);
    } catch (e) {
      console.error('Failed to fetch models', e);
    }
  };

  const fetchDocuments = async () => {
    try {
      const res = await fetch('/api/rag/documents');
      const data = await res.json();
      setDocuments(Array.isArray(data) ? data : []);
    } catch (e) {
      console.error('Failed to fetch documents', e);
    }
  };

  const sendMessage = async () => {
    const query = input.trim();
    if (!query || loading) return;

    const userMsg: Message = { id: Date.now().toString(), role: 'user', text: query };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const res = await fetch('/api/rag/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
      });
      const data = await res.json();
      const assistantMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        text: data.answer || data.error || 'No response.',
        sources: data.sources || [],
        model: data.model_used,
      };
      setMessages(prev => [...prev, assistantMsg]);
    } catch (e) {
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        text: '⚠️ Failed to reach the RAG backend. Please check that the server is running.',
      }]);
    } finally {
      setLoading(false);
    }
  };

  const saveSettings = async () => {
    setSettingsSaving(true);
    setSettingsMsg('');
    const body: Record<string, string> = {};
    if (apiKeyInput.trim()) body.api_key = apiKeyInput.trim();
    if (selectedModel) body.model_id = selectedModel;
    if (!Object.keys(body).length) {
      setSettingsMsg('No changes to save.');
      setSettingsSaving(false);
      return;
    }
    try {
      const res = await fetch('/api/rag/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (data.error) throw new Error(data.error);
      setSettingsMsg('Settings saved.');
      setApiKeyInput('');
      await fetchStatus();
    } catch (e: unknown) {
      setSettingsMsg(`Error: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setSettingsSaving(false);
    }
  };

  const uploadDocument = async (file: File) => {
    setDocUploading(true);
    setDocMsg('');
    const formData = new FormData();
    formData.append('file', file);
    try {
      const res = await fetch('/api/rag/upload', { method: 'POST', body: formData });
      const data = await res.json();
      if (data.error) throw new Error(data.error);
      setDocMsg(`Indexed: ${data.chunks_count} chunks from ${file.name}`);
      await fetchDocuments();
      await fetchStatus();
    } catch (e: unknown) {
      setDocMsg(`Error: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setDocUploading(false);
    }
  };

  const deleteDocument = async (filename: string) => {
    try {
      await fetch(`/api/rag/documents/${encodeURIComponent(filename)}`, { method: 'DELETE' });
      await fetchDocuments();
      await fetchStatus();
    } catch (e) {
      console.error(e);
    }
  };

  const toggleSources = (id: string) => {
    setExpandedSources(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  return (
    <div className="space-y-4">

      {/* SECTION: HEADER */}
      <div className="flex items-center justify-between border-b dark:border-zinc-800 border-zinc-200 pb-2">
        <h2 className="text-xl font-bold dark:text-white text-zinc-900 flex items-center gap-2">
          <Bot className="w-5 h-5 text-violet-500" />
          RAG Conservation Bot
        </h2>
        <div className="flex items-center gap-2">
          <button
            onClick={() => { setShowDocs(!showDocs); setShowSettings(false); }}
            className={cn("flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-colors",
              showDocs ? "bg-violet-500/20 text-violet-500" : "text-zinc-500 hover:bg-zinc-100 dark:hover:bg-zinc-800")}
          >
            <Database className="w-3.5 h-3.5" /> Documents
          </button>
          <button
            onClick={() => { setShowSettings(!showSettings); setShowDocs(false); }}
            className={cn("flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-colors",
              showSettings ? "bg-violet-500/20 text-violet-500" : "text-zinc-500 hover:bg-zinc-100 dark:hover:bg-zinc-800")}
          >
            <Settings className="w-3.5 h-3.5" /> Settings
          </button>
        </div>
      </div>

      {/* SECTION: STATUS BAR */}
      {status && (
        <div className="flex flex-wrap items-center gap-3 text-xs">
          <StatusBadge
            ok={status.api_key_configured}
            label={status.api_key_configured ? 'API Ready' : 'No API Key'}
          />
          <span className="flex items-center gap-1 text-zinc-500">
            <Cpu className="w-3.5 h-3.5" />{status.selected_model}
          </span>
          <span className="flex items-center gap-1 text-zinc-500">
            <BookOpen className="w-3.5 h-3.5" />{status.chunk_count} chunks indexed
          </span>
          {status.gpu_available && (
            <span className="flex items-center gap-1 text-emerald-500 font-bold">
              GPU: {status.gpu_name}
            </span>
          )}
        </div>
      )}

      {/* SECTION: SETTINGS PANEL */}
      <AnimatePresence>
        {showSettings && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <div className="p-5 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 space-y-4">
              <h3 className="text-sm font-bold text-zinc-500 uppercase tracking-wider flex items-center gap-2">
                <Key className="w-4 h-4" /> Settings
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-xs text-zinc-500 font-bold uppercase tracking-wider">Gemini API Key</label>
                  <input
                    type="password"
                    placeholder="AIza..."
                    value={apiKeyInput}
                    onChange={e => setApiKeyInput(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 text-sm dark:text-white focus:outline-none focus:ring-2 focus:ring-violet-500"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-xs text-zinc-500 font-bold uppercase tracking-wider">Model</label>
                  <select
                    value={selectedModel}
                    onChange={e => setSelectedModel(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 text-sm dark:text-white focus:outline-none focus:ring-2 focus:ring-violet-500"
                  >
                    {models.map(m => (
                      <option key={m.id} value={m.id}>{m.label}{m.type === 'ollama' && !m.installed ? ' (not installed)' : ''}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <button
                  onClick={saveSettings}
                  disabled={settingsSaving}
                  className="px-4 py-2 rounded-lg bg-violet-600 text-white text-sm font-bold hover:bg-violet-700 disabled:opacity-50 flex items-center gap-2"
                >
                  {settingsSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
                  Save
                </button>
                {settingsMsg && (
                  <span className={cn("text-xs font-medium", settingsMsg.startsWith('Error') ? "text-red-500" : "text-emerald-500")}>
                    {settingsMsg}
                  </span>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* SECTION: DOCUMENT MANAGEMENT PANEL */}
      <AnimatePresence>
        {showDocs && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <div className="p-5 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold text-zinc-500 uppercase tracking-wider flex items-center gap-2">
                  <Database className="w-4 h-4" /> Knowledge Base
                </h3>
                <button
                  onClick={() => docInputRef.current?.click()}
                  disabled={docUploading}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-violet-600 text-white text-xs font-bold hover:bg-violet-700 disabled:opacity-50"
                >
                  {docUploading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Upload className="w-3.5 h-3.5" />}
                  Upload
                </button>
                <input
                  ref={docInputRef}
                  type="file"
                  accept=".txt,.pdf,.docx"
                  className="hidden"
                  onChange={e => e.target.files && uploadDocument(e.target.files[0])}
                />
              </div>

              {docMsg && (
                <p className={cn("text-xs font-medium", docMsg.startsWith('Error') ? "text-red-500" : "text-emerald-500")}>
                  {docMsg}
                </p>
              )}

              {documents.length === 0 ? (
                <p className="text-sm text-zinc-400 italic">No documents indexed yet. Upload a TXT, PDF, or DOCX file.</p>
              ) : (
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {documents.map(doc => (
                    <div key={doc.filename} className="flex items-center justify-between p-3 rounded-lg bg-zinc-50 dark:bg-zinc-800">
                      <div className="flex items-center gap-2 min-w-0">
                        <FileText className="w-4 h-4 text-violet-500 shrink-0" />
                        <div className="min-w-0">
                          <p className="text-xs font-bold dark:text-white text-zinc-900 truncate">{doc.filename}</p>
                          <p className="text-[10px] text-zinc-400">{doc.chunks} chunks · {(doc.size_bytes / 1024).toFixed(1)} KB</p>
                        </div>
                      </div>
                      <button
                        onClick={() => deleteDocument(doc.filename)}
                        className="ml-2 p-1.5 rounded-lg hover:bg-red-50 dark:hover:bg-red-500/10 text-zinc-400 hover:text-red-500 transition-colors"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* SECTION: CHAT THREAD */}
      <div className="rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 flex flex-col" style={{ minHeight: '420px' }}>
        <div className="flex-1 overflow-y-auto p-4 space-y-4 max-h-[520px]">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-64 text-zinc-400 gap-3">
              <Bot className="w-12 h-12 opacity-20" />
              <p className="font-medium text-sm">Ask a conservation question</p>
              <p className="text-xs text-center max-w-xs">
                The bot answers from indexed conservation documents. Upload knowledge base files via the Documents panel.
              </p>
            </div>
          )}

          {messages.map(msg => (
            <div key={msg.id} className={cn("flex", msg.role === 'user' ? "justify-end" : "justify-start")}>
              <div className={cn(
                "max-w-[80%] space-y-2",
                msg.role === 'user' ? "items-end" : "items-start"
              )}>
                <div className={cn(
                  "px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap",
                  msg.role === 'user'
                    ? "bg-violet-600 text-white rounded-br-sm"
                    : "bg-zinc-100 dark:bg-zinc-800 dark:text-white text-zinc-900 rounded-bl-sm"
                )}>
                  {msg.text}
                </div>

                {msg.role === 'assistant' && msg.sources && msg.sources.length > 0 && (
                  <div className="w-full">
                    <button
                      onClick={() => toggleSources(msg.id)}
                      className="flex items-center gap-1 text-xs text-zinc-400 hover:text-violet-500 transition-colors font-medium"
                    >
                      {expandedSources.has(msg.id) ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                      {msg.sources.length} source{msg.sources.length !== 1 ? 's' : ''}
                      {msg.model && <span className="ml-2 opacity-60">· {msg.model}</span>}
                    </button>
                    <AnimatePresence>
                      {expandedSources.has(msg.id) && (
                        <motion.div
                          initial={{ opacity: 0, height: 0 }}
                          animate={{ opacity: 1, height: 'auto' }}
                          exit={{ opacity: 0, height: 0 }}
                          className="overflow-hidden mt-2 space-y-2"
                        >
                          {msg.sources.map((s, i) => (
                            <div key={i} className="p-3 rounded-xl bg-zinc-50 dark:bg-zinc-800/50 border border-zinc-200 dark:border-zinc-700">
                              <p className="text-[10px] font-bold text-violet-500 uppercase tracking-wider mb-1">
                                [{i + 1}] {s.filename}
                              </p>
                              <p className="text-xs text-zinc-500 dark:text-zinc-400 line-clamp-3">{s.text}…</p>
                            </div>
                          ))}
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                )}
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex justify-start">
              <div className="px-4 py-3 rounded-2xl rounded-bl-sm bg-zinc-100 dark:bg-zinc-800 flex items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin text-violet-500" />
                <span className="text-sm text-zinc-500">Thinking...</span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* SECTION: INPUT BAR */}
        <div className="border-t dark:border-zinc-800 border-zinc-200 p-4">
          {status && !status.api_key_configured && (
            <div className="flex items-center gap-2 mb-3 p-2 rounded-lg bg-amber-50 dark:bg-amber-500/10 text-amber-700 dark:text-amber-400 text-xs">
              <AlertCircle className="w-4 h-4 shrink-0" />
              No API key configured. Open Settings to add a Gemini API key or select a local Ollama model.
            </div>
          )}
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="Ask about artwork conservation..."
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && !e.shiftKey && sendMessage()}
              className="flex-1 px-4 py-2.5 rounded-xl bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 text-sm dark:text-white focus:outline-none focus:ring-2 focus:ring-violet-500"
            />
            <button
              onClick={sendMessage}
              disabled={loading || !input.trim()}
              className="px-4 py-2.5 rounded-xl bg-violet-600 text-white font-bold hover:bg-violet-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}


// SECTION: SUBCOMPONENTS
// Description: Small status indicator badge.

function StatusBadge({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span className={cn(
      "flex items-center gap-1 px-2 py-0.5 rounded-full font-bold text-[10px] uppercase tracking-wider",
      ok ? "bg-emerald-500/10 text-emerald-500" : "bg-amber-500/10 text-amber-500"
    )}>
      <span className={cn("w-1.5 h-1.5 rounded-full", ok ? "bg-emerald-500" : "bg-amber-500")} />
      {label}
    </span>
  );
}
