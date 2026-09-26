import React, { useState } from 'react';
import { 
  GitBranch, 
  Layers, 
  Plus, 
  Sparkles, 
  BarChart2, 
  Terminal, 
  Check, 
  Copy,
  ChevronDown,
  Activity,
  FolderGit2
} from 'lucide-react';
import { RepositoryItem, api } from '../api/client';

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
  const [ingestStatusText, setIngestStatusText] = useState('');
  const [copied, setCopied] = useState(false);

  const currentRepo = repositories.find(r => r.id === currentRepoId);

  const handleIngestSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const url = inputUrl.trim();
    if (!url) return;
    setIngestLoading(true);
    setIngestStatusText('Initiating repository archaeology...');
    try {
      const { task_id } = await api.ingestAsync(url);
      setIngestStatusText('Ingestion task queued. Processing...');
      
      let attempts = 0;
      const pollInterval = setInterval(async () => {
        attempts++;
        try {
          const statusData = await api.getTaskStatus(task_id);
          if (statusData.progress) {
            setIngestStatusText(statusData.progress);
          }
          if (statusData.status === 'completed') {
            clearInterval(pollInterval);
            setIngestLoading(false);
            setShowIngestModal(false);
            setInputUrl('');
            setIngestStatusText('');
            if (statusData.repo_id) {
              onSelectRepo(statusData.repo_id);
            } else {
              await onIngest(url);
            }
          } else if (statusData.status === 'failed') {
            clearInterval(pollInterval);
            setIngestLoading(false);
            setIngestStatusText('');
            alert(`Ingestion failed: ${statusData.error || 'Unknown error'}`);
          } else if (attempts > 120) {
            clearInterval(pollInterval);
            setIngestLoading(false);
            setIngestStatusText('');
            alert('Ingestion timed out.');
          }
        } catch (err) {
          console.warn('Poll error:', err);
        }
      }, 1500);
    } catch (err) {
      try {
        setIngestStatusText('Running sync analysis...');
        await onIngest(url);
        setShowIngestModal(false);
        setInputUrl('');
      } catch (syncErr) {
        alert(`Ingestion failed: ${syncErr}`);
      } finally {
        setIngestLoading(false);
        setIngestStatusText('');
      }
    }
  };

  const copyRepoPath = () => {
    if (currentRepo?.path) {
      navigator.clipboard.writeText(currentRepo.path);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    }
  };

  return (
    <header className="h-12 px-4 border-b border-[var(--border-hairline)] bg-[#0d0e12] flex items-center justify-between shrink-0 select-none z-30">
      {/* Left: Product Brand & Active Repository */}
      <div className="flex items-center gap-4">
        {/* Brand Lockup */}
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-md bg-indigo-600/20 border border-indigo-500/40 flex items-center justify-center text-indigo-400">
            <Layers className="w-4 h-4" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="font-semibold text-xs tracking-tight text-white uppercase font-mono">
              CodeArchaeologist
            </span>
            <span className="text-[10px] text-zinc-500 font-mono hidden md:inline">
              v1.0.0
            </span>
          </div>
        </div>

        <div className="h-4 w-px bg-zinc-800" />

        {/* Repository Dropdown Selector */}
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-[#16171d] border border-zinc-800 hover:border-zinc-700 transition-colors">
            <FolderGit2 className="w-3.5 h-3.5 text-zinc-400" />
            <select
              value={currentRepoId}
              onChange={(e) => onSelectRepo(e.target.value)}
              className="bg-transparent text-xs text-zinc-200 font-mono font-medium focus:outline-none cursor-pointer appearance-none pr-3"
              disabled={loading}
            >
              {repositories.map(r => (
                <option key={r.id} value={r.id} className="bg-[#16171d] text-zinc-200">
                  {r.name}
                </option>
              ))}
            </select>
            <ChevronDown className="w-3 h-3 text-zinc-500 -ml-2 pointer-events-none" />
          </div>

          {currentRepo && (
            <div className="hidden lg:flex items-center gap-2 text-[11px] font-mono text-zinc-400">
              <span className="flex items-center gap-1 text-zinc-500">
                <GitBranch className="w-3 h-3 text-zinc-500" />
                {currentRepo.default_branch || 'main'}
              </span>
              <button 
                onClick={copyRepoPath}
                className="hover:text-zinc-200 transition-colors flex items-center gap-1"
                title="Copy local repository path"
              >
                {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Center: System Status Indicator */}
      <div className="hidden xl:flex items-center gap-2 font-mono text-[11px] text-zinc-500">
        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
        <span>8 PHASES ACTIVE</span>
        <span className="text-zinc-700">•</span>
        <span>GRAPH-FIRST DETERMINISTIC ENGINE</span>
      </div>

      {/* Right: Actions */}
      <div className="flex items-center gap-2">
        {currentRepo?.stats && (
          <div className="hidden md:flex items-center gap-2 mr-2 font-mono text-[11px]">
            <div className="px-2 py-0.5 rounded bg-emerald-950/40 border border-emerald-900/60 text-emerald-400">
              Arch F1: <span className="font-semibold">{(currentRepo.stats.arch_f1 ?? 1.0).toFixed(2)}</span>
            </div>
            <div className="px-2 py-0.5 rounded bg-indigo-950/40 border border-indigo-900/60 text-indigo-400">
              Blast F1: <span className="font-semibold">{(currentRepo.stats.blast_f1 ?? 0.85).toFixed(2)}</span>
            </div>
          </div>
        )}

        <button
          onClick={onOpenEval}
          className="btn-studio btn-studio-secondary p-1.5 sm:px-2.5 sm:py-1"
          title="Empirical Phase 7 Benchmarks"
        >
          <BarChart2 className="w-3.5 h-3.5 text-zinc-400" />
          <span className="hidden md:inline">Evaluation</span>
        </button>

        <button
          onClick={onLoadSample}
          disabled={loading}
          className="btn-studio btn-studio-secondary p-1.5 sm:px-2.5 sm:py-1"
          title="Reload 2022-2026 Enterprise E-Commerce Evolution Benchmark"
        >
          <Sparkles className="w-3.5 h-3.5 text-amber-400" />
          <span className="hidden sm:inline">Demo</span>
        </button>

        {/* 1-Click Live GitHub Demo Pathway */}
        <div className="relative group">
          <button
            disabled={loading}
            className="btn-studio btn-studio-secondary flex items-center gap-1.5 text-cyan-300 border-cyan-900/40 hover:border-cyan-700/60 p-1.5 sm:px-2.5 sm:py-1"
            title="1-Click Analyze Real Open-Source GitHub Repositories"
          >
            <FolderGit2 className="w-3.5 h-3.5 text-cyan-400" />
            <span className="hidden lg:inline">Live Demo</span>
            <ChevronDown className="w-3 h-3 text-zinc-500 hidden sm:inline" />
          </button>
          
          <div className="hidden group-hover:block absolute right-0 top-full mt-1 w-64 bg-[#14151f] border border-zinc-800 rounded-lg shadow-2xl p-1.5 z-50">
            <span className="text-[9.5px] uppercase font-mono text-zinc-400 font-semibold px-2 py-1 block border-b border-zinc-800/80 mb-1">
              Live Ingestion Benchmark Presets:
            </span>
            {[
              { name: 'expressjs/express', desc: 'Node.js REST Framework (30k+ commits)', url: 'https://github.com/expressjs/express' },
              { name: 'fastapi/fastapi', desc: 'Python ASGI Web Framework', url: 'https://github.com/fastapi/fastapi' },
              { name: 'pallets/flask', desc: 'Python WSGI Microframework', url: 'https://github.com/pallets/flask' }
            ].map(repo => (
              <button
                key={repo.name}
                type="button"
                onClick={() => onIngest(repo.url)}
                disabled={loading}
                className="w-full text-left p-2 rounded hover:bg-[#1e202e] transition-colors font-mono block"
              >
                <div className="text-xs font-semibold text-zinc-200">⚡ {repo.name}</div>
                <div className="text-[10px] text-zinc-500">{repo.desc}</div>
              </button>
            ))}
          </div>
        </div>

        <button
          onClick={() => setShowIngestModal(true)}
          disabled={loading}
          className="btn-studio btn-studio-primary p-1.5 sm:px-2.5 sm:py-1"
        >
          <Plus className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">Ingest</span>
        </button>
      </div>

      {/* Ingest Modal */}
      {showIngestModal && (
        <div className="fixed inset-0 bg-black/75 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="studio-panel-elevated w-full max-w-lg p-5 bg-[#121318]">
            <div className="flex items-center justify-between pb-3 border-b border-[var(--border-hairline)] mb-4">
              <div className="flex items-center gap-2">
                <Terminal className="w-4 h-4 text-indigo-400" />
                <h3 className="font-semibold text-sm text-white font-mono">
                  Ingest Repository
                </h3>
              </div>
              <button 
                onClick={() => setShowIngestModal(false)}
                className="text-zinc-500 hover:text-zinc-200 text-sm font-mono"
              >
                ✕
              </button>
            </div>

            <p className="text-xs text-zinc-400 mb-4 leading-relaxed">
              Provide a public Git URL or local folder. The system will extract AST symbols, construct the dependency graph, classify components, and mine Git evolution history.
            </p>

            <form onSubmit={handleIngestSubmit} className="space-y-4">
              <div>
                <label className="block text-[11px] font-mono text-zinc-400 uppercase tracking-wider mb-1">
                  Source URL or Local Path:
                </label>
                <input
                  type="text"
                  placeholder="https://github.com/expressjs/express or D:\code\my-project"
                  value={inputUrl}
                  onChange={(e) => setInputUrl(e.target.value)}
                  className="w-full bg-[#0a0b0e] border border-zinc-800 rounded px-3 py-2 text-xs font-mono text-zinc-200 focus:outline-none focus:border-indigo-500"
                  required
                />
                
                {/* 1-Click Benchmark Presets */}
                <div className="mt-2.5 space-y-1.5">
                  <span className="text-[10px] text-zinc-500 font-mono uppercase tracking-wider block">
                    1-Click Real-World Repository Presets:
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {[
                      { name: 'expressjs/express', url: 'https://github.com/expressjs/express' },
                      { name: 'fastapi/fastapi', url: 'https://github.com/fastapi/fastapi' },
                      { name: 'pallets/flask', url: 'https://github.com/pallets/flask' },
                      { name: 'CodeArchaeologist (Self)', url: 'https://github.com/PanatiNitesh/CodeArchaeologist' }
                    ].map(preset => (
                      <button
                        key={preset.name}
                        type="button"
                        onClick={() => setInputUrl(preset.url)}
                        className="px-2 py-1 rounded bg-[#161722] hover:bg-[#202235] border border-zinc-800 hover:border-indigo-700 text-[10.5px] font-mono text-zinc-300 transition-colors flex items-center gap-1"
                      >
                        ⚡ {preset.name}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-[var(--border-hairline)]">
                <button
                  type="button"
                  onClick={() => setShowIngestModal(false)}
                  className="btn-studio btn-studio-secondary"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={ingestLoading}
                  className="btn-studio btn-studio-primary min-w-[140px]"
                >
                  {ingestLoading ? (ingestStatusText || 'Analyzing Pipeline...') : 'Run Archaeology Ingestion'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </header>
  );
};
