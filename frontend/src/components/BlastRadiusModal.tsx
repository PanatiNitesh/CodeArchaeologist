import React from 'react';
import { 
  Flame, 
  ShieldAlert, 
  GitPullRequest, 
  Cpu, 
  ArrowRight, 
  CheckCircle2, 
  AlertTriangle,
  X
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
    <div className="fixed inset-0 bg-black/80 backdrop-blur-md flex items-center justify-center z-50 p-4">
      <div className="glass-panel w-full max-w-4xl max-h-[90vh] flex flex-col bg-slate-950/95 border border-indigo-500/40">
        {/* Header */}
        <div className="p-4 border-b border-subtle flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-rose-500/20 border border-rose-500/40 flex items-center justify-center text-rose-400">
              <Flame className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-bold text-white text-sm">
                  Cascading Blast Radius & ML Change-Impact Predictor
                </h3>
                <span className="badge risk-critical text-[10px]">
                  {blastRadius.risk_level.toUpperCase()} ({blastRadius.risk_score}%)
                </span>
              </div>
              <p className="text-xs font-mono text-slate-400 truncate">
                Target: {blastRadius.target_file}
              </p>
            </div>
          </div>

          <button onClick={onClose} className="text-slate-400 hover:text-white p-1">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Executive Summary Card */}
          <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
              Impact Assessment Summary
            </h4>
            <p className="text-xs text-slate-300 leading-relaxed">
              {blastRadius.explanation}
            </p>

            <div className="grid grid-cols-4 gap-3 mt-4">
              <div className="p-3 rounded-lg bg-slate-950/70 border border-slate-800 text-center">
                <span className="block text-[10px] text-slate-400 uppercase font-semibold">Direct Impact</span>
                <span className="text-lg font-bold font-mono text-rose-400">{blastRadius.direct_affected_files.length}</span>
                <span className="block text-[9px] text-slate-500">1-Hop dependents</span>
              </div>
              <div className="p-3 rounded-lg bg-slate-950/70 border border-slate-800 text-center">
                <span className="block text-[10px] text-slate-400 uppercase font-semibold">Indirect Impact</span>
                <span className="text-lg font-bold font-mono text-amber-400">{blastRadius.indirect_affected_files.length}</span>
                <span className="block text-[9px] text-slate-500">Transitive files</span>
              </div>
              <div className="p-3 rounded-lg bg-slate-950/70 border border-slate-800 text-center">
                <span className="block text-[10px] text-slate-400 uppercase font-semibold">Affected APIs</span>
                <span className="text-lg font-bold font-mono text-emerald-400">{blastRadius.affected_apis.length}</span>
                <span className="block text-[9px] text-slate-500">Endpoints</span>
              </div>
              <div className="p-3 rounded-lg bg-slate-950/70 border border-slate-800 text-center">
                <span className="block text-[10px] text-slate-400 uppercase font-semibold">Affected Tests</span>
                <span className="text-lg font-bold font-mono text-pink-400">{blastRadius.affected_tests.length}</span>
                <span className="block text-[9px] text-slate-500">Suites to run</span>
              </div>
            </div>
          </div>

          {/* ML Change-Impact Prediction Rankings */}
          {predictions && (
            <div>
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Cpu className="w-4 h-4 text-cyan-400" />
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-200">
                    ML Change-Impact Probability Rankings ({predictions.model_name})
                  </h4>
                </div>
                <span className="text-[11px] text-slate-400 font-mono">
                  Calibrated by Historical Co-Changes + Graph Topology
                </span>
              </div>

              <div className="space-y-2">
                {predictions.predicted_files.map((item, idx) => (
                  <div
                    key={idx}
                    className="p-3 rounded-lg bg-slate-900/60 border border-slate-800 flex items-center justify-between text-xs"
                  >
                    <div className="space-y-1">
                      <div className="flex items-center gap-2 font-mono font-medium text-slate-200">
                        <span>{item.file_path}</span>
                        <span className="badge badge-service text-[9px]">{item.component_type}</span>
                      </div>
                      <p className="text-[11px] text-slate-400">
                        {item.reason}
                      </p>
                    </div>

                    <div className="text-right shrink-0 pl-4">
                      <div className="flex items-center gap-2 justify-end">
                        <div className="w-24 bg-slate-800 rounded-full h-2 overflow-hidden">
                          <div
                            className={`h-full rounded-full ${
                              item.probability >= 0.75
                                ? 'bg-rose-500'
                                : item.probability >= 0.5
                                ? 'bg-amber-500'
                                : 'bg-cyan-500'
                            }`}
                            style={{ width: `${Math.round(item.probability * 100)}%` }}
                          />
                        </div>
                        <span className="font-mono font-bold text-sm text-cyan-300 w-10 text-right">
                          {Math.round(item.probability * 100)}%
                        </span>
                      </div>
                      <span className="text-[10px] text-slate-500 font-mono">
                        dist: {item.graph_distance} • co-changes: {item.co_change_count}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Breakdown Lists */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <h5 className="text-xs font-bold text-slate-300 mb-2">Direct Dependents</h5>
              <div className="space-y-1 max-h-40 overflow-y-auto">
                {blastRadius.direct_affected_files.map((f, i) => (
                  <div key={i} className="p-1.5 rounded bg-slate-900 border border-slate-800/80 text-[11px] font-mono text-slate-300">
                    {f}
                  </div>
                ))}
              </div>
            </div>

            <div>
              <h5 className="text-xs font-bold text-slate-300 mb-2">Transitive Indirect Dependents</h5>
              <div className="space-y-1 max-h-40 overflow-y-auto">
                {blastRadius.indirect_affected_files.map((f, i) => (
                  <div key={i} className="p-1.5 rounded bg-slate-900 border border-slate-800/80 text-[11px] font-mono text-slate-400">
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
