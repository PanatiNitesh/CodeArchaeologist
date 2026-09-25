import React, { useState, useMemo } from 'react';
import { 
  Folder, 
  FolderOpen, 
  FileCode, 
  Search, 
  ChevronRight, 
  ChevronDown, 
  X,
  SlidersHorizontal
} from 'lucide-react';
import { FileItem } from '../api/client';

interface FileTreeProps {
  files: FileItem[];
  selectedFilePath: string | null;
  onSelectFile: (filePath: string) => void;
}

interface TreeNode {
  name: string;
  path: string;
  isDir: boolean;
  children: Record<string, TreeNode>;
  fileData?: FileItem;
}

export const FileTree: React.FC<FileTreeProps> = ({
  files,
  selectedFilePath,
  onSelectFile
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [expandedFolders, setExpandedFolders] = useState<Record<string, boolean>>({
    'src': true,
    'src/auth': true,
    'src/users': true,
    'src/payment': true,
    'src/orders': true,
    'src/common': true,
    'src/tests': true
  });

  const toggleFolder = (path: string) => {
    setExpandedFolders(prev => ({ ...prev, [path]: !prev[path] }));
  };

  const treeRoot = useMemo(() => {
    const root: TreeNode = { name: 'root', path: '', isDir: true, children: {} };

    const filtered = files.filter(f => 
      f.path.toLowerCase().includes(searchTerm.toLowerCase()) ||
      f.component_type.toLowerCase().includes(searchTerm.toLowerCase())
    );

    for (const f of filtered) {
      const parts = f.path.split('/');
      let current = root;

      for (let i = 0; i < parts.length; i++) {
        const part = parts[i];
        const isFile = i === parts.length - 1;
        const currentPath = parts.slice(0, i + 1).join('/');

        if (!current.children[part]) {
          current.children[part] = {
            name: part,
            path: currentPath,
            isDir: !isFile,
            children: {},
            fileData: isFile ? f : undefined
          };
        }
        current = current.children[part];
      }
    }
    return root;
  }, [files, searchTerm]);

  const getComponentBadge = (type: string, confidence?: number) => {
    const t = (type || 'unknown').toLowerCase();
    let badgeClass = 'badge-utility';
    let shortCode = 'UTIL';

    if (t.includes('controller') || t.includes('route')) {
      badgeClass = 'badge-controller';
      shortCode = 'CTRL';
    } else if (t.includes('service')) {
      badgeClass = 'badge-service';
      shortCode = 'SRV';
    } else if (t.includes('repository') || t.includes('dao')) {
      badgeClass = 'badge-repository';
      shortCode = 'REPO';
    } else if (t.includes('model') || t.includes('schema')) {
      badgeClass = 'badge-model';
      shortCode = 'MOD';
    } else if (t.includes('component')) {
      badgeClass = 'badge-component';
      shortCode = 'UI';
    } else if (t.includes('test')) {
      badgeClass = 'badge-test';
      shortCode = 'TEST';
    } else if (t.includes('middleware')) {
      badgeClass = 'badge-middleware';
      shortCode = 'MID';
    }

    const confPct = confidence ? `${Math.round(confidence * 100)}%` : '92%';

    return (
      <span
        className={`badge-arch ${badgeClass} text-[8.5px] px-1.5 py-0.5 tracking-wider`}
        title={`Classified as ${type} (${confPct} confidence)`}
      >
        {shortCode}
      </span>
    );
  };

  const renderNode = (node: TreeNode, depth: number = 0) => {
    if (node.name === 'root') {
      return Object.values(node.children)
        .sort((a, b) => (b.isDir ? 1 : 0) - (a.isDir ? 1 : 0) || a.name.localeCompare(b.name))
        .map(child => renderNode(child, depth));
    }

    if (node.isDir) {
      const isExpanded = expandedFolders[node.path] ?? true;
      return (
        <div key={node.path} className="select-none">
          <div
            onClick={() => toggleFolder(node.path)}
            style={{ paddingLeft: `${depth * 12 + 6}px` }}
            className="flex items-center gap-1.5 py-1 px-1.5 hover:bg-[#181920] rounded cursor-pointer text-zinc-400 hover:text-zinc-200 transition-colors text-xs font-mono"
          >
            {isExpanded ? (
              <ChevronDown className="w-3 h-3 text-zinc-500 shrink-0" />
            ) : (
              <ChevronRight className="w-3 h-3 text-zinc-500 shrink-0" />
            )}
            {isExpanded ? (
              <FolderOpen className="w-3.5 h-3.5 text-indigo-400/80 shrink-0" />
            ) : (
              <Folder className="w-3.5 h-3.5 text-zinc-500 shrink-0" />
            )}
            <span className="truncate">{node.name}</span>
          </div>

          {isExpanded && (
            <div>
              {Object.values(node.children)
                .sort((a, b) => (b.isDir ? 1 : 0) - (a.isDir ? 1 : 0) || a.name.localeCompare(b.name))
                .map(child => renderNode(child, depth + 1))}
            </div>
          )}
        </div>
      );
    }

    const isSelected = selectedFilePath === node.path;
    const file = node.fileData!;

    return (
      <div
        key={node.path}
        onClick={() => onSelectFile(node.path)}
        style={{ paddingLeft: `${depth * 12 + 18}px` }}
        className={`group flex items-center justify-between py-1 px-2 rounded cursor-pointer text-xs transition-colors font-mono ${
          isSelected
            ? 'bg-[#1c1d25] border-l-2 border-indigo-500 text-white font-medium'
            : 'text-zinc-400 hover:bg-[#16171d] hover:text-zinc-200'
        }`}
      >
        <div className="flex items-center gap-2 truncate">
          <FileCode className={`w-3.5 h-3.5 shrink-0 ${isSelected ? 'text-indigo-400' : 'text-zinc-500'}`} />
          <span className="truncate">{node.name}</span>
        </div>

        <div className="flex items-center gap-1.5 shrink-0">
          {getComponentBadge(file.component_type, file.component_confidence)}
          <span className="text-[10px] text-zinc-600 font-mono hidden group-hover:inline">
            {file.loc}L
          </span>
        </div>
      </div>
    );
  };

  return (
    <div className="studio-panel flex flex-col h-full bg-[#0e0f14]">
      {/* Header */}
      <div className="p-2.5 border-b border-[var(--border-hairline)] bg-[#121318]">
        <div className="flex items-center justify-between mb-2">
          <span className="text-[11px] font-mono font-semibold uppercase tracking-wider text-zinc-400">
            Explorer
          </span>
          <span className="text-[10px] font-mono text-zinc-500">
            {files.length} indexed files
          </span>
        </div>

        {/* Filter Input */}
        <div className="relative flex items-center">
          <Search className="w-3.5 h-3.5 absolute left-2 text-zinc-500 pointer-events-none" />
          <input
            type="text"
            placeholder="Filter files or tiers..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-[#090a0d] border border-zinc-800 rounded pl-7 pr-7 py-1 text-xs font-mono text-zinc-200 placeholder-zinc-600 focus:outline-none focus:border-indigo-500"
          />
          {searchTerm && (
            <button 
              onClick={() => setSearchTerm('')}
              className="absolute right-2 text-zinc-500 hover:text-zinc-300"
            >
              <X className="w-3 h-3" />
            </button>
          )}
        </div>
      </div>

      {/* Tree Content */}
      <div className="flex-1 overflow-y-auto p-1.5 space-y-0.5">
        {renderNode(treeRoot)}
      </div>
    </div>
  );
};
