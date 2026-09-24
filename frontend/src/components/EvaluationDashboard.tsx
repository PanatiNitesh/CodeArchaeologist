import React from 'react';
import { 
  BarChart3, 
  CheckCircle2, 
  Layers, 
  Flame, 
  GitCommit, 
  Award,
  X,
  TrendingUp,
  ShieldCheck
} from 'lucide-react';
import { OverallEvaluation } from '../api/client';

interface EvaluationDashboardProps {
  evaluation: OverallEvaluation | null;
  onClose: () => void;
}

export const EvaluationDashboard: React.FC<EvaluationDashboardProps> = ({
  evaluation,
  onClose
}) => {
  if (!evaluation) return null;

  const { architecture_eval, blast_radius_eval, commit_count_evaluated, summary } = evaluation;

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-md flex items-center justify-center z-50 p-4">
      <div className="glass-panel w-full max-w-3xl max-h-[90vh] flex flex-col bg-slate-950/95 border border-indigo-500/40">
        {/* Header */}
        <div className="p-4 border-b border-subtle flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center text-emerald-400">
              <Award className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-bold text-white text-sm">
                  Phase 7 Empirical Evaluation & Benchmarks
                </h3>
                <span className="badge badge-controller text-[10px]">Verified Metrics</span>
              </div>
              <p className="text-xs text-slate-400">
                Scientific validation of Architecture Discovery & Historical Blast Radius Prediction
              </p>
            </div>
          </div>

          <button onClick={onClose} className="text-slate-400 hover:text-white p-1">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Summary Box */}
          <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-1">
              Benchmark Conclusion
            </h4>
            <p className="text-xs text-slate-300 leading-relaxed font-mono">
              {summary}
            </p>
          </div>

          {/* Metric Comparison Cards */}
          <div className="grid grid-cols-2 gap-4">
            {/* Step 17: Architecture Evaluation */}
            <div className="p-4 rounded-xl bg-slate-900/60 border border-indigo-500/30 space-y-3">
              <div className="flex items-center gap-2">
                <Layers className="w-4 h-4 text-indigo-400" />
                <h4 className="font-bold text-xs text-white">
                  Step 17: Architecture Graph Evaluation
                </h4>
              </div>
              <p className="text-[11px] text-slate-400">
                Predicted module dependencies vs actual imports & call boundaries.
              </p>

              <div className="space-y-2 pt-1 font-mono">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-400">Precision:</span>
                  <span className="font-bold text-emerald-400">
                    {(architecture_eval.precision * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-400">Recall:</span>
                  <span className="font-bold text-cyan-400">
                    {(architecture_eval.recall * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="flex items-center justify-between text-xs pt-1 border-t border-slate-800">
                  <span className="font-sans font-semibold text-slate-300">Composite F1 Score:</span>
                  <span className="font-bold text-indigo-300 text-sm">
                    {architecture_eval.f1_score.toFixed(3)}
                  </span>
                </div>
              </div>
              <div className="text-[10px] text-slate-500 font-mono">
                Sample size: {architecture_eval.tested_samples} dependency edges evaluated
              </div>
            </div>

            {/* Step 18: Blast Radius Backtesting Evaluation */}
            <div className="p-4 rounded-xl bg-slate-900/60 border border-rose-500/30 space-y-3">
              <div className="flex items-center gap-2">
                <Flame className="w-4 h-4 text-rose-400" />
                <h4 className="font-bold text-xs text-white">
                  Step 18: Historical Blast-Radius Evaluation
                </h4>
              </div>
              <p className="text-[11px] text-slate-400">
                Backtesting multi-file Git commits: given seed file A, predict actual co-affected {`{B, C, D}`}.
              </p>

              <div className="space-y-2 pt-1 font-mono">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-400">Precision:</span>
                  <span className="font-bold text-emerald-400">
                    {(blast_radius_eval.precision * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-400">Recall:</span>
                  <span className="font-bold text-cyan-400">
                    {(blast_radius_eval.recall * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="flex items-center justify-between text-xs pt-1 border-t border-slate-800">
                  <span className="font-sans font-semibold text-slate-300">Composite F1 Score:</span>
                  <span className="font-bold text-rose-300 text-sm">
                    {blast_radius_eval.f1_score.toFixed(3)}
                  </span>
                </div>
              </div>
              <div className="text-[10px] text-slate-500 font-mono">
                Sample size: {blast_radius_eval.tested_samples} historical commits backtested
              </div>
            </div>
          </div>

          {/* Historical Run Details */}
          {blast_radius_eval.details?.top_runs && (
            <div>
              <h5 className="text-xs font-bold uppercase tracking-wider text-slate-300 mb-2">
                Recent Backtested Commit Experiments
              </h5>
              <div className="space-y-1.5">
                {blast_radius_eval.details.top_runs.map((run: any, idx: number) => (
                  <div
                    key={idx}
                    className="p-2.5 rounded bg-slate-900/60 border border-slate-800 flex items-center justify-between text-xs font-mono"
                  >
                    <div className="space-y-0.5">
                      <div className="flex items-center gap-2">
                        <span className="text-indigo-400 font-bold">{run.commit_hash}</span>
                        <span className="text-slate-300 truncate max-w-md font-sans">
                          {run.commit_msg}
                        </span>
                      </div>
                      <div className="text-[10px] text-slate-500">
                        Seed: <span className="text-slate-400">{run.seed_file}</span> • Actual: {run.ground_truth_count} • Predicted: {run.predicted_count}
                      </div>
                    </div>

                    <div className="text-right shrink-0">
                      <span className="badge badge-service text-[10px]">
                        F1: {run.f1}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
