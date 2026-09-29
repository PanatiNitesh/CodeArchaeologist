import React, { useState, useEffect } from 'react';
import { 
  Bot, 
  Layers, 
  History, 
  Flame, 
  Cpu, 
  Loader2, 
  Command,
  Sparkles,
  Compass,
  FolderTree,
  FileCode2,
  CalendarClock
} from 'lucide-react';
import { Header } from './components/Header';
import { FileTree } from './components/FileTree';
import { ArchitectureGraph } from './components/ArchitectureGraph';
import { TimelineView } from './components/TimelineView';
import { FileIntelligence } from './components/FileIntelligence';
import { AIChatDrawer } from './components/AIChatDrawer';
import { BlastRadiusModal } from './components/BlastRadiusModal';
import { EvaluationDashboard } from './components/EvaluationDashboard';
import { AnalyticsModal } from './components/AnalyticsModal';
import { 
  api, 
  RepositoryItem, 
  FileItem, 
  SoftwareGraph, 
  SoftwareTimeline, 
  FileEvolution, 
  BlastRadiusResult, 
  ChangeImpactPrediction,
  OverallEvaluation,
  RAGAnswerResponse
} from './api/client';

export const App: React.FC = () => {
  const [repositories, setRepositories] = useState<RepositoryItem[]>([]);
  const [currentRepoId, setCurrentRepoId] = useState<string>('');
  const [files, setFiles] = useState<FileItem[]>([]);
  const [selectedFilePath, setSelectedFilePath] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<FileItem | null>(null);
  
  const [graph, setGraph] = useState<SoftwareGraph | null>(null);
  const [timeline, setTimeline] = useState<SoftwareTimeline | null>(null);
  const [fileEvolution, setFileEvolution] = useState<FileEvolution | null>(null);
  const [blastRadius, setBlastRadius] = useState<BlastRadiusResult | null>(null);
  const [predictions, setPredictions] = useState<ChangeImpactPrediction | null>(null);
  const [evaluation, setEvaluation] = useState<OverallEvaluation | null>(null);

  const [loading, setLoading] = useState<boolean>(true);
  const [loadingMessage, setLoadingMessage] = useState<string>('Initializing CodeArchaeologist...');
  const [isAIChatOpen, setIsAIChatOpen] = useState<boolean>(false);
  const [isBlastModalOpen, setIsBlastModalOpen] = useState<boolean>(false);
  const [isEvalOpen, setIsEvalOpen] = useState<boolean>(false);
  const [isAnalyticsOpen, setIsAnalyticsOpen] = useState<boolean>(false);
  const [chatInitialPrompt, setChatInitialPrompt] = useState<string>('');
  const [mobileTab, setMobileTab] = useState<'graph' | 'files' | 'intelligence' | 'timeline'>('graph');

  // Initial load
  useEffect(() => {
    loadRepositories();
    api.trackEvent('page_view');
  }, []);

  const loadRepositories = async () => {
    setLoading(true);
    setLoadingMessage('Loading repository registry...');
    try {
      let repos = await api.getRepositories();
      if (!repos || repos.length === 0) {
        setLoadingMessage('Initializing 2022–2026 Enterprise E-Commerce Sample Repository...');
        await api.loadSample();
        repos = await api.getRepositories();
      }
      setRepositories(repos);
      if (repos.length > 0) {
        await switchRepository(repos[0].id);
      }
    } catch (err) {
      console.error('Failed to load repositories:', err);
    } finally {
      setLoading(false);
    }
  };

  const switchRepository = async (repoId: string) => {
    setCurrentRepoId(repoId);
    setLoading(true);
    setLoadingMessage(`Indexing architecture graph and Git archaeology for ${repoId}...`);

    try {
      const [filesData, graphData, timelineData, evalData] = await Promise.all([
        api.getFiles(repoId),
        api.getGraph(repoId),
        api.getTimeline(repoId),
        api.getEvaluation(repoId)
      ]);

      setFiles(filesData);
      setGraph(graphData);
      setTimeline(timelineData);
      setEvaluation(evalData);

      const defaultFile = filesData.find(f => f.path.includes('userService') || f.path.includes('paymentService')) || filesData[0];
      if (defaultFile) {
        await handleSelectFile(defaultFile.path, repoId, filesData);
      } else {
        setSelectedFilePath(null);
        setSelectedFile(null);
      }
    } catch (err) {
      console.error('Failed to switch repo:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectFile = async (filePath: string, repoId: string = currentRepoId, filesList: FileItem[] = files) => {
    setSelectedFilePath(filePath);
    const matched = filesList.find(f => f.path === filePath) || null;
    setSelectedFile(matched);

    try {
      const [evo, blast, pred] = await Promise.all([
        api.getFileIntelligence(repoId, filePath),
        api.calculateBlastRadius(repoId, filePath),
        api.predictImpact(repoId, filePath)
      ]);

      setFileEvolution(evo);
      setBlastRadius(blast);
      setPredictions(pred);
    } catch (err) {
      console.error('Failed to fetch file intelligence:', err);
    }
  };

  const handleIngest = async (url: string) => {
    setLoading(true);
    setLoadingMessage('Executing 8-phase code understanding & Git mining pipeline...');
    try {
      const res = await api.ingest(url);
      const repos = await api.getRepositories();
      setRepositories(repos);
      if (res.repo_id) {
        await switchRepository(res.repo_id);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleLoadSample = async () => {
    setLoading(true);
    setLoadingMessage('Loading 2022–2026 Enterprise E-Commerce Sample Repository...');
    try {
      const res = await api.loadSample();
      const repos = await api.getRepositories();
      setRepositories(repos);
      if (res.repo_id) {
        await switchRepository(res.repo_id);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleAskAIFromComponent = (prompt: string) => {
    setChatInitialPrompt(prompt);
    setIsAIChatOpen(true);
  };

  const handleAskQuestion = async (question: string): Promise<RAGAnswerResponse> => {
    if (!currentRepoId) throw new Error('No repository active');
    return await api.askAI(currentRepoId, question);
  };

  const handleReRunEvaluation = async () => {
    if (!currentRepoId) return;
    const evalData = await api.getEvaluation(currentRepoId);
    setEvaluation(evalData);
  };

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-[#090a0d] text-zinc-100 font-sans">
      {/* Precision Header */}
      <Header
        repositories={repositories}
        currentRepoId={currentRepoId}
        onSelectRepo={switchRepository}
        onIngest={handleIngest}
        onLoadSample={handleLoadSample}
        onOpenEval={() => setIsEvalOpen(true)}
        onOpenAnalytics={() => setIsAnalyticsOpen(true)}
        loading={loading}
      />

      {/* Main Studio Viewport */}
      {loading ? (
        <div className="flex-1 flex flex-col items-center justify-center space-y-3 select-none">
          <Loader2 className="w-8 h-8 animate-spin text-indigo-500" />
          <p className="font-mono text-xs text-zinc-300">{loadingMessage}</p>
          <span className="text-[11px] font-mono text-zinc-600">
            AST Extraction • Graph Generation • Commit Mining • Vector Embeddings
          </span>
        </div>
      ) : (
        <div className="flex-1 flex flex-col min-h-0 p-1 sm:p-2 gap-2 overflow-hidden">
          {/* Mobile View Switcher Tab Bar (< lg screens) */}
          <div className="lg:hidden flex items-center bg-[#111218] p-1 rounded-lg border border-zinc-800 shrink-0">
            <button
              onClick={() => setMobileTab('graph')}
              className={`flex-1 py-1.5 px-2 rounded text-xs font-mono flex items-center justify-center gap-1.5 transition-all ${
                mobileTab === 'graph' 
                  ? 'bg-indigo-600/30 text-indigo-300 font-semibold border border-indigo-500/50' 
                  : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              <Compass className="w-3.5 h-3.5" />
              <span>Graph</span>
            </button>
            <button
              onClick={() => setMobileTab('files')}
              className={`flex-1 py-1.5 px-2 rounded text-xs font-mono flex items-center justify-center gap-1.5 transition-all ${
                mobileTab === 'files' 
                  ? 'bg-indigo-600/30 text-indigo-300 font-semibold border border-indigo-500/50' 
                  : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              <FolderTree className="w-3.5 h-3.5" />
              <span>Files</span>
            </button>
            <button
              onClick={() => setMobileTab('intelligence')}
              className={`flex-1 py-1.5 px-2 rounded text-xs font-mono flex items-center justify-center gap-1.5 transition-all ${
                mobileTab === 'intelligence' 
                  ? 'bg-indigo-600/30 text-indigo-300 font-semibold border border-indigo-500/50' 
                  : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              <FileCode2 className="w-3.5 h-3.5" />
              <span>Intel</span>
            </button>
            <button
              onClick={() => setMobileTab('timeline')}
              className={`flex-1 py-1.5 px-2 rounded text-xs font-mono flex items-center justify-center gap-1.5 transition-all ${
                mobileTab === 'timeline' 
                  ? 'bg-indigo-600/30 text-indigo-300 font-semibold border border-indigo-500/50' 
                  : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              <CalendarClock className="w-3.5 h-3.5" />
              <span>Timeline</span>
            </button>
          </div>

          {/* Mobile Single-Pane Viewport (< lg screens) */}
          <div className="lg:hidden flex-1 min-h-0 overflow-y-auto">
            {mobileTab === 'graph' && (
              <div className="h-full min-h-[400px]">
                <ArchitectureGraph
                  graph={graph}
                  selectedFilePath={selectedFilePath}
                  onSelectNode={handleSelectFile}
                  blastRadius={blastRadius}
                />
              </div>
            )}
            {mobileTab === 'files' && (
              <div className="h-full min-h-[400px]">
                <FileTree
                  files={files}
                  selectedFilePath={selectedFilePath}
                  onSelectFile={(p) => {
                    handleSelectFile(p);
                    setMobileTab('intelligence');
                  }}
                />
              </div>
            )}
            {mobileTab === 'intelligence' && (
              <div className="h-full min-h-[400px]">
                <FileIntelligence
                  file={selectedFile}
                  evolution={fileEvolution}
                  blastRadius={blastRadius}
                  predictions={predictions}
                  onAskAI={handleAskAIFromComponent}
                  onOpenBlastModal={() => setIsBlastModalOpen(true)}
                />
              </div>
            )}
            {mobileTab === 'timeline' && (
              <div className="h-full min-h-[400px]">
                <TimelineView
                  timeline={timeline}
                  onSelectCommit={(c) => {
                    if (c.changed_files.length > 0) {
                      const target = files.find(f => f.path.includes(c.changed_files[0])) || files[0];
                      if (target) {
                        handleSelectFile(target.path);
                        setMobileTab('intelligence');
                      }
                    }
                  }}
                />
              </div>
            )}
          </div>

          {/* Desktop Multi-Pane Grid Viewport (>= lg screens) */}
          <div className="hidden lg:flex flex-col flex-1 min-h-0 gap-2">
            {/* Top Grid: Explorer (Col 3) + Topology Graph (Col 5) + Inspector (Col 4) */}
            <div className="flex-1 grid grid-cols-12 gap-2 min-h-0">
              <div className="col-span-3 h-full min-h-0">
                <FileTree
                  files={files}
                  selectedFilePath={selectedFilePath}
                  onSelectFile={handleSelectFile}
                />
              </div>

              <div className="col-span-5 h-full min-h-0">
                <ArchitectureGraph
                  graph={graph}
                  selectedFilePath={selectedFilePath}
                  onSelectNode={handleSelectFile}
                  blastRadius={blastRadius}
                />
              </div>

              <div className="col-span-4 h-full min-h-0">
                <FileIntelligence
                  file={selectedFile}
                  evolution={fileEvolution}
                  blastRadius={blastRadius}
                  predictions={predictions}
                  onAskAI={handleAskAIFromComponent}
                  onOpenBlastModal={() => setIsBlastModalOpen(true)}
                />
              </div>
            </div>

            {/* Bottom Dock: Software Evolution Timeline */}
            <div className="h-56 shrink-0 min-h-0">
              <TimelineView
                timeline={timeline}
                onSelectCommit={(c) => {
                  if (c.changed_files.length > 0) {
                    const target = files.find(f => f.path.includes(c.changed_files[0])) || files[0];
                    if (target) handleSelectFile(target.path);
                  }
                }}
              />
            </div>
          </div>
        </div>
      )}

      {/* Floating Precision Assistant Trigger */}
      <button
        onClick={() => setIsAIChatOpen(true)}
        className="fixed bottom-4 right-4 px-3 py-2 rounded-lg bg-[#181922] hover:bg-[#20222e] border border-zinc-700/80 shadow-2xl flex items-center gap-2 z-30 transition-all font-mono text-xs text-zinc-200"
        title="Open CodeArchaeologist Evidence Assistant"
      >
        <Bot className="w-4 h-4 text-indigo-400" />
        <span className="font-medium">Evidence Assistant</span>
        <span className="px-1.5 py-0.5 rounded bg-zinc-800 text-[10px] text-zinc-400 border border-zinc-700">
          ⌘K
        </span>
      </button>

      {/* AI Chat Drawer */}
      <AIChatDrawer
        isOpen={isAIChatOpen}
        onClose={() => setIsAIChatOpen(false)}
        onAskQuestion={handleAskQuestion}
        onSelectFile={handleSelectFile}
        initialPrompt={chatInitialPrompt}
      />

      {/* Blast Radius Modal */}
      {isBlastModalOpen && (
        <BlastRadiusModal
          blastRadius={blastRadius}
          predictions={predictions}
          onClose={() => setIsBlastModalOpen(false)}
        />
      )}

      {/* Evaluation Dashboard Modal */}
      {isEvalOpen && (
        <EvaluationDashboard
          evaluation={evaluation}
          onClose={() => setIsEvalOpen(false)}
          onReRun={handleReRunEvaluation}
        />
      )}

      {/* Usage Analytics Modal */}
      {isAnalyticsOpen && (
        <AnalyticsModal
          onClose={() => setIsAnalyticsOpen(false)}
        />
      )}
    </div>
  );
};
