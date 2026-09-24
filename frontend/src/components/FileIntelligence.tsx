import React, { useState } from 'react';
import { 
  FileCode, 
  History, 
  ShieldAlert, 
  Flame, 
  GitBranch, 
  User, 
  Calendar, 
  Sparkles, 
  Code2, 
  ExternalLink,
  ChevronRight,
  CheckCircle,
  Bug,
  Cpu
} from 'lucide-react';
import { FileItem, FileEvolution, BlastRadiusResult, ChangeImpactPrediction } from '../api/client';

interface FileIntelligenceProps {
  file: FileItem | null;
  evolution: FileEvolution | null;
  blastRadius: BlastRadiusResult | null;
  predictions: ChangeImpactPrediction | null;
  onAskAI: (prompt: string) => void;
  onOpenBlastModal: () => void;
}

export const FileIntelligence: React.FC<FileIntelligenceProps> = ({
  file,
  evolution,
  blastRadius,
  predictions,
  onAskAI,
  onOpenBlastModal
}) => {
  const [activeTab, setActiveTab] = useState<'overview' | 'history' | 'blast'>('overview');

  if (!file) {
    return (
      <div className="glass-panel p-6 flex flex-col items-center justify-center h-full text-center text-slate-500">
        <FileCode className="w-12 h-12 mb-3 text-slate-700" />
        <h3 className="font-semibold text-slate-300 text-sm mb-1">No File Selected</h3>
        <p className="text-xs max-w-xs text-slate-500">
          Click any file in the File Tree or node in the Architecture Graph to reveal its archaeological history, AST symbols, and change blast radius.
        </p>
      </div>
    );
  }

  const getRiskBadge = (level: string = 'Low', score: number = 0) => {
    const l = level.toLowerCase();
    let badgeClass = 'risk-low';
    if (l === 'critical') badgeClass = 'risk-critical';
    else if (l === 'high') badgeClass = 'risk-high';
    else if (l === 'medium') badgeClass = 'risk-medium';

    return (
      <span className={`badge ${badgeClass} text-[10px] py-1 px-2.5 font-bold`}>
        {level.toUpperCase()} RISK ({score}%)
      </span>
    );
  };

  return (
    <div className="glass-panel flex flex-col h-full overflow-hidden border border-subtle">
      {/* File Header */}
      <div className="p-4 border-b border-subtle bg-slate-950/50">
        <div className="flex items-start justify-between gap-2 mb-2">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h2 className="font-bold text-sm text-white truncate font-mono">
                {file.name}
              </h2>
              <span className="badge badge-service text-[9px]">{file.component_type}</span>
            </div>
            <p className="text-[11px] text-slate-500 font-mono truncate">{file.path}</p>
          </div>
          {blastRadius && getRiskBadge(blastRadius.risk_level, blastRadius.risk_score)}
        </div>

        {/* Tab Navigation */}
        <div className="flex items-center gap-2 pt-2 border-t border-slate-800/80">
          <button
            onClick={() => setActiveTab('overview')}
            className={`px-3 py-1 rounded text-xs font-semibold transition-all ${
              activeTab === 'overview'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Overview & AST
          </button>
          <button
            onClick={() => setActiveTab('history')}
            className={`px-3 py-1 rounded text-xs font-semibold transition-all ${
              activeTab === 'history'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Evolution History ({evolution?.total_revisions ?? 0})
          </button>
          <button
            onClick={() => setActiveTab('blast')}
            className={`px-3 py-1 rounded text-xs font-semibold transition-all ${
              activeTab === 'blast'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Blast Radius ({blastRadius?.total_impact_count ?? 0})
          </button>
        </div>
      </div>

      {/* Tab Contents */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* OVERVIEW TAB */}
        {activeTab === 'overview' && (
          <div className="space-y-4">
            {/* Quick Stats Grid */}
            <div className="grid grid-cols-3 gap-2">
              <div className="p-2.5 rounded-lg bg-slate-900/80 border border-slate-800 text-center">
                <span className="block text-[10px] text-slate-400">Lines of Code</span>
                <span className="font-mono font-bold text-sm text-cyan-400">{file.loc}</span>
              </div>
              <div className="p-2.5 rounded-lg bg-slate-900/80 border border-slate-800 text-center">
                <span className="block text-[10px] text-slate-400">Functions</span>
                <span className="font-mono font-bold text-sm text-indigo-400">{file.functions?.length ?? 0}</span>
              </div>
              <div className="p-2.5 rounded-lg bg-slate-900/80 border border-slate-800 text-center">
                <span className="block text-[10px] text-slate-400">Classes</span>
                <span className="font-mono font-bold text-sm text-emerald-400">{file.classes?.length ?? 0}</span>
              </div>
            </div>

            {/* Extracted AST Functions */}
            {file.functions && file.functions.length > 0 && (
              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2 flex items-center gap-1.5">
                  <Code2 className="w-3.5 h-3.5 text-indigo-400" />
                  Extracted Functions & Methods
                </h4>
                <div className="space-y-1.5">
                  {file.functions.map((fn, idx) => (
                    <div
                      key={idx}
                      className="p-2 rounded bg-slate-900/60 border border-slate-800/80 text-xs"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-mono font-semibold text-indigo-300">
                          {fn.name}({fn.params.join(', ')})
                        </span>
                        <span className="font-mono text-[10px] text-slate-500">
                          L{fn.start_line}-L{fn.end_line}
                        </span>
                      </div>
                      {fn.calls.length > 0 && (
                        <div className="mt-1 text-[11px] text-slate-400 flex items-center gap-1">
                          <span className="text-slate-500 font-mono">Calls:</span>
                          <span className="font-mono text-cyan-400">{fn.calls.slice(0, 3).join(', ')}</span>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* AI Prompt Button */}
            <div className="p-3 rounded-lg bg-indigo-950/40 border border-indigo-500/30 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-indigo-400" />
                <span className="text-xs font-medium text-indigo-200">
                  Ask AI to explain {file.name}
                </span>
              </div>
              <button
                onClick={() => onAskAI(`Explain the purpose, architecture, and historical evolution of ${file.path}`)}
                className="btn-primary text-xs py-1 px-2.5"
              >
                Explain Component
              </button>
            </div>
          </div>
        )}

        {/* HISTORY TAB */}
        {activeTab === 'history' && (
          <div className="space-y-4">
            {evolution ? (
              <>
                {/* Creation Metadata */}
                <div className="p-3 rounded-lg bg-slate-900/90 border border-slate-800 space-y-1.5">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-400 flex items-center gap-1">
                      <Calendar className="w-3.5 h-3.5 text-slate-400" /> Created Date:
                    </span>
                    <span className="font-mono font-bold text-slate-200">{evolution.created_date}</span>
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-400 flex items-center gap-1">
                      <User className="w-3.5 h-3.5 text-slate-400" /> Original Author:
                    </span>
                    <span className="font-medium text-indigo-300">{evolution.created_by || 'Unknown'}</span>
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-400">Total Contributors:</span>
                    <span className="font-mono text-slate-300">{evolution.total_authors} developers</span>
                  </div>
                </div>

                {/* Major Milestones */}
                <div>
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
                    Major Architectural Milestones
                  </h4>
                  <div className="space-y-2">
                    {evolution.major_milestones.map((m, idx) => (
                      <div
                        key={idx}
                        className="p-2.5 rounded bg-slate-900/60 border border-slate-800 text-xs flex items-start gap-2"
                      >
                        <span className="font-mono font-bold text-indigo-400 shrink-0 text-[11px]">
                          {m.date}
                        </span>
                        <div className="flex-1 min-w-0">
                          <p className="text-slate-200 font-medium">{m.description}</p>
                          <span className="text-[10px] text-slate-500 font-mono">
                            {m.hash} • by {m.author}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Bug Fixes & Refactors */}
                {evolution.bug_fixes.length > 0 && (
                  <div>
                    <h4 className="text-xs font-bold uppercase tracking-wider text-rose-400 mb-2 flex items-center gap-1">
                      <Bug className="w-3.5 h-3.5" /> Historical Bug Fixes ({evolution.bug_fixes.length})
                    </h4>
                    <div className="space-y-1.5">
                      {evolution.bug_fixes.map((bf, idx) => (
                        <div key={idx} className="p-2 rounded bg-rose-950/20 border border-rose-500/20 text-xs">
                          <div className="flex items-center gap-2">
                            <span className="font-mono text-rose-300 font-bold">{bf.short_hash}</span>
                            <span className="text-slate-300">{bf.message}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            ) : (
              <p className="text-xs text-slate-500">Mining file evolution records...</p>
            )}
          </div>
        )}

        {/* BLAST RADIUS TAB */}
        {activeTab === 'blast' && (
          <div className="space-y-4">
            {blastRadius ? (
              <>
                <div className="p-3 rounded-lg bg-slate-900/90 border border-slate-800">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-bold text-slate-300">Composite Blast Impact:</span>
                    {getRiskBadge(blastRadius.risk_level, blastRadius.risk_score)}
                  </div>
                  <p className="text-xs text-slate-400 leading-relaxed">
                    {blastRadius.explanation}
                  </p>
                </div>

                {/* Direct Dependents */}
                <div>
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-300 mb-2 flex items-center justify-between">
                    <span>Direct Dependents (1-Hop):</span>
                    <span className="text-rose-400 font-mono">{blastRadius.direct_affected_files.length}</span>
                  </h4>
                  <div className="space-y-1">
                    {blastRadius.direct_affected_files.map((df, idx) => (
                      <div key={idx} className="p-1.5 rounded bg-slate-900/60 border border-slate-800 text-xs font-mono text-slate-300">
                        {df}
                      </div>
                    ))}
                  </div>
                </div>

                {/* Affected APIs */}
                {blastRadius.affected_apis.length > 0 && (
                  <div>
                    <h4 className="text-xs font-bold uppercase tracking-wider text-emerald-400 mb-2">
                      Potentially Affected APIs ({blastRadius.affected_apis.length})
                    </h4>
                    <div className="space-y-1">
                      {blastRadius.affected_apis.map((api, idx) => (
                        <div key={idx} className="p-1.5 rounded bg-emerald-950/20 border border-emerald-500/20 text-xs font-mono text-emerald-300">
                          {api}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Affected Tests */}
                {blastRadius.affected_tests.length > 0 && (
                  <div>
                    <h4 className="text-xs font-bold uppercase tracking-wider text-pink-400 mb-2">
                      Required Test Validations ({blastRadius.affected_tests.length})
                    </h4>
                    <div className="space-y-1">
                      {blastRadius.affected_tests.map((test, idx) => (
                        <div key={idx} className="p-1.5 rounded bg-pink-950/20 border border-pink-500/20 text-xs font-mono text-pink-300">
                          {test}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <button
                  onClick={onOpenBlastModal}
                  className="w-full btn-primary text-xs justify-center py-2"
                >
                  <Flame className="w-3.5 h-3.5 text-amber-300" />
                  View Full ML Change-Impact Predictions
                </button>
              </>
            ) : (
              <p className="text-xs text-slate-500">Calculating blast radius propagation...</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
