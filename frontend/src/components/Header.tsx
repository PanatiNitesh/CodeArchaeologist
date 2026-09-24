import React, { useState } from 'react';
import { 
  GitFork, 
  Layers, 
  History, 
  Cpu, 
  PlusCircle, 
  Sparkles, 
  CheckCircle2, 
  ShieldAlert, 
  BarChart3,
  Search,
  ExternalLink
} from 'lucide-react';
import { RepositoryItem } from '../api/client';

interface HeaderProps {
  repositories: RepositoryItem[];
  currentRepoId: string;
  onSelectRepo: (id: string) => void;
  onIngest: (url: string) => Promise<void>;
  onLoadSample: () => Promise<void>;
  onOpenEval: () => void;
  loading: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  repositories,
  currentRepoId,
  onSelectRepo,
  onIngest,
  onLoadSample,
  onOpenEval,
  loading
}) => {
  const [showIngestModal, setShowIngestModal] = useState(false);
  const [inputUrl, setInputUrl] = useState('');
  const [ingestLoading, setIngestLoading] = useState(false);

  const currentRepo = repositories.find(r => r.id === currentRepoId);

  const handleIngestSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputUrl.trim()) return;
    setIngestLoading(true);
    try {
      await onIngest(inputUrl.trim());
      setShowIngestModal(false);
      setInputUrl('');
    } catch (err) {
      alert(`Ingestion failed: ${err}`);
    } finally {
      setIngestLoading(false);
    }
  };

  return (
    <header className="glass-header px-6 py-3 flex items-center justify-between sticky top-0 z-40 border-b border-subtle">
      {/* Brand & Subtitle */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-cyan-400 flex items-center justify-center shadow-lg shadow-indigo-500/25">
            <Layers className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="font-extrabold text-lg tracking-tight bg-gradient-to-r from-white via-slate-100 to-indigo-200 bg-clip-text text-transparent">
                CODEARCHAEOLOGIST
              </h1>
              <span className="badge badge-service text-[10px]">v1.0 ML Engine</span>
            </div>
            <p className="text-xs text-slate-400 font-medium">
              AI-Powered Software Evolution & Legacy Code Intelligence
            </p>
          </div>
        </div>

        {/* Repository Switcher */}
        <div className="hidden md:flex items-center ml-6 pl-6 border-l border-subtle">
          <div className="flex items-center gap-2 bg-slate-900/80 px-3 py-1.5 rounded-lg border border-subtle text-sm">
            <GitFork className="w-4 h-4 text-cyan-400" />
            <select
              value={currentRepoId}
              onChange={(e) => onSelectRepo(e.target.value)}
              className="bg-transparent text-slate-200 font-medium focus:outline-none cursor-pointer pr-4"
              disabled={loading}
            >
              {repositories.map(r => (
                <option key={r.id} value={r.id} className="bg-slate-900 text-white">
                  {r.name}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Metrics & Actions */}
      <div className="flex items-center gap-3">
        {currentRepo?.stats && (
          <div className="hidden lg:flex items-center gap-3 mr-2">
            <div className="flex items-center gap-1.5 px-3 py-1 rounded-md bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-mono font-medium">
              <span>Arch F1:</span>
              <span className="font-bold">{(currentRepo.stats.arch_f1 ?? 1.0).toFixed(2)}</span>
            </div>
            <div className="flex items-center gap-1.5 px-3 py-1 rounded-md bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 text-xs font-mono font-medium">
              <span>Blast F1:</span>
              <span className="font-bold">{(currentRepo.stats.blast_f1 ?? 0.85).toFixed(2)}</span>
            </div>
          </div>
        )}

        <button
          onClick={onOpenEval}
          className="btn-secondary text-xs py-1.5 px-3"
          title="View Phase 7 Architecture & Blast Radius Precision/Recall Evaluation"
        >
          <BarChart3 className="w-3.5 h-3.5 text-cyan-400" />
          <span>Evaluation Suite</span>
        </button>

        <button
          onClick={onLoadSample}
          disabled={loading}
          className="btn-secondary text-xs py-1.5 px-3"
          title="Load 2022-2026 Enterprise E-Commerce Evolution Demo"
        >
          <Sparkles className="w-3.5 h-3.5 text-amber-400" />
          <span>Demo Repo</span>
        </button>

        <button
          onClick={() => setShowIngestModal(true)}
          disabled={loading}
          className="btn-primary text-xs py-1.5 px-3.5"
        >
          <PlusCircle className="w-3.5 h-3.5" />
          <span>Analyze Repo</span>
        </button>
      </div>

      {/* Ingestion Modal */}
      {showIngestModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-md flex items-center justify-center z-50 p-4">
          <div className="glass-panel w-full max-w-lg p-6 bg-slate-900/95 border border-indigo-500/30">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-bold text-lg text-white flex items-center gap-2">
                <GitFork className="w-5 h-5 text-indigo-400" />
                Ingest GitHub or Local Repository
              </h3>
              <button 
                onClick={() => setShowIngestModal(false)}
                className="text-slate-400 hover:text-white text-lg font-bold"
              >
                &times;
              </button>
            </div>
            
            <p className="text-xs text-slate-400 mb-4 leading-relaxed">
              Enter a public GitHub URL (e.g. <code className="text-cyan-300">https://github.com/expressjs/express</code>) 
              or an absolute local folder path on your computer. CodeArchaeologist will clone, parse the AST, 
              mine historical commits, synthesize the dependency graph, and calibrate the blast radius ML model.
            </p>

            <form onSubmit={handleIngestSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Repository URL / Local Path:
                </label>
                <input
                  type="text"
                  placeholder="https://github.com/user/project or D:\projects\my-app"
                  value={inputUrl}
                  onChange={(e) => setInputUrl(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3.5 py-2 text-sm text-white focus:outline-none focus:border-indigo-500 font-mono"
                  required
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowIngestModal(false)}
                  className="btn-secondary text-xs"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={ingestLoading}
                  className="btn-primary text-xs"
                >
                  {ingestLoading ? 'Analyzing 8 Phases...' : 'Start Archaeology Analysis'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </header>
  );
};
