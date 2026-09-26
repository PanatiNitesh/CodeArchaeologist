import React, { useState } from 'react';
import { 
  FileCode, 
  History, 
  Flame, 
  GitCommit, 
  User, 
  Calendar, 
  Sparkles, 
  Code2, 
  ExternalLink,
  ChevronRight,
  Bug,
  Shield,
  Layers,
  ArrowUpRight
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
      <div className="studio-panel p-6 flex flex-col items-center justify-center h-full text-center text-zinc-500 bg-[#0e0f14]">
        <FileCode className="w-10 h-10 mb-3 text-zinc-700 stroke-[1.2]" />
        <h3 className="font-semibold text-zinc-300 text-xs mb-1 font-mono uppercase tracking-wider">
          No Component Selected
        </h3>
        <p className="text-[11px] max-w-xs text-zinc-500 leading-relaxed">
          Select any node in the topology graph or file in the explorer to inspect AST symbols, historical Git milestones, and cascading reach.
        </p>
      </div>
    );
  }

  const getRiskPill = (level: string = 'Low', score: number = 0) => {
    const l = level.toLowerCase();
    let cls = 'risk-pill-low';
    if (l === 'critical') cls = 'risk-pill-critical';
    else if (l === 'high') cls = 'risk-pill-high';
    else if (l === 'medium') cls = 'risk-pill-medium';

    return (
      <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold ${cls}`}>
        {level.toUpperCase()} IMPACT ({score}%)
      </span>
    );
  };

  return (
    <div className="studio-panel flex flex-col h-full bg-[#0e0f14]">
      {/* File Header Card */}
      <div className="p-3 border-b border-[var(--border-hairline)] bg-[#121318]">
        <div className="flex items-start justify-between gap-2 mb-2">
          <div className="min-w-0">
            <div className="flex items-center gap-1.5 flex-wrap">
              <span className="font-bold text-xs text-white truncate font-mono">
                {file.name}
              </span>
              <span className="badge-arch badge-service text-[9px]">{file.component_type}</span>
              <span 
                className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-zinc-800/80 text-zinc-400 border border-zinc-700/50"
                title="Probabilistic classification confidence score (classifier.py)"
              >
                {Math.round((file.component_confidence || 0.92) * 100)}% conf
              </span>
              {evolution?.hotspot_score && evolution.hotspot_score >= 4.0 ? (
                <span 
                  className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-rose-950 text-rose-300 border border-rose-800 flex items-center gap-1 font-semibold"
                  title={`Regression hotspot score: ${evolution.hotspot_score}/10 based on bug fixes and churn frequency`}
                >
                  🔥 Hotspot ({evolution.hotspot_score})
                </span>
              ) : evolution?.hotspot_score && evolution.hotspot_score >= 2.0 ? (
                <span 
                  className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-amber-950 text-amber-300 border border-amber-800 flex items-center gap-1"
                  title={`Watchlist score: ${evolution.hotspot_score}/10 based on bug fixes and revisions`}
                >
                  ⚠️ Watch ({evolution.hotspot_score})
                </span>
              ) : null}
            </div>
            <p className="text-[10px] text-zinc-500 font-mono truncate mt-0.5">{file.path}</p>
          </div>
          {blastRadius && getRiskPill(blastRadius.risk_level, blastRadius.risk_score)}
        </div>

        {/* Precision Segmented Control */}
        <div className="segmented-control w-full mt-2">
          <div
            onClick={() => setActiveTab('overview')}
            className={`segmented-item flex-1 text-center ${activeTab === 'overview' ? 'active' : ''}`}
          >
            Overview & AST
          </div>
          <div
            onClick={() => setActiveTab('history')}
            className={`segmented-item flex-1 text-center ${activeTab === 'history' ? 'active' : ''}`}
          >
            History ({evolution?.total_revisions ?? 0})
          </div>
          <div
            onClick={() => setActiveTab('blast')}
            className={`segmented-item flex-1 text-center ${activeTab === 'blast' ? 'active' : ''}`}
          >
            Reach ({blastRadius?.total_impact_count ?? 0})
          </div>
        </div>
      </div>

      {/* Tab Body */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {/* OVERVIEW TAB */}
        {activeTab === 'overview' && (
          <div className="space-y-3">
            {/* Metadata Stats Grid */}
            <div className="grid grid-cols-4 gap-2">
              <div className="p-2 rounded bg-[#13141a] border border-zinc-800 text-center">
                <span className="block text-[9px] font-mono text-zinc-500 uppercase">Lines</span>
                <span className="font-mono font-semibold text-xs text-zinc-200">{file.loc}</span>
              </div>
              <div className="p-2 rounded bg-[#13141a] border border-zinc-800 text-center">
                <span className="block text-[9px] font-mono text-zinc-500 uppercase">Functions</span>
                <span className="font-mono font-semibold text-xs text-indigo-400">{file.functions?.length ?? 0}</span>
              </div>
              <div className="p-2 rounded bg-[#13141a] border border-zinc-800 text-center">
                <span className="block text-[9px] font-mono text-zinc-500 uppercase">Classes</span>
                <span className="font-mono font-semibold text-xs text-emerald-400">{file.classes?.length ?? 0}</span>
              </div>
              <div className="p-2 rounded bg-[#13141a] border border-zinc-800 text-center">
                <span className="block text-[9px] font-mono text-zinc-500 uppercase">Churn</span>
                <span className={`font-mono font-semibold text-xs ${
                  (evolution?.total_churn || 0) > 600
                    ? 'text-rose-400'
                    : (evolution?.total_churn || 0) > 200
                    ? 'text-amber-400'
                    : 'text-zinc-200'
                }`}>
                  {evolution?.total_churn ?? 0}
                </span>
              </div>
            </div>

            {/* Extracted AST Functions */}
            {file.functions && file.functions.length > 0 && (
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-[10px] font-mono font-semibold uppercase tracking-wider text-zinc-400 flex items-center gap-1.5">
                    <Code2 className="w-3 h-3 text-indigo-400" />
                    Extracted Functions ({file.functions.length})
                  </span>
                </div>
                <div className="space-y-1.5">
                  {file.functions.map((fn, idx) => (
                    <div
                      key={idx}
                      className="p-2 rounded bg-[#13141a] border border-zinc-800/80 text-[11px]"
                    >
                      <div className="flex items-center justify-between font-mono">
                        <span className="font-semibold text-indigo-300 truncate">
                          {fn.name}<span className="text-zinc-500">({fn.params.join(', ')})</span>
                        </span>
                        <span className="text-[10px] text-zinc-600 shrink-0 pl-1">
                          L{fn.start_line}–{fn.end_line}
                        </span>
                      </div>
                      {fn.calls.length > 0 && (
                        <div className="mt-1 text-[10px] font-mono text-zinc-500 flex items-center gap-1">
                          <span>Calls:</span>
                          <span className="text-cyan-400">{fn.calls.slice(0, 3).join(', ')}</span>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* AI Architectural Inquiry Menu */}
            <div className="p-3 rounded-lg bg-[#131520] border border-indigo-900/50 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-mono font-semibold text-zinc-300 flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
                  Ask Archaeological Assistant
                </span>
                <span className="text-[9px] font-mono text-zinc-500">Grounded in AST + Commits</span>
              </div>

              <div className="grid grid-cols-2 gap-1.5 pt-1">
                <button
                  onClick={() => onAskAI(`Explain the architecture, design choices, and purpose of ${file.path}`)}
                  className="p-1.5 rounded bg-[#181a26] hover:bg-[#202234] border border-indigo-950 hover:border-indigo-800 text-[10px] text-zinc-300 text-left transition-colors font-mono flex items-center gap-1"
                  title="Explain architecture and design choices"
                >
                  🏛️ Architecture & Role
                </button>

                <button
                  onClick={() => onAskAI(`What could break across callers or APIs if I change ${file.path}?`)}
                  className="p-1.5 rounded bg-[#181a26] hover:bg-[#202234] border border-indigo-950 hover:border-indigo-800 text-[10px] text-zinc-300 text-left transition-colors font-mono flex items-center gap-1"
                  title="Simulate breaking changes and blast reach"
                >
                  💥 What Breaks if Changed?
                </button>

                <button
                  onClick={() => onAskAI(`Why was ${file.path} modified in past commits and what bug fixes touched it?`)}
                  className="p-1.5 rounded bg-[#181a26] hover:bg-[#202234] border border-indigo-950 hover:border-indigo-800 text-[10px] text-zinc-300 text-left transition-colors font-mono flex items-center gap-1"
                  title="Historical commit rationale and bug fix traces"
                >
                  📜 Bug Fix History
                </button>

                <button
                  onClick={() => onAskAI(`Which test suites and callers depend on ${file.name}?`)}
                  className="p-1.5 rounded bg-[#181a26] hover:bg-[#202234] border border-indigo-950 hover:border-indigo-800 text-[10px] text-zinc-300 text-left transition-colors font-mono flex items-center gap-1"
                  title="Identify downstream callers and required tests"
                >
                  🧪 Dependent Tests & Callers
                </button>
              </div>
            </div>
          </div>
        )}

        {/* HISTORY TAB */}
        {activeTab === 'history' && (
          <div className="space-y-3">
            {evolution ? (
              <>
                {/* Creation Lifecycle Card */}
                <div className="p-2.5 rounded bg-[#13141a] border border-zinc-800 text-[11px] font-mono space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="text-zinc-500">Origin Date:</span>
                    <span className="text-zinc-200">{evolution.created_date}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-zinc-500">Original Author:</span>
                    <span className="text-indigo-300">{evolution.created_by || 'Unknown'}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-zinc-500">Total Contributors:</span>
                    <span className="text-zinc-300">{evolution.total_authors} developers</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-zinc-500">Historical Churn:</span>
                    <span className="text-zinc-200">
                      {evolution.total_churn ?? 0} lines ({evolution.churn_per_revision ?? 0}/rev)
                    </span>
                  </div>
                  {evolution.hotspot_score !== undefined && evolution.hotspot_score > 0 && (
                    <div className="flex items-center justify-between">
                      <span className="text-zinc-500">Hotspot Risk:</span>
                      <span className={evolution.hotspot_score >= 4 ? 'text-rose-400 font-semibold' : 'text-amber-400'}>
                        {evolution.hotspot_score} / 10
                      </span>
                    </div>
                  )}
                </div>

                {/* Major Milestones */}
                <div>
                  <span className="text-[10px] font-mono font-semibold uppercase tracking-wider text-zinc-400 block mb-1.5">
                    Evolutionary Milestones
                  </span>
                  <div className="space-y-1.5">
                    {evolution.major_milestones.map((m, idx) => (
                      <div
                        key={idx}
                        className="p-2 rounded bg-[#13141a] border border-zinc-800 flex items-start gap-2 text-xs"
                      >
                        <span className="font-mono font-semibold text-indigo-400 shrink-0 text-[10px] pt-0.5">
                          {m.date}
                        </span>
                        <div className="flex-1 min-w-0">
                          <p className="text-zinc-200 text-[11px] leading-tight font-medium">{m.description}</p>
                          <span className="text-[10px] text-zinc-500 font-mono">
                            {m.hash} • {m.author}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Bug Fixes & Refactors */}
                {evolution.bug_fixes.length > 0 && (
                  <div>
                    <span className="text-[10px] font-mono font-semibold uppercase tracking-wider text-rose-400 block mb-1.5">
                      Historical Bug Fixes ({evolution.bug_fixes.length})
                    </span>
                    <div className="space-y-1">
                      {evolution.bug_fixes.map((bf, idx) => (
                        <div key={idx} className="p-1.5 rounded bg-rose-950/20 border border-rose-900/30 text-[11px] font-mono flex items-center gap-2">
                          <span className="text-rose-400 font-bold">{bf.short_hash}</span>
                          <span className="text-zinc-300 truncate font-sans">{bf.message}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            ) : (
              <p className="text-xs text-zinc-500 font-mono">Mining file evolution records...</p>
            )}
          </div>
        )}

        {/* BLAST REACH TAB */}
        {activeTab === 'blast' && (
          <div className="space-y-3">
            {blastRadius ? (
              <>
                <div className="p-2.5 rounded bg-[#13141a] border border-zinc-800">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[10px] font-mono text-zinc-400 uppercase font-semibold">Impact Assessment</span>
                    {getRiskPill(blastRadius.risk_level, blastRadius.risk_score)}
                  </div>
                  <p className="text-[11px] text-zinc-400 leading-relaxed">
                    {blastRadius.explanation}
                  </p>
                </div>

                {/* Direct Dependents */}
                <div>
                  <span className="text-[10px] font-mono font-semibold uppercase tracking-wider text-rose-400 flex items-center justify-between mb-1">
                    <span>Direct Dependents (1-Hop):</span>
                    <span>{blastRadius.direct_affected_files.length}</span>
                  </span>
                  <div className="space-y-1">
                    {blastRadius.direct_affected_files.length === 0 ? (
                      <div className="p-1.5 rounded bg-[#13141a] border border-zinc-800/50 text-[10px] font-mono text-zinc-600 italic">None</div>
                    ) : blastRadius.direct_affected_files.map((df, idx) => (
                      <div key={idx} className="p-1.5 rounded bg-[#13141a] border border-rose-900/30 text-[10px] font-mono text-zinc-300 truncate" title={df}>
                        {df}
                      </div>
                    ))}
                  </div>
                </div>

                {/* Indirect Dependents */}
                <div>
                  <span className="text-[10px] font-mono font-semibold uppercase tracking-wider text-amber-400 flex items-center justify-between mb-1">
                    <span>Indirect Dependents (2+ Hop):</span>
                    <span>{blastRadius.indirect_affected_files.length}</span>
                  </span>
                  <div className="space-y-1 max-h-24 overflow-y-auto">
                    {blastRadius.indirect_affected_files.length === 0 ? (
                      <div className="p-1.5 rounded bg-[#13141a] border border-zinc-800/50 text-[10px] font-mono text-zinc-600 italic">None</div>
                    ) : blastRadius.indirect_affected_files.map((df, idx) => (
                      <div key={idx} className="p-1.5 rounded bg-[#13141a] border border-amber-900/30 text-[10px] font-mono text-zinc-400 truncate" title={df}>
                        {df}
                      </div>
                    ))}
                  </div>
                </div>

                {/* Downstream APIs */}
                {blastRadius.affected_apis.length > 0 && (
                  <div>
                    <span className="text-[10px] font-mono font-semibold uppercase tracking-wider text-emerald-400 block mb-1">
                      Downstream API Endpoints ({blastRadius.affected_apis.length})
                    </span>
                    <div className="space-y-1">
                      {blastRadius.affected_apis.map((api, idx) => (
                        <div key={idx} className="p-1.5 rounded bg-emerald-950/20 border border-emerald-900/30 text-[10px] font-mono text-emerald-300 truncate">
                          {api}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Required Test Runs */}
                {blastRadius.affected_tests.length > 0 && (
                  <div>
                    <span className="text-[10px] font-mono font-semibold uppercase tracking-wider text-pink-400 block mb-1">
                      Candidate Regression Tests ({blastRadius.affected_tests.length})
                    </span>
                    <div className="space-y-1">
                      {blastRadius.affected_tests.map((test, idx) => (
                        <div key={idx} className="p-1.5 rounded bg-pink-950/20 border border-pink-900/30 text-[10px] font-mono text-pink-300 truncate">
                          {test}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <button
                  onClick={onOpenBlastModal}
                  className="w-full btn-studio btn-studio-primary text-xs py-1.5"
                >
                  <Flame className="w-3.5 h-3.5 text-amber-300" />
                  View Predictive Impact & Co-Changes
                </button>
              </>
            ) : (
              <p className="text-xs text-zinc-500 font-mono">Calculating cascading reach...</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
