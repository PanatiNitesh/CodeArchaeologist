import React, { useState } from 'react';
import { 
  History, 
  GitCommit, 
  Calendar, 
  User, 
  Tag, 
  Sparkles,
  ShieldCheck,
  Zap,
  Wrench,
  CheckCircle2,
  Bug
} from 'lucide-react';
import { SoftwareTimeline, CommitRecord } from '../api/client';

interface TimelineViewProps {
  timeline: SoftwareTimeline | null;
  onSelectCommit?: (commit: CommitRecord) => void;
}

export const TimelineView: React.FC<TimelineViewProps> = ({
  timeline,
  onSelectCommit
}) => {
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL');

  if (!timeline || timeline.milestones.length === 0) {
    return (
      <div className="glass-panel p-6 text-center text-slate-400">
        <History className="w-8 h-8 mx-auto mb-2 text-slate-600" />
        <p className="text-sm">No evolutionary Git timeline records available.</p>
      </div>
    );
  }

  const getCategoryBadge = (category: string) => {
    switch (category) {
      case 'FEATURE':
        return <span className="badge bg-indigo-500/15 text-indigo-400 border border-indigo-500/30">Feature</span>;
      case 'BUG_FIX':
        return <span className="badge bg-rose-500/15 text-rose-400 border border-rose-500/30">Bug Fix</span>;
      case 'REFACTOR':
        return <span className="badge bg-purple-500/15 text-purple-400 border border-purple-500/30">Refactor</span>;
      case 'SECURITY':
        return <span className="badge bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">Security</span>;
      case 'PERFORMANCE':
        return <span className="badge bg-amber-500/15 text-amber-400 border border-amber-500/30">Perf</span>;
      case 'TEST':
        return <span className="badge bg-pink-500/15 text-pink-400 border border-pink-500/30">Test</span>;
      default:
        return <span className="badge bg-slate-500/15 text-slate-400 border border-slate-500/30">{category}</span>;
    }
  };

  const categories = ['ALL', ...Object.keys(timeline.category_distribution)];

  return (
    <div className="glass-panel p-4 flex flex-col h-full overflow-hidden border border-subtle">
      {/* Timeline Header & Filters */}
      <div className="flex items-center justify-between pb-3 border-b border-subtle mb-4">
        <div className="flex items-center gap-2">
          <History className="w-4 h-4 text-cyan-400" />
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-300">
            Software Evolution Timeline ({timeline.time_span})
          </h2>
          <span className="text-[11px] font-mono text-cyan-400 bg-cyan-500/10 px-2 py-0.5 rounded">
            {timeline.total_commits} commits mined
          </span>
        </div>

        {/* Category Pills */}
        <div className="flex items-center gap-1 overflow-x-auto max-w-md py-1">
          {categories.map(cat => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className={`px-2 py-1 rounded text-[10px] font-semibold transition-all ${
                selectedCategory === cat
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'bg-slate-800/60 text-slate-400 hover:text-slate-200'
              }`}
            >
              {cat} {cat !== 'ALL' && `(${timeline.category_distribution[cat] || 0})`}
            </button>
          ))}
        </div>
      </div>

      {/* Chronological Milestone Scroll */}
      <div className="flex-1 overflow-y-auto space-y-4 pr-1">
        {timeline.milestones.map((milestone, idx) => {
          const filteredCommits = milestone.key_commits.filter(c => 
            selectedCategory === 'ALL' || c.category === selectedCategory
          );

          if (filteredCommits.length === 0 && selectedCategory !== 'ALL') {
            return null;
          }

          return (
            <div key={`milestone-${idx}`} className="relative pl-6 border-l-2 border-indigo-500/40 pb-2">
              {/* Timeline Node Dot */}
              <div className="absolute -left-[9px] top-0 w-4 h-4 rounded-full bg-slate-950 border-2 border-indigo-400 flex items-center justify-center">
                <div className="w-1.5 h-1.5 rounded-full bg-cyan-400"></div>
              </div>

              {/* Milestone Banner */}
              <div className="bg-slate-900/70 border border-subtle rounded-lg p-3 hover:border-indigo-500/40 transition-all">
                <div className="flex items-center justify-between mb-1.5">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-bold text-indigo-400">
                      {milestone.period}
                    </span>
                    <span className="text-xs font-semibold text-slate-200">
                      {milestone.headline}
                    </span>
                  </div>
                  <span className="text-[10px] text-slate-500 font-mono">
                    {milestone.commit_count} commits in period
                  </span>
                </div>

                {/* Commits in this milestone */}
                <div className="space-y-2 mt-2 pt-2 border-t border-slate-800/80">
                  {filteredCommits.map(commit => (
                    <div
                      key={commit.commit_id}
                      onClick={() => onSelectCommit && onSelectCommit(commit)}
                      className="flex items-start justify-between p-2 rounded bg-slate-950/60 border border-slate-800/50 hover:border-slate-700 cursor-pointer text-xs"
                    >
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          {getCategoryBadge(commit.category)}
                          <span className="font-mono text-cyan-300 font-bold text-[11px]">
                            {commit.short_hash}
                          </span>
                          <span className="text-slate-300 font-medium">
                            {commit.message}
                          </span>
                        </div>

                        <div className="flex items-center gap-3 text-[10px] text-slate-500">
                          <span className="flex items-center gap-1">
                            <User className="w-3 h-3 text-slate-400" />
                            {commit.author}
                          </span>
                          <span className="flex items-center gap-1 font-mono">
                            <Calendar className="w-3 h-3 text-slate-400" />
                            {commit.date}
                          </span>
                          {commit.changed_files.length > 0 && (
                            <span className="font-mono text-slate-400">
                              Touched {commit.changed_files.length} files
                            </span>
                          )}
                        </div>
                      </div>

                      <div className="text-right font-mono text-[10px] shrink-0 pl-2">
                        <span className="text-emerald-400">+{commit.added_lines}</span>{' '}
                        <span className="text-rose-400">-{commit.deleted_lines}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
