import React, { useState, useRef, useEffect, useMemo } from 'react';
import { 
  Network, 
  ZoomIn, 
  ZoomOut, 
  RotateCcw, 
  Layers, 
  Flame, 
  Info,
  Maximize2
} from 'lucide-react';
import { SoftwareGraph, GraphNode, GraphEdge, BlastRadiusResult } from '../api/client';

interface ArchitectureGraphProps {
  graph: SoftwareGraph | null;
  selectedFilePath: string | null;
  onSelectNode: (path: string) => void;
  blastRadius: BlastRadiusResult | null;
}

export const ArchitectureGraph: React.FC<ArchitectureGraphProps> = ({
  graph,
  selectedFilePath,
  onSelectNode,
  blastRadius
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [filterLayer, setFilterLayer] = useState<string>('all');

  // Compute node layout (layered tier positioning)
  const layoutNodes = useMemo(() => {
    if (!graph || !graph.nodes) return [];

    const nodes = [...graph.nodes];
    const tiers: Record<string, GraphNode[]> = {
      controller: [],
      middleware: [],
      service: [],
      repository: [],
      model: [],
      other: []
    };

    nodes.forEach(n => {
      const type = (n.component_type || '').toLowerCase();
      if (type.includes('controller') || type.includes('route') || type.includes('api')) tiers.controller.push(n);
      else if (type.includes('middleware') || type.includes('guard')) tiers.middleware.push(n);
      else if (type.includes('service') || type.includes('usecase')) tiers.service.push(n);
      else if (type.includes('repository') || type.includes('dao')) tiers.repository.push(n);
      else if (type.includes('model') || type.includes('schema') || type.includes('entity')) tiers.model.push(n);
      else tiers.other.push(n);
    });

    const positioned: Array<GraphNode & { x: number; y: number; color: string }> = [];
    const tierOrder = ['controller', 'middleware', 'service', 'repository', 'model', 'other'];
    const startY = 80;
    const tierSpacing = 130;

    tierOrder.forEach((tName, tIndex) => {
      const list = tiers[tName];
      const count = list.length;
      const totalWidth = Math.max(800, count * 220);
      const spacingX = totalWidth / (count + 1);

      list.forEach((node, idx) => {
        let color = '#94a3b8';
        if (tName === 'controller') color = '#10b981';
        else if (tName === 'middleware') color = '#d946ef';
        else if (tName === 'service') color = '#818cf8';
        else if (tName === 'repository') color = '#f59e0b';
        else if (tName === 'model') color = '#06b6d4';
        else if ((node.component_type || '').toLowerCase().includes('test')) color = '#f43f5e';

        positioned.push({
          ...node,
          x: spacingX * (idx + 1) - totalWidth / 2 + 450,
          y: startY + tIndex * tierSpacing,
          color
        });
      });
    });

    return positioned;
  }, [graph]);

  const nodeMap = useMemo(() => {
    const map = new Map<string, typeof layoutNodes[0]>();
    layoutNodes.forEach(n => map.set(n.id, n));
    return map;
  }, [layoutNodes]);

  // Handle Pan
  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.button !== 0) return;
    setIsDragging(true);
    setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging) return;
    setPan({ x: e.clientX - dragStart.x, y: e.clientY - dragStart.y });
  };

  const handleMouseUp = () => setIsDragging(false);

  const resetView = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  };

  // Determine Blast Radius highlights
  const directSet = useMemo(() => new Set(blastRadius?.direct_affected_files || []), [blastRadius]);
  const indirectSet = useMemo(() => new Set(blastRadius?.indirect_affected_files || []), [blastRadius]);

  return (
    <div className="glass-panel relative flex flex-col h-full overflow-hidden border border-subtle">
      {/* Graph Toolbar */}
      <div className="p-3 border-b border-subtle bg-slate-950/40 flex items-center justify-between z-10">
        <div className="flex items-center gap-2">
          <Network className="w-4 h-4 text-indigo-400" />
          <span className="text-xs font-bold uppercase tracking-wider text-slate-300">
            Interactive Architecture & Call Graph
          </span>
          {graph && (
            <span className="text-[11px] font-mono text-slate-400 ml-2">
              {graph.stats.total_nodes} components, {graph.stats.total_edges} dependencies
            </span>
          )}
        </div>

        {/* Zoom & View Controls */}
        <div className="flex items-center gap-1.5">
          <button
            onClick={() => setZoom(z => Math.min(2.0, z + 0.15))}
            className="p-1.5 rounded bg-slate-800/80 hover:bg-slate-700 text-slate-300 text-xs"
            title="Zoom In"
          >
            <ZoomIn className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => setZoom(z => Math.max(0.4, z - 0.15))}
            className="p-1.5 rounded bg-slate-800/80 hover:bg-slate-700 text-slate-300 text-xs"
            title="Zoom Out"
          >
            <ZoomOut className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={resetView}
            className="p-1.5 rounded bg-slate-800/80 hover:bg-slate-700 text-slate-300 text-xs"
            title="Reset View"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* SVG Canvas */}
      <div
        ref={containerRef}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        className="flex-1 w-full h-full cursor-grab active:cursor-grabbing overflow-hidden bg-[#090d16]"
      >
        <svg
          className="w-full h-full select-none"
          style={{
            transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
            transformOrigin: 'center center',
            transition: isDragging ? 'none' : 'transform 0.1s ease-out'
          }}
        >
          <defs>
            <marker
              id="arrow-default"
              viewBox="0 0 10 10"
              refX="22"
              refY="5"
              markerWidth="6"
              markerHeight="6"
              orient="auto-start-reverse"
            >
              <path d="M 0 1 L 10 5 L 0 9 z" fill="#64748b" opacity="0.6" />
            </marker>
            <marker
              id="arrow-impact"
              viewBox="0 0 10 10"
              refX="22"
              refY="5"
              markerWidth="7"
              markerHeight="7"
              orient="auto-start-reverse"
            >
              <path d="M 0 1 L 10 5 L 0 9 z" fill="#f43f5e" />
            </marker>
          </defs>

          {/* Render Edges */}
          {graph?.edges.map((edge, i) => {
            const sourceNode = nodeMap.get(edge.source);
            const targetNode = nodeMap.get(edge.target);
            if (!sourceNode || !targetNode) return null;

            const isSourceSelected = selectedFilePath === edge.source;
            const isTargetSelected = selectedFilePath === edge.target;
            const isImpactEdge = 
              (isTargetSelected && directSet.has(edge.source)) ||
              (directSet.has(edge.target) && indirectSet.has(edge.source));

            return (
              <g key={`edge-${i}`}>
                <line
                  x1={sourceNode.x}
                  y1={sourceNode.y}
                  x2={targetNode.x}
                  y2={targetNode.y}
                  stroke={isImpactEdge ? '#f43f5e' : isSourceSelected || isTargetSelected ? '#6366f1' : '#334155'}
                  strokeWidth={isImpactEdge ? 2.5 : isSourceSelected || isTargetSelected ? 2 : 1}
                  strokeDasharray={edge.relation === 'EXTENDS' ? '4 4' : undefined}
                  markerEnd={isImpactEdge ? 'url(#arrow-impact)' : 'url(#arrow-default)'}
                  opacity={isImpactEdge ? 1 : isSourceSelected || isTargetSelected ? 0.9 : 0.35}
                />
              </g>
            );
          })}

          {/* Render Nodes */}
          {layoutNodes.map(node => {
            const isSelected = selectedFilePath === node.id;
            const isDirectImpact = directSet.has(node.id);
            const isIndirectImpact = indirectSet.has(node.id);

            let strokeColor = node.color;
            let filter = undefined;

            if (isSelected) {
              strokeColor = '#ffffff';
            } else if (isDirectImpact) {
              strokeColor = '#f43f5e';
            } else if (isIndirectImpact) {
              strokeColor = '#fb923c';
            }

            return (
              <g
                key={node.id}
                transform={`translate(${node.x}, ${node.y})`}
                onClick={(e) => {
                  e.stopPropagation();
                  onSelectNode(node.id);
                }}
                className="cursor-pointer group"
              >
                {/* Selection & Blast Radius Rings */}
                {isSelected && (
                  <circle
                    r={36}
                    fill="none"
                    stroke="#6366f1"
                    strokeWidth={2}
                    opacity={0.7}
                    className="pulse-glow"
                  />
                )}
                {isDirectImpact && (
                  <circle
                    r={34}
                    fill="none"
                    stroke="#f43f5e"
                    strokeWidth={2}
                    strokeDasharray="4 2"
                    className="pulse-glow"
                  />
                )}
                {isIndirectImpact && (
                  <circle
                    r={32}
                    fill="none"
                    stroke="#fb923c"
                    strokeWidth={1.5}
                    strokeDasharray="3 3"
                  />
                )}

                {/* Node Body Card */}
                <rect
                  x={-85}
                  y={-24}
                  width={170}
                  height={48}
                  rx={8}
                  fill={isSelected ? '#1e1b4b' : '#0f172a'}
                  stroke={strokeColor}
                  strokeWidth={isSelected || isDirectImpact ? 2.5 : 1.2}
                  className="transition-all duration-200 group-hover:filter group-hover:brightness-125"
                />

                {/* Type Indicator Pill */}
                <circle
                  cx={-68}
                  cy={0}
                  r={6}
                  fill={node.color}
                />

                {/* Label & Details */}
                <text
                  x={-54}
                  y={-3}
                  fill="#f8fafc"
                  fontSize="11"
                  fontWeight="600"
                  fontFamily="Outfit, sans-serif"
                >
                  {node.label.length > 17 ? node.label.slice(0, 16) + '...' : node.label}
                </text>
                <text
                  x={-54}
                  y={13}
                  fill="#94a3b8"
                  fontSize="9"
                  fontFamily="JetBrains Mono, monospace"
                >
                  {node.component_type || 'Module'} • {node.loc || 0}L
                </text>

                {/* Impact Badge */}
                {isDirectImpact && (
                  <g transform="translate(68, -16)">
                    <circle r={9} fill="#f43f5e" />
                    <text y={3} textAnchor="middle" fill="#fff" fontSize="8" fontWeight="bold">D</text>
                  </g>
                )}
                {isIndirectImpact && (
                  <g transform="translate(68, -16)">
                    <circle r={9} fill="#fb923c" />
                    <text y={3} textAnchor="middle" fill="#fff" fontSize="8" fontWeight="bold">I</text>
                  </g>
                )}
              </g>
            );
          })}
        </svg>
      </div>

      {/* Legend Footer */}
      <div className="p-2 border-t border-subtle bg-slate-950/60 flex items-center justify-between text-[11px] text-slate-400">
        <div className="flex items-center gap-4">
          <span className="font-semibold text-slate-300">Tiers:</span>
          <div className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-emerald-500"></span> Controller</div>
          <div className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-indigo-500"></span> Service</div>
          <div className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-amber-500"></span> Repository</div>
          <div className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-cyan-500"></span> Model</div>
          <div className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-rose-500"></span> Test</div>
        </div>

        {blastRadius && (
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1 text-rose-400">
              <span className="w-2 h-2 rounded-full bg-rose-500"></span> Direct Impact ({blastRadius.direct_affected_files.length})
            </span>
            <span className="flex items-center gap-1 text-orange-400">
              <span className="w-2 h-2 rounded-full bg-orange-500"></span> Indirect Impact ({blastRadius.indirect_affected_files.length})
            </span>
          </div>
        )}
      </div>
    </div>
  );
};
