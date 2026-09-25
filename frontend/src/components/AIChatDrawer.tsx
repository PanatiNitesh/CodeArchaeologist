import React, { useState } from 'react';
import { 
  Bot, 
  Send, 
  Sparkles, 
  CheckCircle2, 
  FileCode, 
  GitCommit, 
  X,
  CornerDownLeft,
  ChevronRight,
  ShieldCheck
} from 'lucide-react';
import { RAGAnswerResponse, EvidenceItem } from '../api/client';

interface AIChatDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  onAskQuestion: (question: string) => Promise<RAGAnswerResponse>;
  onSelectFile: (filePath: string) => void;
  initialPrompt?: string;
}

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  evidence?: EvidenceItem[];
  sources?: Record<string, number>;
  confidence?: number;
}

export const AIChatDrawer: React.FC<AIChatDrawerProps> = ({
  isOpen,
  onClose,
  onAskQuestion,
  onSelectFile,
  initialPrompt
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: 'assistant',
      content: (
        "Welcome to **CodeArchaeologist AI Assistant**.\n" +
        "I synthesize answers grounded strictly in your **AST Dependency Graph**, **Multi-Tier Call Chains**, and **Empirical Git History**.\n\n" +
        "Every claim cites verifiable source lines and commit hashes."
      )
    }
  ]);
  const [input, setInput] = useState(initialPrompt || '');
  const [loading, setLoading] = useState(false);

  const suggestedPrompts = [
    "Why was Redis introduced?",
    "What caused the 2024 payment timeout bug?",
    "Which commits introduced security patches?",
    "What would be affected if paymentService.ts is modified?",
    "How does authentication token validation flow across tiers?",
    "Which components depend on UserService?"
  ];

  const handleSend = async (questionToSend?: string) => {
    const q = (questionToSend || input).trim();
    if (!q || loading) return;

    setMessages(prev => [...prev, { role: 'user', content: q }]);
    setInput('');
    setLoading(true);

    try {
      const response = await onAskQuestion(q);
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: response.answer,
          evidence: response.evidence,
          sources: response.retrieval_sources,
          confidence: response.confidence_score
        }
      ]);
    } catch (err) {
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: `Synthesis error: ${err}`
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-y-0 right-0 w-full max-w-lg bg-[#0e0f14] border-l border-[var(--border-hairline)] z-50 flex flex-col shadow-2xl select-none">
      {/* Drawer Header */}
      <div className="h-12 px-4 border-b border-[var(--border-hairline)] flex items-center justify-between bg-[#121318]">
        <div className="flex items-center gap-2.5">
          <div className="w-6 h-6 rounded bg-indigo-600/20 border border-indigo-500/40 flex items-center justify-center text-indigo-400">
            <Bot className="w-3.5 h-3.5" />
          </div>
          <div>
            <span className="font-semibold text-xs text-white font-mono flex items-center gap-2">
              CodeArchaeologist Assistant
              <span className="px-1.5 py-0.2 rounded text-[9px] bg-indigo-950 text-indigo-400 border border-indigo-800">
                EVIDENCE RAG
              </span>
            </span>
          </div>
        </div>

        <button onClick={onClose} className="text-zinc-500 hover:text-zinc-200 text-xs font-mono">
          ✕
        </button>
      </div>

      {/* Suggested Inquiries */}
      <div className="p-3 border-b border-[var(--border-hairline)] bg-[#101116]">
        <span className="text-[10px] font-mono uppercase tracking-wider text-zinc-500 block mb-1.5">
          Suggested Inquiries:
        </span>
        <div className="flex flex-wrap gap-1">
          {suggestedPrompts.map((p, idx) => (
            <button
              key={idx}
              onClick={() => handleSend(p)}
              disabled={loading}
              className="text-[10.5px] px-2 py-0.5 rounded bg-[#161720] hover:bg-[#1f212c] border border-zinc-800 text-zinc-300 transition-colors font-sans text-left"
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3.5 select-text">
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}
          >
            <div
              className={`max-w-[94%] rounded-lg p-3 text-xs leading-relaxed ${
                msg.role === 'user'
                  ? 'bg-indigo-600 text-white font-sans'
                  : 'bg-[#14151b] text-zinc-200 border border-zinc-800/80 font-sans'
              }`}
            >
              {/* Content */}
              <div className="whitespace-pre-line space-y-1.5">
                {msg.content}
              </div>

              {/* Verifiable Evidence Drawer */}
              {msg.evidence && msg.evidence.length > 0 && (
                <div className="mt-3 pt-2.5 border-t border-zinc-800 space-y-2">
                  <div className="flex items-center justify-between font-mono">
                    <span className="text-[10px] font-semibold text-cyan-400 flex items-center gap-1 uppercase tracking-wider">
                      <ShieldCheck className="w-3 h-3 text-cyan-400" />
                      Verifiable Archaeological Citations ({msg.evidence.length})
                    </span>
                    {msg.confidence && (
                      <span className="text-[10px] text-zinc-500">
                        Confidence: {Math.round(msg.confidence * 100)}%
                      </span>
                    )}
                  </div>

                  <div className="space-y-1">
                    {msg.evidence.map((ev, eIdx) => (
                      <div
                        key={eIdx}
                        className="p-2 rounded bg-[#0d0e13] border border-zinc-800 hover:border-zinc-700 text-[11px] font-mono transition-colors"
                      >
                        <div className="flex items-center justify-between mb-0.5">
                          <button
                            onClick={() => onSelectFile(ev.file_path)}
                            className="font-bold text-cyan-300 hover:underline flex items-center gap-1 truncate text-left"
                          >
                            <FileCode className="w-3 h-3 text-cyan-400 shrink-0" />
                            <span className="truncate">{ev.file_path}</span>
                            {ev.line_start && (
                              <span className="text-zinc-500 font-normal">
                                :L{ev.line_start}–{ev.line_end}
                              </span>
                            )}
                          </button>

                          {ev.commit_hash && (
                            <span className="text-[9.5px] text-indigo-400 bg-indigo-950/80 px-1 py-0.5 rounded border border-indigo-900/60 shrink-0">
                              {ev.commit_hash}
                            </span>
                          )}
                        </div>

                        {ev.commit_message && (
                          <div className="text-[10px] text-zinc-400 flex items-center gap-1 mb-0.5">
                            <GitCommit className="w-3 h-3 text-zinc-500 shrink-0" />
                            <span className="truncate">"{ev.commit_message}"</span>
                          </div>
                        )}

                        <p className="text-[10px] text-zinc-500 italic font-sans leading-tight">
                          {ev.relevance_reason}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex items-center gap-2 p-2 text-xs text-indigo-400 font-mono">
            <Sparkles className="w-3.5 h-3.5 animate-spin" />
            <span>Consulting dependency graph & Git commit logs...</span>
          </div>
        )}
      </div>

      {/* Input Field */}
      <div className="p-3 border-t border-[var(--border-hairline)] bg-[#121318]">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="flex items-center gap-2"
        >
          <input
            type="text"
            placeholder="Ask about architecture, Redis, blast reach, payment..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={loading}
            className="flex-1 bg-[#090a0e] border border-zinc-800 rounded px-3 py-1.5 text-xs font-mono text-zinc-200 placeholder-zinc-600 focus:outline-none focus:border-indigo-500"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="btn-studio btn-studio-primary px-3 py-1.5"
          >
            <CornerDownLeft className="w-3.5 h-3.5" />
          </button>
        </form>
      </div>
    </div>
  );
};
