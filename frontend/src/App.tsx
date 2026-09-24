import React, { useState, useEffect } from 'react';
import { 
  Bot, 
  Layers, 
  History, 
  Flame, 
  Cpu, 
  Loader2, 
  FileText,
  AlertCircle
} from 'lucide-react';
import { Header } from './components/Header';
import { FileTree } from './components/FileTree';
import { ArchitectureGraph } from './components/ArchitectureGraph';
import { TimelineView } from './components/TimelineView';
import { FileIntelligence } from './components/FileIntelligence';
import { AIChatDrawer } from './components/AIChatDrawer';
import { BlastRadiusModal } from './components/BlastRadiusModal';
import { EvaluationDashboard } from './components/EvaluationDashboard';
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
  const [chatInitialPrompt, setChatInitialPrompt] = useState<string>('');

  // Initial load
  useEffect(() => {
    loadRepositories();
  }, []);

  const loadRepositories = async () => {
    setLoading(true);
    setLoadingMessage('Loading repository registry...');
    try {
      let repos = await api.getRepositories();
      if (!repos || repos.length === 0) {
        // Automatically load sample enterprise repo
        setLoadingMessage('Initializing 2022-2026 Enterprise E-Commerce Sample Repository...');
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
    setLoadingMessage(`Loading architecture graph and Git archaeology for ${repoId}...`);

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

      // Select default representative service file
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
    setLoadingMessage('Ingesting repository and running full 8-phase intelligence pipeline...');
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
    setLoadingMessage('Loading 2022-2026 Enterprise E-Commerce Sample Repository...');
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

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-slate-950 text-slate-100">
      {/* Header */}
      <Header
        repositories={repositories}
        currentRepoId={currentRepoId}
        onSelectRepo={switchRepository}
        onIngest={handleIngest}
        onLoadSample={handleLoadSample}
        onOpenEval={() => setIsEvalOpen(true)}
        loading={loading}
      />

      {/* Main Content Area */}
      {loading ? (
        <div className="flex-1 flex flex-col items-center justify-center space-y-4">
          <Loader2 className="w-10 h-10 animate-spin text-indigo-400" />
          <p className="font-mono text-sm text-slate-300">{loadingMessage}</p>
          <span className="text-xs text-slate-500">
            AST Extraction • Graph Generation • Commit Mining • Vector Embeddings
          </span>
        </div>
      ) : (
        <div className="flex-1 flex flex-col min-h-0 p-3 gap-3 overflow-hidden">
          {/* Top Row: File Tree (left) + Architecture Graph (center) + File Intelligence (right) */}
          <div className="flex-1 grid grid-cols-12 gap-3 min-h-0">
            {/* Left: File Tree (Col 3) */}
            <div className="col-span-3 h-full min-h-0">
              <FileTree
                files={files}
                selectedFilePath={selectedFilePath}
                onSelectFile={handleSelectFile}
              />
            </div>

            {/* Center: Architecture Graph (Col 5) */}
            <div className="col-span-5 h-full min-h-0">
              <ArchitectureGraph
                graph={graph}
                selectedFilePath={selectedFilePath}
                onSelectNode={handleSelectFile}
                blastRadius={blastRadius}
              />
            </div>

            {/* Right: File Intelligence Panel (Col 4) */}
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

          {/* Bottom Row: Software Timeline */}
          <div className="h-64 shrink-0 min-h-0">
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
      )}

      {/* Floating AI Chat Trigger Button */}
      <button
        onClick={() => setIsAIChatOpen(true)}
        className="fixed bottom-6 right-6 btn-primary rounded-full p-4 shadow-2xl flex items-center gap-2 z-30"
        title="Open CodeArchaeologist AI Knowledge Chat"
      >
        <Bot className="w-5 h-5 text-white" />
        <span className="font-semibold text-xs pr-1">Ask CodeArchaeologist AI</span>
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
        />
      )}
    </div>
  );
};
