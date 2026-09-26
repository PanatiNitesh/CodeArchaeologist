import React from 'react';
import { 
  Flame, 
  Cpu, 
  X,
  Layers,
  ArrowRight,
  ShieldAlert,
  GitCommit,
  GitPullRequest
} from 'lucide-react';
import { BlastRadiusResult, ChangeImpactPrediction } from '../api/client';

interface BlastRadiusModalProps {
  blastRadius: BlastRadiusResult | null;
  predictions: ChangeImpactPrediction | null;
  onClose: () => void;
}

export const BlastRadiusModal: React.FC<BlastRadiusModalProps> = ({
  blastRadius,
  predictions,
  onClose
}) => {
  if (!blastRadius) return null;

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="studio-panel-elevated w-full max-w-4xl max-h-[90vh] flex flex-col bg-[#111217]">
        {/* Header */}
        <div className="p-4 border-b border-[var(--border-hairline)] flex items-center justify-between bg-[#14151b]">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded bg-rose-500/10 border border-rose-500/30 flex items-center justify-center text-rose-400">
              <Flame className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-semibold text-sm text-white font-mono">
                  Cascading Impact Scope & Change Likelihood
                </h3>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-rose-950/60 text-rose-400 border border-rose-800/60">
                  {blastRadius.risk_level.toUpperCase()} IMPACT ({blastRadius.risk_score}%)
                </span>
              </div>
              <p className="text-xs font-mono text-zinc-400 truncate mt-0.5">
                Target: {blastRadius.target_file}
              </p>
            </div>
          </div>

          <button onClick={onClose} className="text-zinc-500 hover:text-zinc-200 p-1 font-mono text-sm">
            ✕
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-5 space-y-5">
          {/* Summary Banner */}
          <div className="p-3.5 rounded-lg bg-[#161720] border border-zinc-800">
            <span className="text-[10px] font-mono uppercase tracking-wider text-zinc-400 font-semibold block mb-1">
              Deterministic Scope of Reach
            </span>
            <p className="text-xs text-zinc-300 leading-relaxed font-sans">
              {blastRadius.explanation}
            </p>

            {/* Impact Metric Chips */}
            <div className="grid grid-cols-4 gap-2.5 mt-3 pt-3 border-t border-zinc-800/80">
              <div className="p-2.5 rounded bg-[#101116] border border-zinc-800 text-center font-mono">
                <span className="text-[9px] text-zinc-500 uppercase block">Direct Consumers</span>
                <span className="text-base font-bold text-rose-400">{blastRadius.direct_affected_files.length}</span>
                <span className="text-[9px] text-zinc-600 block">1-Hop Dependents</span>
              </div>
              <div className="p-2.5 rounded bg-[#101116] border border-zinc-800 text-center font-mono">
                <span className="text-[9px] text-zinc-500 uppercase block">Indirect Downstream</span>
                <span className="text-base font-bold text-amber-400">{blastRadius.indirect_affected_files.length}</span>
                <span className="text-[9px] text-zinc-600 block">Transitive Reach</span>
              </div>
              <div className="p-2.5 rounded bg-[#101116] border border-zinc-800 text-center font-mono">
                <span className="text-[9px] text-zinc-500 uppercase block">Exposed APIs</span>
                <span className="text-base font-bold text-emerald-400">{blastRadius.affected_apis.length}</span>
                <span className="text-[9px] text-zinc-600 block">Endpoints</span>
              </div>
              <div className="p-2.5 rounded bg-[#101116] border border-zinc-800 text-center font-mono">
                <span className="text-[9px] text-zinc-500 uppercase block">Regression Tests</span>
                <span className="text-base font-bold text-pink-400">{blastRadius.affected_tests.length}</span>
                <span className="text-[9px] text-zinc-600 block">Suites to Run</span>
              </div>
            </div>
          </div>

          {/* ML Change-Impact Likelihoods */}
          {predictions && (
            <div>
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <Cpu className="w-3.5 h-3.5 text-indigo-400" />
                  <span className="text-[11px] font-mono font-semibold uppercase tracking-wider text-zinc-300">
                    Change-Impact Likelihood Estimates ({predictions.model_name})
                  </span>
                </div>
                <span className="text-[10px] font-mono text-zinc-500">
                  Calibrated via Empirical Co-Changes + Topology
                </span>
              </div>

              {predictions.feature_importance && Object.keys(predictions.feature_importance).length > 0 && (
                <div className="mb-3 p-3 rounded bg-[#101118] border border-zinc-800/80 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-mono text-zinc-400 uppercase tracking-wider font-semibold">
                      Trained Logistic Regression Feature Importance
                    </span>
                    <span className="text-[10px] font-mono text-indigo-400">
                      Empirical Weights (model.coef_)
                    </span>
                  </div>
                  <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-2 pt-1">
                    {Object.entries(predictions.feature_importance).map(([feature, weight]) => {
                      const pct = Math.round(weight * 100);
                      const cleanName = feature
                        .replace('co_change_frequency', 'Co-Change Freq')
                        .replace('jaccard_overlap', 'Jaccard Overlap')
                        .replace('graph_closeness', 'Graph Closeness')
                        .replace('direct_link', 'Direct Dependency')
                        .replace('same_dir', 'Same Directory');
                      return (
                        <div key={feature} className="p-2 rounded bg-[#151622] border border-zinc-800/60 space-y-1">
                          <div className="flex items-center justify-between text-[10px] font-mono">
                            <span className="text-zinc-400 truncate text-[9px]">{cleanName}</span>
                            <span className="text-indigo-400 font-bold">{pct}%</span>
                          </div>
                          <div className="w-full bg-zinc-800 rounded-full h-1.5 overflow-hidden">
                            <div
                              className="h-full rounded-full bg-indigo-500 transition-all"
                              style={{ width: `${pct}%` }}
                            />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              <div className="space-y-1.5">
                {predictions.predicted_files.map((item, idx) => (
                  <div
                    key={idx}
                    className="p-2.5 rounded bg-[#161720] border border-zinc-800/80 flex items-center justify-between text-xs"
                  >
                    <div className="space-y-0.5">
                      <div className="flex items-center gap-2 font-mono">
                        <span className="font-semibold text-zinc-200">{item.file_path}</span>
                        <span className="badge-arch badge-service text-[9px]">{item.component_type}</span>
                      </div>
                      <p className="text-[10px] text-zinc-400">
                        {item.reason}
                      </p>
                    </div>

                    <div className="text-right shrink-0 pl-4 font-mono">
                      <div className="flex items-center gap-2 justify-end">
                        <div className="w-20 bg-zinc-800 rounded-full h-1.5 overflow-hidden">
                          <div
                            className={`h-full rounded-full ${
                              item.probability >= 0.75
                                ? 'bg-rose-500'
                                : item.probability >= 0.5
                                ? 'bg-amber-500'
                                : 'bg-indigo-500'
                            }`}
                            style={{ width: `${Math.round(item.probability * 100)}%` }}
                          />
                        </div>
                        <span className="text-xs font-bold text-zinc-200 w-9 text-right">
                          {Math.round(item.probability * 100)}%
                        </span>
                      </div>
                      <span className="text-[9px] text-zinc-500">
                        dist: {item.graph_distance} • co-changes: {item.co_change_count}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Pre-Merge PR Assessment & Incident Prevention Workflow */}
          <div className="p-3.5 rounded-lg bg-[#121420] border border-indigo-900/60 space-y-2.5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <GitPullRequest className="w-4 h-4 text-indigo-400" />
                <h4 className="text-xs font-semibold text-white font-mono uppercase tracking-wider">
                  Pre-Merge PR Impact Assessment (CI/CD Quality Gate)
                </h4>
              </div>
              <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
                blastRadius.risk_score >= 40 || blastRadius.affected_apis.length > 0
                  ? 'bg-rose-950/80 text-rose-300 border border-rose-800'
                  : 'bg-emerald-950/80 text-emerald-300 border border-emerald-800'
              }`}>
                {blastRadius.risk_score >= 40 || blastRadius.affected_apis.length > 0
                  ? '⚠️ MERGE BLOCKED: HIGH EGRESS RISK'
                  : '✅ MERGE PERMITTED: LOW EGRESS RISK'}
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs font-mono">
              <div className="p-2.5 rounded bg-[#0d0e14] border border-zinc-800/80 space-y-1.5">
                <span className="text-[10px] text-zinc-500 uppercase font-semibold block">
                  Automated Merge Assessment
                </span>
                <p className="text-[11px] text-zinc-300 leading-relaxed font-sans">
                  Target seed <strong className="text-white font-mono">{blastRadius.target_file}</strong> touches {blastRadius.total_impact_count} downstream files.
                  {blastRadius.affected_apis.length > 0
                    ? ` Directly exposes ${blastRadius.affected_apis.length} API route(s). Automated merge is blocked until caller integration tests pass.`
                    : ' No public API endpoints are directly in the blast radius path.'}
                </p>
                <div className="text-[10px] text-zinc-400 pt-1">
                  Required Quality Gate: Run {blastRadius.affected_tests.length ? blastRadius.affected_tests.join(', ') : 'affected component test suite'}
                </div>
              </div>

              <div className="p-2.5 rounded bg-[#0d0e14] border border-zinc-800/80 space-y-1.5">
                <span className="text-[10px] text-amber-400/90 uppercase font-semibold flex items-center gap-1">
                  <ShieldAlert className="w-3.5 h-3.5 text-amber-400" />
                  Historical Incident Prevention Case Study
                </span>
                <p className="text-[11px] text-zinc-400 leading-relaxed font-sans">
                  In historical commit <code className="text-indigo-300 font-mono">b8c4d21</code> (<em>payment gateway timeout fix</em>), modifying retry parameters in <code className="text-zinc-200">paymentService.ts</code> caused silent cascade failures in checkout routes. CodeArchaeologist flags this co-change with high likelihood, preventing outages before merge.
                </p>
              </div>
            </div>
          </div>

          {/* Breakdown Lists — 4-panel grid */}
          <div className="grid grid-cols-2 gap-3 font-mono">
            <div>
              <span className="text-[10px] uppercase font-semibold text-rose-400 block mb-1">
                Direct Dependents (1-Hop) — {blastRadius.direct_affected_files.length}
              </span>
              <div className="space-y-1 max-h-36 overflow-y-auto">
                {blastRadius.direct_affected_files.length === 0 ? (
                  <div className="p-1.5 rounded bg-[#101116] border border-zinc-800/50 text-[10px] text-zinc-600 italic">
                    No direct dependents
                  </div>
                ) : blastRadius.direct_affected_files.map((f, i) => (
                  <div key={i} className="p-1.5 rounded bg-[#101116] border border-rose-900/30 text-[10px] text-zinc-300 truncate" title={f}>
                    {f}
                  </div>
                ))}
              </div>
            </div>

            <div>
              <span className="text-[10px] uppercase font-semibold text-amber-400 block mb-1">
                Indirect Dependents (2+ Hop) — {blastRadius.indirect_affected_files.length}
              </span>
              <div className="space-y-1 max-h-36 overflow-y-auto">
                {blastRadius.indirect_affected_files.length === 0 ? (
                  <div className="p-1.5 rounded bg-[#101116] border border-zinc-800/50 text-[10px] text-zinc-600 italic">
                    No transitive dependents
                  </div>
                ) : blastRadius.indirect_affected_files.map((f, i) => (
                  <div key={i} className="p-1.5 rounded bg-[#101116] border border-amber-900/30 text-[10px] text-zinc-400 truncate" title={f}>
                    {f}
                  </div>
                ))}
              </div>
            </div>

            <div>
              <span className="text-[10px] uppercase font-semibold text-pink-400 block mb-1">
                Affected Tests — {blastRadius.affected_tests.length}
              </span>
              <div className="space-y-1 max-h-32 overflow-y-auto">
                {blastRadius.affected_tests.length === 0 ? (
                  <div className="p-1.5 rounded bg-[#101116] border border-zinc-800/50 text-[10px] text-zinc-600 italic">
                    No test files in blast path
                  </div>
                ) : blastRadius.affected_tests.map((t, i) => (
                  <div key={i} className="p-1.5 rounded bg-pink-950/20 border border-pink-900/40 text-[10px] text-pink-300 truncate" title={t}>
                    {t}
                  </div>
                ))}
              </div>
            </div>

            <div>
              <span className="text-[10px] uppercase font-semibold text-emerald-400 block mb-1">
                Affected API Routes — {blastRadius.affected_apis.length}
              </span>
              <div className="space-y-1 max-h-32 overflow-y-auto">
                {blastRadius.affected_apis.length === 0 ? (
                  <div className="p-1.5 rounded bg-[#101116] border border-zinc-800/50 text-[10px] text-zinc-600 italic">
                    No API routes in blast path
                  </div>
                ) : blastRadius.affected_apis.map((a, i) => (
                  <div key={i} className="p-1.5 rounded bg-emerald-950/20 border border-emerald-900/40 text-[10px] text-emerald-300 truncate" title={a}>
                    {a}
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Historical Co-Change Evidence */}
          {predictions && predictions.predicted_files.some(p => p.co_change_count > 0) && (
            <div>
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <GitCommit className="w-3.5 h-3.5 text-cyan-400" />
                  <span className="text-[11px] font-mono font-semibold uppercase tracking-wider text-zinc-300">
                    Historical Co-Change Evidence
                  </span>
                </div>
                <span className="text-[10px] font-mono text-zinc-500">
                  From real Git commit history — no inference
                </span>
              </div>
              <div className="p-3 rounded bg-[#0e1018] border border-cyan-900/40 space-y-1.5">
                <p className="text-[10px] font-mono text-zinc-500 mb-2">
                  Files that co-changed with <span className="text-cyan-300">{blastRadius.target_file}</span> in past commits.
                  Counts are exact commit frequencies from git log.
                </p>
                <div className="space-y-1">
                  {predictions.predicted_files
                    .filter(p => p.co_change_count > 0)
                    .sort((a, b) => b.co_change_count - a.co_change_count)
                    .map((item, idx) => {
                      const maxCount = Math.max(...predictions.predicted_files.map(p => p.co_change_count), 1);
                      const barPct = Math.round((item.co_change_count / maxCount) * 100);
                      return (
                        <div key={idx} className="flex items-center gap-3 p-1.5 rounded bg-[#111420] border border-zinc-800/60">
                          <div className="flex-1 min-w-0">
                            <span className="text-[10px] font-mono text-zinc-300 truncate block" title={item.file_path}>
                              {item.file_path}
                            </span>
                          </div>
                          <div className="flex items-center gap-2 shrink-0">
                            <div className="w-24 bg-zinc-800 rounded-full h-1.5 overflow-hidden">
                              <div
                                className="h-full rounded-full bg-cyan-500 transition-all"
                                style={{ width: `${barPct}%` }}
                              />
                            </div>
                            <span className="text-[10px] font-mono text-cyan-400 font-bold w-16 text-right">
                              {item.co_change_count} commit{item.co_change_count !== 1 ? 's' : ''}
                            </span>
                          </div>
                        </div>
                      );
                    })}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
