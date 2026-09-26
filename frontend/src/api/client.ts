const API_BASE = '/api';

export interface RepositoryItem {
  id: string;
  name: string;
  path: string;
  url: string;
  default_branch: string;
  cloned_at: string;
  stats?: {
    total_files?: number;
    total_loc?: number;
    total_commits?: number;
    arch_f1?: number;
    blast_f1?: number;
  };
}

export interface FileItem {
  path: string;
  name: string;
  extension: string;
  size_bytes: number;
  loc: number;
  component_type: string;
  component_confidence: number;
  functions?: Array<{
    name: string;
    kind: string;
    start_line: number;
    end_line: number;
    params: string[];
    calls: string[];
  }>;
  classes?: Array<{
    name: string;
    super_class?: string;
    methods: string[];
  }>;
  imports?: Array<{
    source: string;
    imported_names: string[];
  }>;
  exports?: Array<{
    name: string;
    kind: string;
  }>;
}

export interface GraphNode {
  id: string;
  label: string;
  type: string;
  component_type?: string;
  path?: string;
  loc?: number;
  degree: number;
  in_degree: number;
  out_degree: number;
}

export interface GraphEdge {
  source: string;
  target: string;
  relation: string;
  details?: any;
}

export interface SoftwareGraph {
  nodes: GraphNode[];
  edges: GraphEdge[];
  stats: Record<string, any>;
}

export interface CommitRecord {
  commit_id: string;
  short_hash: string;
  author: string;
  date: string;
  timestamp: number;
  message: string;
  category: string;
  changed_files: string[];
  added_lines: number;
  deleted_lines: number;
}

export interface TimelineMilestone {
  year: number;
  month: number;
  period: string;
  commit_count: number;
  top_categories: Record<string, number>;
  key_commits: CommitRecord[];
  headline: string;
}

export interface SoftwareTimeline {
  total_commits: number;
  time_span: string;
  milestones: TimelineMilestone[];
  category_distribution: Record<string, number>;
}

export interface FileEvolution {
  file_path: string;
  created_date: string;
  created_commit?: string;
  created_by?: string;
  total_revisions: number;
  total_authors: number;
  authors: string[];
  major_milestones: Array<{
    date: string;
    hash: string;
    type: string;
    description: string;
    author: string;
  }>;
  bug_fixes: CommitRecord[];
  refactors: CommitRecord[];
  recent_changes: CommitRecord[];
  total_churn?: number;
  churn_per_revision?: number;
  hotspot_score?: number;
}

export interface BlastRadiusResult {
  target_file: string;
  direct_affected_files: string[];
  indirect_affected_files: string[];
  affected_apis: string[];
  affected_tests: string[];
  total_impact_count: number;
  risk_level: string;
  risk_score: number;
  impact_graph?: SoftwareGraph;
  explanation: string;
}

export interface ChangePredictionItem {
  file_path: string;
  probability: number;
  co_change_count: number;
  graph_distance: number;
  component_type: string;
  reason: string;
}

export interface ChangeImpactPrediction {
  target_file: string;
  predicted_files: ChangePredictionItem[];
  model_name: string;
  feature_importance: Record<string, number>;
}

export interface EvidenceItem {
  file_path: string;
  line_start?: number;
  line_end?: number;
  commit_hash?: string;
  commit_message?: string;
  commit_date?: string;
  snippet: string;
  relevance_reason: string;
}

export interface RAGAnswerResponse {
  question: string;
  answer: string;
  evidence: EvidenceItem[];
  confidence_score: number;
  retrieval_sources: Record<string, number>;
}

export interface EvaluationMetrics {
  precision: number;
  recall: number;
  f1_score: number;
  tested_samples: number;
  details?: any;
}

export interface OverallEvaluation {
  architecture_eval: EvaluationMetrics;
  blast_radius_eval: EvaluationMetrics;
  commit_count_evaluated: number;
  summary: string;
}

export const api = {
  async getRepositories(): Promise<RepositoryItem[]> {
    const res = await fetch(`${API_BASE}/repositories`);
    return res.json();
  },

  async ingest(repo_url_or_path: string, force_reclone: boolean = false): Promise<any> {
    const res = await fetch(`${API_BASE}/ingest`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ repo_url_or_path, force_reclone })
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async ingestAsync(repo_url_or_path: string, force_reclone: boolean = false): Promise<{ task_id: string; status: string }> {
    const res = await fetch(`${API_BASE}/ingest/async`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ repo_url_or_path, force_reclone })
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async getTaskStatus(taskId: string): Promise<{ task_id: string; status: string; progress?: string; repo_id?: string; error?: string }> {
    const res = await fetch(`${API_BASE}/tasks/${taskId}`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async loadSample(): Promise<any> {
    const res = await fetch(`${API_BASE}/load-sample`, { method: 'POST' });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async getFiles(repoId: string): Promise<FileItem[]> {
    const res = await fetch(`${API_BASE}/repo/${repoId}/files`);
    const data = await res.json();
    return data.files || [];
  },

  async getFileContent(repoId: string, path: string): Promise<any> {
    const res = await fetch(`${API_BASE}/repo/${repoId}/file-content?path=${encodeURIComponent(path)}`);
    return res.json();
  },

  async getGraph(repoId: string): Promise<SoftwareGraph> {
    const res = await fetch(`${API_BASE}/repo/${repoId}/graph`);
    return res.json();
  },

  async getTimeline(repoId: string): Promise<SoftwareTimeline> {
    const res = await fetch(`${API_BASE}/repo/${repoId}/timeline`);
    return res.json();
  },

  async getFileIntelligence(repoId: string, filePath: string): Promise<FileEvolution> {
    const res = await fetch(`${API_BASE}/repo/${repoId}/file-intelligence?file_path=${encodeURIComponent(filePath)}`);
    return res.json();
  },

  async calculateBlastRadius(repoId: string, targetFile: string): Promise<BlastRadiusResult> {
    const res = await fetch(`${API_BASE}/repo/${repoId}/blast-radius?target_file=${encodeURIComponent(targetFile)}`);
    return res.json();
  },

  async predictImpact(repoId: string, targetFile: string): Promise<ChangeImpactPrediction> {
    const res = await fetch(`${API_BASE}/repo/${repoId}/predict-impact?target_file=${encodeURIComponent(targetFile)}`);
    return res.json();
  },

  async askAI(repoId: string, question: string): Promise<RAGAnswerResponse> {
    const res = await fetch(`${API_BASE}/repo/${repoId}/ask`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question })
    });
    return res.json();
  },

  async getEvaluation(repoId: string): Promise<OverallEvaluation> {
    const res = await fetch(`${API_BASE}/repo/${repoId}/evaluation`);
    return res.json();
  }
};
