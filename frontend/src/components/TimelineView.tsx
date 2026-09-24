import React, { useState } from 'react';
import { 
  GitCommit, 
  Calendar, 
  User, 
  Tag, 
  Sparkles,
  GitBranch,
  Layers
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
      <div className="studio-panel p-4 text-center text-zinc-500 font-mono text-xs">
        No evolutionary Git timeline records available.
      </div>
    );
  }

  const getCategoryChip = (category: string) => {
    switch (category) {
      case 'FEATURE':
        return <span className="px-1.5 py-0.5 rounded text-[9px] font-mono font-semibold bg-indigo-950/60 text-indigo-400 border border-indigo-800/60">FEAT</span>;
      case 'BUG_FIX':
        return <span className="px-1.5 py-0.5 rounded text-[9px] font-mono font-semibold bg-rose-950/60 text-rose-400 border border-rose-800/60">FIX</span>;
      case 'REFACTOR':
        return <span className="px-1.5 py-0.5 rounded text-[9px] font-mono font-semibold bg-purple-950/60 text-purple-400 border border-purple-800/60">REFACTOR</span>;
      case 'SECURITY':
        return <span className="px-1.5 py-0.5 rounded text-[9px] font-mono font-semibold bg-emerald-950/60 text-emerald-400 border border-emerald-800/60">SEC</span>;
      case 'PERFORMANCE':
        return <span className="px-1.5 py-0.5 rounded text-[9px] font-mono font-semibold bg-amber-950/60 text-amber-400 border border-amber-800/60">PERF</span>;
      case 'TEST':
        return <span className="px-1.5 py-0.5 rounded text-[9px] font-mono font-semibold bg-pink-950/60 text-pink-400 border border-pink-800/60">TEST</span>;
      default:
        return <span className="px-1.5 py-0.5 rounded text-[9px] font-mono font-semibold bg-zinc-800 text-zinc-400">{category}</span>;
    }
  };

  const categories = ['ALL', ...Object.keys(timeline.category_distribution)];

  return (
    <div className="studio-panel flex flex-col h-full bg-[#0d0e13]">
      {/* Header bar */}
      <div className="h-8 px-3 border-b border-[var(--border-hairline)] bg-[#121318] flex items-center justify-between select-none">
        <div className="flex items-center gap-2">
          <GitBranch className="w-3.5 h-3.5 text-zinc-400" />
          <span className="text-[11px] font-mono font-semibold uppercase tracking-wider text-zinc-300">
            Software Evolution Timeline ({timeline.time_span})
          </span>
          <span className="text-[10px] font-mono text-zinc-500">
            • {timeline.total_commits} mined commits
          </span>
        </div>

        {/* Filter Pills */}
        <div className="flex items-center gap-1">
          {categories.map(cat => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className={`px-2 py-0.5 rounded text-[10px] font-mono font-medium transition-colors ${
                selectedCategory === cat
                  ? 'bg-zinc-700 text-white'
                  : 'text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800/50'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      {/* Horizontal / Vertical Timeline Lane */}
      <div className="flex-1 overflow-x-auto overflow-y-auto p-3 flex gap-4 items-start">
        {timeline.milestones.map((milestone, idx) => {
          const filteredCommits = milestone.key_commits.filter(c => 
            selectedCategory === 'ALL' || c.category === selectedCategory
          );

          if (filteredCommits.length === 0 && selectedCategory !== 'ALL') return null;

          return (
            <div
              key={`m-${idx}`}
              className="w-72 shrink-0 rounded-lg bg-[#121319] border border-zinc-800/80 p-2.5 flex flex-col gap-2"
            >
              {/* Milestone Tag */}
              <div className="flex items-center justify-between pb-1.5 border-b border-zinc-800/80">
                <span className="font-mono text-xs font-bold text-indigo-400">
                  {milestone.period}
                </span>
                <span className="text-[10px] font-mono text-zinc-500">
                  {milestone.commit_count} commits
                </span>
              </div>

              <p className="text-[11px] text-zinc-300 font-medium leading-tight">
                {milestone.headline}
              </p>

              {/* Commits */}
              <div className="space-y-1.5 mt-1">
                {filteredCommits.map(c => (
                  <div
                    key={c.commit_id}
                    onClick={() => onSelectCommit && onSelectCommit(c)}
                    className="p-1.5 rounded bg-[#161720] border border-zinc-800/60 hover:border-zinc-700 cursor-pointer text-xs transition-colors"
                  >
                    <div className="flex items-center gap-1.5 mb-1">
                      {getCategoryChip(c.category)}
                      <span className="font-mono text-[10px] text-zinc-400 font-semibold">
                        {c.short_hash}
                      </span>
                      <div className="text-[9px] font-mono text-zinc-500 ml-auto flex items-center gap-1">
                        <span className="text-emerald-500">+{c.added_lines}</span>
                        <span className="text-rose-500">-{c.deleted_lines}</span>
                      </div>
                    </div>

                    <p className="text-[11px] text-zinc-300 truncate font-sans">
                      {c.message}
                    </p>

                    <div className="flex items-center justify-between text-[10px] font-mono text-zinc-500 mt-1">
                      <span className="truncate max-w-[120px]">{c.author}</span>
                      <span>{c.date.slice(0, 10)}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
