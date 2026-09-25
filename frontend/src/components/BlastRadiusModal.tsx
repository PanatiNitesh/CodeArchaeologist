import React from 'react';
import { 
  Flame, 
  Cpu, 
  X,
  Layers,
  ArrowRight,
  ShieldAlert,
  GitCommit
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
                <div className="mb-2.5 p-2 rounded bg-[#101118] border border-zinc-800/60 flex flex-wrap items-center gap-1.5 text-[10px] font-mono">
                  <span className="text-zinc-500 font-semibold mr-1">Empirical Model Weights:</span>
                  {Object.entries(predictions.feature_importance).map(([feature, weight]) => (
                    <span key={feature} className="px-1.5 py-0.5 rounded bg-zinc-800/80 border border-zinc-700/50 text-zinc-300">
                      {feature.replace(/_/g, ' ')}: <strong className="text-indigo-400">{(weight * 100).toFixed(0)}%</strong>
                    </span>
                  ))}
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

          {/* Breakdown Lists */}
          <div className="grid grid-cols-2 gap-3 font-mono">
            <div>
              <span className="text-[10px] uppercase font-semibold text-zinc-400 block mb-1">
                Direct Consumers (1-Hop)
              </span>
              <div className="space-y-1 max-h-36 overflow-y-auto">
                {blastRadius.direct_affected_files.map((f, i) => (
                  <div key={i} className="p-1.5 rounded bg-[#101116] border border-zinc-800 text-[10px] text-zinc-300 truncate">
                    {f}
                  </div>
                ))}
              </div>
            </div>

            <div>
              <span className="text-[10px] uppercase font-semibold text-zinc-400 block mb-1">
                Transitive Downstream Components
              </span>
              <div className="space-y-1 max-h-36 overflow-y-auto">
                {blastRadius.indirect_affected_files.map((f, i) => (
                  <div key={i} className="p-1.5 rounded bg-[#101116] border border-zinc-800 text-[10px] text-zinc-400 truncate">
                    {f}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
