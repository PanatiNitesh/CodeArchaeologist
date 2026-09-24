import React, { useState } from 'react';
import { 
  Bot, 
  Send, 
  Sparkles, 
  CheckCircle2, 
  FileCode, 
  GitCommit, 
  ExternalLink, 
  BookOpen, 
  HelpCircle,
  X,
  MessageSquare
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
        "Welcome to **CodeArchaeologist Intelligence Chat**. " +
        "I query your AST dependency graph, multi-tier call flows, and historical Git archaeology to provide **evidence-based explanations** with clickable citations.\n\n" +
        "Try asking any question below or click a suggested prompt."
      )
    }
  ]);
  const [input, setInput] = useState(initialPrompt || '');
  const [loading, setLoading] = useState(false);

  const suggestedPrompts = [
    "How does authentication work?",
    "Why was Redis introduced?",
    "What changed in the payment module?",
    "Which components depend on UserService?",
    "What could break if I modify UserService.ts?",
    "Show me the most important architectural changes."
  ];

  const handleSend = async (questionToSend?: string) => {
    const q = (questionToSend || input).trim();
    if (!q || loading) return;

    // Add user message
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
          content: `Analysis failed: ${err}`
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-y-0 right-0 w-full max-w-xl bg-slate-950/95 border-l border-indigo-500/30 backdrop-blur-xl z-50 flex flex-col shadow-2xl">
      {/* Drawer Header */}
      <div className="p-4 border-b border-subtle flex items-center justify-between bg-slate-900/60">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-indigo-500/20 border border-indigo-500/40 flex items-center justify-center text-indigo-400">
            <Bot className="w-4 h-4" />
          </div>
          <div>
            <h3 className="font-bold text-sm text-white flex items-center gap-2">
              CodeArchaeologist AI
              <span className="badge badge-service text-[9px]">Evidence-Based RAG</span>
            </h3>
            <p className="text-[11px] text-slate-400 font-mono">
              Graph + AST + Git History + Embeddings
            </p>
          </div>
        </div>

        <button onClick={onClose} className="text-slate-400 hover:text-white p-1">
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Suggested Prompts Banner */}
      <div className="p-3 border-b border-subtle bg-slate-900/40">
        <span className="text-[10px] uppercase font-bold text-slate-400 block mb-1.5">
          Suggested Archaeological Inquiries:
        </span>
        <div className="flex flex-wrap gap-1.5">
          {suggestedPrompts.map((p, idx) => (
            <button
              key={idx}
              onClick={() => handleSend(p)}
              disabled={loading}
              className="text-[11px] px-2 py-1 rounded bg-slate-800/80 hover:bg-indigo-600/30 hover:border-indigo-500/50 border border-slate-700/60 text-slate-300 text-left transition-all"
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}
          >
            <div
              className={`max-w-[92%] rounded-xl p-3.5 text-xs leading-relaxed ${
                msg.role === 'user'
                  ? 'bg-indigo-600 text-white shadow-md'
                  : 'bg-slate-900/90 text-slate-200 border border-slate-800'
              }`}
            >
              {/* Message Content */}
              <div className="whitespace-pre-line space-y-2">
                {msg.content}
              </div>

              {/* Verified Evidence Drawer */}
              {msg.evidence && msg.evidence.length > 0 && (
                <div className="mt-3 pt-3 border-t border-slate-800/80 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-cyan-400 flex items-center gap-1">
                      <CheckCircle2 className="w-3 h-3 text-cyan-400" />
                      Verifiable Archaeological Evidence ({msg.evidence.length})
                    </span>
                    {msg.confidence && (
                      <span className="font-mono text-[10px] text-slate-400">
                        Confidence: {Math.round(msg.confidence * 100)}%
                      </span>
                    )}
                  </div>

                  <div className="space-y-1.5">
                    {msg.evidence.map((ev, eIdx) => (
                      <div
                        key={eIdx}
                        className="p-2 rounded bg-slate-950/80 border border-slate-800/90 hover:border-cyan-500/40 text-[11px] transition-colors"
                      >
                        <div className="flex items-center justify-between mb-1">
                          <button
                            onClick={() => onSelectFile(ev.file_path)}
                            className="font-mono font-bold text-cyan-300 hover:underline flex items-center gap-1 truncate text-left"
                          >
                            <FileCode className="w-3 h-3 text-cyan-400 shrink-0" />
                            <span className="truncate">{ev.file_path}</span>
                            {ev.line_start && (
                              <span className="text-slate-500 font-normal">
                                :L{ev.line_start}
                              </span>
                            )}
                          </button>

                          {ev.commit_hash && (
                            <span className="font-mono text-[10px] text-indigo-400 bg-indigo-500/10 px-1.5 py-0.5 rounded shrink-0">
                              {ev.commit_hash}
                            </span>
                          )}
                        </div>

                        {ev.commit_message && (
                          <div className="text-[10px] text-slate-400 flex items-center gap-1 mb-1">
                            <GitCommit className="w-3 h-3 text-slate-500 shrink-0" />
                            <span className="truncate font-mono">"{ev.commit_message}"</span>
                          </div>
                        )}

                        <p className="text-[10px] text-slate-400 italic">
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
          <div className="flex items-center gap-2 p-3 text-xs text-indigo-400 font-mono">
            <Sparkles className="w-4 h-4 animate-spin text-cyan-400" />
            <span>Consulting Software Graph & Git Archaeology...</span>
          </div>
        )}
      </div>

      {/* Input Field */}
      <div className="p-3 border-t border-subtle bg-slate-900/60">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="flex items-center gap-2"
        >
          <input
            type="text"
            placeholder="Ask anything about architecture, Redis, blast radius, payment..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={loading}
            className="flex-1 bg-slate-950 border border-slate-700/80 rounded-lg px-3.5 py-2 text-xs text-white focus:outline-none focus:border-indigo-500 font-mono"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="btn-primary p-2 rounded-lg"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>
    </div>
  );
};
