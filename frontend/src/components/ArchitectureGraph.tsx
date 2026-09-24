import React, { useState, useRef, useMemo } from 'react';
import { 
  Network, 
  ZoomIn, 
  ZoomOut, 
  RotateCcw, 
  Layers, 
  Flame, 
  Sliders,
  Filter,
  Move
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
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);

  // Position nodes by architectural tiers
  const { positionedNodes, tierLabels } = useMemo(() => {
    if (!graph || !graph.nodes) return { positionedNodes: [], tierLabels: [] };

    const nodes = [...graph.nodes];
    const tiers: Record<string, { label: string; nodes: GraphNode[] }> = {
      controller: { label: 'CONTROLLERS & API INGRESS', nodes: [] },
      middleware: { label: 'MIDDLEWARE & INTERCEPTORS', nodes: [] },
      service: { label: 'DOMAIN SERVICES & APPLICATION LOGIC', nodes: [] },
      repository: { label: 'DATA REPOSITORIES & STORAGE', nodes: [] },
      model: { label: 'DATA MODELS & ENTITIES', nodes: [] },
      test: { label: 'TEST SUITES & INTEGRATION SPECS', nodes: [] },
      other: { label: 'COMMON & SHARED INFRASTRUCTURE', nodes: [] }
    };

    nodes.forEach(n => {
      const type = (n.component_type || '').toLowerCase();
      if (type.includes('controller') || type.includes('route') || type.includes('api')) tiers.controller.nodes.push(n);
      else if (type.includes('middleware') || type.includes('guard')) tiers.middleware.nodes.push(n);
      else if (type.includes('service') || type.includes('usecase')) tiers.service.nodes.push(n);
      else if (type.includes('repository') || type.includes('dao')) tiers.repository.nodes.push(n);
      else if (type.includes('model') || type.includes('schema') || type.includes('entity')) tiers.model.nodes.push(n);
      else if (type.includes('test')) tiers.test.nodes.push(n);
      else tiers.other.nodes.push(n);
    });

    const positioned: Array<GraphNode & { x: number; y: number; color: string; tierKey: string }> = [];
    const labels: Array<{ text: string; y: number }> = [];

    const activeTiers = Object.entries(tiers).filter(([_, data]) => data.nodes.length > 0);
    const startY = 70;
    const tierSpacing = 140;

    activeTiers.forEach(([tKey, data], tIndex) => {
      const currentY = startY + tIndex * tierSpacing;
      labels.push({ text: data.label, y: currentY - 32 });

      const count = data.nodes.length;
      const totalWidth = Math.max(900, count * 220);
      const spacingX = totalWidth / (count + 1);

      data.nodes.forEach((node, idx) => {
        let color = '#94a3b8';
        if (tKey === 'controller') color = '#10b981';
        else if (tKey === 'middleware') color = '#ec4899';
        else if (tKey === 'service') color = '#6366f1';
        else if (tKey === 'repository') color = '#f59e0b';
        else if (tKey === 'model') color = '#06b6d4';
        else if (tKey === 'test') color = '#f43f5e';

        positioned.push({
          ...node,
          x: spacingX * (idx + 1) - totalWidth / 2 + 500,
          y: currentY,
          color,
          tierKey: tKey
        });
      });
    });

    return { positionedNodes: positioned, tierLabels: labels };
  }, [graph]);

  const nodeMap = useMemo(() => {
    const map = new Map<string, typeof positionedNodes[0]>();
    positionedNodes.forEach(n => map.set(n.id, n));
    return map;
  }, [positionedNodes]);

  const directSet = useMemo(() => new Set(blastRadius?.direct_affected_files || []), [blastRadius]);
  const indirectSet = useMemo(() => new Set(blastRadius?.indirect_affected_files || []), [blastRadius]);

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

  return (
    <div className="studio-panel relative flex flex-col h-full bg-[#0c0d12]">
      {/* Top Toolbar */}
      <div className="h-9 px-3 border-b border-[var(--border-hairline)] bg-[#121318] flex items-center justify-between z-10 select-none">
        <div className="flex items-center gap-2">
          <Network className="w-3.5 h-3.5 text-indigo-400" />
          <span className="text-[11px] font-mono font-semibold uppercase tracking-wider text-zinc-300">
            Topology Graph
          </span>
          {graph && (
            <span className="text-[10px] font-mono text-zinc-500">
              ({graph.stats.total_nodes} nodes • {graph.stats.total_edges} dependencies)
            </span>
          )}
        </div>

        {/* View Controls */}
        <div className="flex items-center gap-1">
          <button
            onClick={() => setZoom(z => Math.min(2.0, z + 0.15))}
            className="p-1 rounded hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors"
            title="Zoom In"
          >
            <ZoomIn className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => setZoom(z => Math.max(0.4, z - 0.15))}
            className="p-1 rounded hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors"
            title="Zoom Out"
          >
            <ZoomOut className="w-3.5 h-3.5" />
          </button>
          <div className="h-3 w-px bg-zinc-800 mx-0.5" />
          <button
            onClick={resetView}
            className="p-1 rounded hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors"
            title="Reset Pan & Zoom"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* SVG Canvas Area */}
      <div
        ref={containerRef}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        className="flex-1 w-full h-full cursor-grab active:cursor-grabbing overflow-hidden bg-graph-grid relative"
      >
        <svg
          className="w-full h-full select-none"
          style={{
            transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
            transformOrigin: 'center center',
            transition: isDragging ? 'none' : 'transform 0.08s ease-out'
          }}
        >
          <defs>
            <marker
              id="arrow-default"
              viewBox="0 0 10 10"
              refX="22"
              refY="5"
              markerWidth="5"
              markerHeight="5"
              orient="auto-start-reverse"
            >
              <path d="M 0 1.5 L 10 5 L 0 8.5 z" fill="#4b5563" opacity="0.6" />
            </marker>
            <marker
              id="arrow-active"
              viewBox="0 0 10 10"
              refX="22"
              refY="5"
              markerWidth="6"
              markerHeight="6"
              orient="auto-start-reverse"
            >
              <path d="M 0 1 L 10 5 L 0 9 z" fill="#6366f1" />
            </marker>
            <marker
              id="arrow-impact"
              viewBox="0 0 10 10"
              refX="22"
              refY="5"
              markerWidth="6"
              markerHeight="6"
              orient="auto-start-reverse"
            >
              <path d="M 0 1 L 10 5 L 0 9 z" fill="#f43f5e" />
            </marker>
          </defs>

          {/* Tier Boundary Guidelines */}
          {tierLabels.map((lbl, idx) => (
            <g key={`tier-${idx}`}>
              <line
                x1={-1000}
                y1={lbl.y + 12}
                x2={2000}
                y2={lbl.y + 12}
                stroke="#1f222e"
                strokeWidth={1}
                strokeDasharray="4 4"
              />
              <text
                x={-50}
                y={lbl.y + 6}
                fill="#4b5563"
                fontSize="10"
                fontWeight="600"
                fontFamily="JetBrains Mono, monospace"
                letterSpacing="1px"
              >
                {lbl.text}
              </text>
            </g>
          ))}

          {/* Render Curved Bezier Edges */}
          {graph?.edges.map((edge, i) => {
            const src = nodeMap.get(edge.source);
            const tgt = nodeMap.get(edge.target);
            if (!src || !tgt) return null;

            const isSourceSelected = selectedFilePath === edge.source;
            const isTargetSelected = selectedFilePath === edge.target;
            const isSourceHovered = hoveredNodeId === edge.source;
            const isTargetHovered = hoveredNodeId === edge.target;

            const isImpactEdge = 
              (isTargetSelected && directSet.has(edge.source)) ||
              (directSet.has(edge.target) && indirectSet.has(edge.source));

            const isHighlighted = isSourceSelected || isTargetSelected || isSourceHovered || isTargetHovered;

            // Smooth vertical Bezier spline
            const dx = tgt.x - src.x;
            const dy = tgt.y - src.y;
            const cy1 = src.y + dy * 0.5;
            const cy2 = tgt.y - dy * 0.5;
            const pathD = `M ${src.x} ${src.y} C ${src.x} ${cy1}, ${tgt.x} ${cy2}, ${tgt.x} ${tgt.y}`;

            let stroke = '#262936';
            let strokeWidth = 1.2;
            let marker = 'url(#arrow-default)';

            if (isImpactEdge) {
              stroke = '#f43f5e';
              strokeWidth = 2.2;
              marker = 'url(#arrow-impact)';
            } else if (isHighlighted) {
              stroke = '#6366f1';
              strokeWidth = 1.8;
              marker = 'url(#arrow-active)';
            }

            return (
              <path
                key={`edge-${i}`}
                d={pathD}
                fill="none"
                stroke={stroke}
                strokeWidth={strokeWidth}
                strokeDasharray={edge.relation === 'EXTENDS' ? '3 3' : undefined}
                markerEnd={marker}
                opacity={isImpactEdge || isHighlighted ? 1 : 0.4}
              />
            );
          })}

          {/* Render Precision Node Cards */}
          {positionedNodes.map(node => {
            const isSelected = selectedFilePath === node.id;
            const isDirectImpact = directSet.has(node.id);
            const isIndirectImpact = indirectSet.has(node.id);
            const isHovered = hoveredNodeId === node.id;

            let borderColor = 'rgba(255, 255, 255, 0.1)';
            let bgColor = '#13141b';

            if (isSelected) {
              borderColor = '#6366f1';
              bgColor = '#1a1c28';
            } else if (isDirectImpact) {
              borderColor = '#f43f5e';
              bgColor = '#1e141a';
            } else if (isIndirectImpact) {
              borderColor = '#f59e0b';
              bgColor = '#1e1a14';
            } else if (isHovered) {
              borderColor = 'rgba(255, 255, 255, 0.25)';
              bgColor = '#181a23';
            }

            return (
              <g
                key={node.id}
                transform={`translate(${node.x}, ${node.y})`}
                onClick={(e) => {
                  e.stopPropagation();
                  onSelectNode(node.id);
                }}
                onMouseEnter={() => setHoveredNodeId(node.id)}
                onMouseLeave={() => setHoveredNodeId(null)}
                className="cursor-pointer"
              >
                {/* Active Outer Ring */}
                {isSelected && (
                  <rect
                    x={-92}
                    y={-28}
                    width={184}
                    height={56}
                    rx={8}
                    fill="none"
                    stroke="#6366f1"
                    strokeWidth={1}
                    opacity={0.5}
                    strokeDasharray="4 2"
                  />
                )}

                {/* Node Box */}
                <rect
                  x={-88}
                  y={-24}
                  width={176}
                  height={48}
                  rx={6}
                  fill={bgColor}
                  stroke={borderColor}
                  strokeWidth={isSelected || isDirectImpact ? 1.5 : 1}
                  className="transition-colors duration-150"
                />

                {/* Left Accent Color Strip */}
                <rect
                  x={-88}
                  y={-24}
                  width={3}
                  height={48}
                  rx={1}
                  fill={node.color}
                />

                {/* Title */}
                <text
                  x={-74}
                  y={-4}
                  fill={isSelected ? '#ffffff' : '#e5e7eb'}
                  fontSize="11"
                  fontWeight="600"
                  fontFamily="Inter, sans-serif"
                >
                  {node.label.length > 17 ? node.label.slice(0, 16) + '…' : node.label}
                </text>

                {/* Subtitle / Details */}
                <text
                  x={-74}
                  y={13}
                  fill="#9ca3af"
                  fontSize="9.5"
                  fontFamily="JetBrains Mono, monospace"
                >
                  {node.component_type || 'Module'} • {node.loc || 0}L
                </text>

                {/* Impact Indicator Tag */}
                {isDirectImpact && (
                  <g transform="translate(68, -14)">
                    <rect x={-8} y={-8} width={18} height={14} rx={3} fill="#f43f5e" />
                    <text y={3} textAnchor="middle" fill="#fff" fontSize="8" fontWeight="bold" fontFamily="Inter">DIR</text>
                  </g>
                )}
                {isIndirectImpact && (
                  <g transform="translate(68, -14)">
                    <rect x={-8} y={-8} width={18} height={14} rx={3} fill="#f59e0b" />
                    <text y={3} textAnchor="middle" fill="#fff" fontSize="8" fontWeight="bold" fontFamily="Inter">IND</text>
                  </g>
                )}
              </g>
            );
          })}
        </svg>
      </div>

      {/* Footer Legend */}
      <div className="h-7 px-3 border-t border-[var(--border-hairline)] bg-[#0d0e13] flex items-center justify-between text-[10px] font-mono text-zinc-500 select-none">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-sm bg-emerald-500" /> Controller</div>
          <div className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-sm bg-indigo-500" /> Service</div>
          <div className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-sm bg-amber-500" /> Repository</div>
          <div className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-sm bg-cyan-500" /> Model</div>
          <div className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-sm bg-rose-500" /> Test</div>
        </div>

        {blastRadius && (
          <div className="flex items-center gap-3">
            <span className="text-rose-400">
              Direct Reach: {blastRadius.direct_affected_files.length}
            </span>
            <span className="text-amber-400">
              Indirect Reach: {blastRadius.indirect_affected_files.length}
            </span>
          </div>
        )}
      </div>
    </div>
  );
};
