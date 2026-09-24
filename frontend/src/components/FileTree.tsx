import React, { useState, useMemo } from 'react';
import { 
  Folder, 
  FolderOpen, 
  FileCode2, 
  Search, 
  ChevronRight, 
  ChevronDown, 
  ShieldAlert,
  Flame,
  FileCheck
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
  });

  const toggleFolder = (path: string) => {
    setExpandedFolders(prev => ({ ...prev, [path]: !prev[path] }));
  };

  // Build hierarchical folder tree
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

  const getComponentBadge = (type: string) => {
    const t = type.toLowerCase();
    let badgeClass = 'badge-utility';
    if (t.includes('controller')) badgeClass = 'badge-controller';
    else if (t.includes('service')) badgeClass = 'badge-service';
    else if (t.includes('repository')) badgeClass = 'badge-repository';
    else if (t.includes('model')) badgeClass = 'badge-model';
    else if (t.includes('component')) badgeClass = 'badge-component';
    else if (t.includes('test')) badgeClass = 'badge-test';
    else if (t.includes('middleware')) badgeClass = 'badge-middleware';
    else if (t.includes('config')) badgeClass = 'badge-config';

    return <span className={`badge ${badgeClass} text-[9px] py-0.5 px-1.5`}>{type}</span>;
  };

  const renderNode = (node: TreeNode, depth: number = 0) => {
    if (node.name === 'root') {
      return Object.values(node.children).map(child => renderNode(child, depth));
    }

    if (node.isDir) {
      const isExpanded = expandedFolders[node.path] ?? true;
      return (
        <div key={node.path} className="select-none">
          <div
            onClick={() => toggleFolder(node.path)}
            style={{ paddingLeft: `${depth * 14 + 10}px` }}
            className="flex items-center gap-1.5 py-1.5 px-2 hover:bg-slate-800/60 rounded-md cursor-pointer text-slate-300 hover:text-white transition-colors text-xs font-medium"
          >
            {isExpanded ? (
              <ChevronDown className="w-3.5 h-3.5 text-slate-500" />
            ) : (
              <ChevronRight className="w-3.5 h-3.5 text-slate-500" />
            )}
            {isExpanded ? (
              <FolderOpen className="w-4 h-4 text-indigo-400" />
            ) : (
              <Folder className="w-4 h-4 text-indigo-400/80" />
            )}
            <span>{node.name}</span>
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
        style={{ paddingLeft: `${depth * 14 + 14}px` }}
        className={`group flex items-center justify-between py-1.5 px-2 rounded-md cursor-pointer text-xs transition-all ${
          isSelected
            ? 'bg-indigo-600/25 border-l-2 border-indigo-400 text-white font-medium'
            : 'text-slate-400 hover:bg-slate-800/40 hover:text-slate-200'
        }`}
      >
        <div className="flex items-center gap-2 truncate">
          <FileCode2 className={`w-3.5 h-3.5 shrink-0 ${isSelected ? 'text-indigo-400' : 'text-slate-500'}`} />
          <span className="truncate">{node.name}</span>
        </div>

        <div className="flex items-center gap-1.5 shrink-0 pl-1">
          {getComponentBadge(file.component_type)}
          <span className="text-[10px] text-slate-500 font-mono hidden group-hover:inline">
            {file.loc}L
          </span>
        </div>
      </div>
    );
  };

  return (
    <div className="glass-panel flex flex-col h-full overflow-hidden border border-subtle">
      {/* Header */}
      <div className="p-3 border-b border-subtle bg-slate-950/40">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
            Repository Architecture Tree
          </span>
          <span className="text-[11px] font-mono text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded">
            {files.length} files
          </span>
        </div>

        {/* Filter input */}
        <div className="relative">
          <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-slate-500" />
          <input
            type="text"
            placeholder="Filter files or components..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-slate-900/90 border border-subtle rounded-md pl-8 pr-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 font-mono"
          />
        </div>
      </div>

      {/* Tree Content */}
      <div className="flex-1 overflow-y-auto p-2 space-y-0.5">
        {renderNode(treeRoot)}
      </div>
    </div>
  );
};
