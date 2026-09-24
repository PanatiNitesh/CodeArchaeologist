from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from enum import Enum
from datetime import datetime

class ComponentType(str, Enum):
    CONTROLLER = "Controller"
    SERVICE = "Service"
    REPOSITORY = "Repository"
    MODEL = "Model"
    COMPONENT = "Component"
    UTILITY = "Utility"
    TEST = "Test"
    CONFIGURATION = "Configuration"
    MIDDLEWARE = "Middleware"
    UNKNOWN = "Unknown"

class RelationType(str, Enum):
    IMPORTS = "IMPORTS"
    CALLS = "CALLS"
    EXTENDS = "EXTENDS"
    IMPLEMENTS = "IMPLEMENTS"
    USES = "USES"
    EXPORTS = "EXPORTS"

class CommitCategory(str, Enum):
    FEATURE = "FEATURE"
    BUG_FIX = "BUG_FIX"
    REFACTOR = "REFACTOR"
    SECURITY = "SECURITY"
    PERFORMANCE = "PERFORMANCE"
    DOCUMENTATION = "DOCUMENTATION"
    DEPENDENCY = "DEPENDENCY"
    MIGRATION = "MIGRATION"
    TEST = "TEST"
    OTHER = "OTHER"

class RiskLevel(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"

class SymbolItem(BaseModel):
    name: str
    kind: str # function, class, variable, method, interface
    start_line: int
    end_line: int
    params: List[str] = []
    calls: List[str] = []
    docstring: Optional[str] = None

class ImportItem(BaseModel):
    source: str # imported module / path
    imported_names: List[str] = []
    is_default: bool = False
    raw: str

class ExportItem(BaseModel):
    name: str
    kind: str # named, default, type
    line: int

class FileNode(BaseModel):
    id: str # relative path e.g. "src/auth/authService.ts"
    name: str
    path: str
    extension: str
    size_bytes: int
    lines_of_code: int
    component_type: ComponentType = ComponentType.UNKNOWN
    component_confidence: float = 0.0
    functions: List[SymbolItem] = []
    classes: List[SymbolItem] = []
    imports: List[ImportItem] = []
    exports: List[ExportItem] = []
    calls: List[str] = []

class GraphEdge(BaseModel):
    source: str # file id or symbol id
    target: str # file id or symbol id
    relation: RelationType
    details: Optional[Dict[str, Any]] = None

class GraphNode(BaseModel):
    id: str
    label: str
    type: str # file, class, function, external
    component_type: Optional[ComponentType] = None
    path: Optional[str] = None
    loc: Optional[int] = None
    degree: int = 0
    in_degree: int = 0
    out_degree: int = 0

class SoftwareGraph(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    stats: Dict[str, Any]

class CommitRecord(BaseModel):
    commit_id: str
    short_hash: str
    author: str
    author_email: str
    date: str
    timestamp: int
    message: str
    category: CommitCategory
    changed_files: List[str]
    added_lines: int
    deleted_lines: int

class TimelineMilestone(BaseModel):
    year: int
    month: int
    period: str
    commit_count: int
    top_categories: Dict[str, int]
    key_commits: List[CommitRecord]
    headline: str

class SoftwareTimeline(BaseModel):
    total_commits: int
    time_span: str
    milestones: List[TimelineMilestone]
    category_distribution: Dict[str, int]

class FileEvolution(BaseModel):
    file_path: str
    created_date: str
    created_commit: Optional[str] = None
    created_by: Optional[str] = None
    total_revisions: int
    total_authors: int
    authors: List[str]
    major_milestones: List[Dict[str, Any]]
    bug_fixes: List[CommitRecord]
    refactors: List[CommitRecord]
    recent_changes: List[CommitRecord]

class EvidenceItem(BaseModel):
    file_path: str
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    commit_hash: Optional[str] = None
    commit_message: Optional[str] = None
    commit_date: Optional[str] = None
    snippet: str
    relevance_reason: str

class RAGAnswerResponse(BaseModel):
    question: str
    answer: str
    evidence: List[EvidenceItem]
    confidence_score: float
    retrieval_sources: Dict[str, int]

class BlastRadiusResult(BaseModel):
    target_file: str
    direct_affected_files: List[str]
    indirect_affected_files: List[str]
    affected_apis: List[str]
    affected_tests: List[str]
    total_impact_count: int
    risk_level: RiskLevel
    risk_score: float # 0.0 to 100.0
    impact_graph: Optional[SoftwareGraph] = None
    explanation: str

class ChangePredictionItem(BaseModel):
    file_path: str
    probability: float # e.g. 0.92 = 92%
    co_change_count: int
    graph_distance: int
    component_type: ComponentType
    reason: str

class ChangeImpactPrediction(BaseModel):
    target_file: str
    predicted_files: List[ChangePredictionItem]
    model_name: str
    feature_importance: Dict[str, float]

class EvaluationMetrics(BaseModel):
    precision: float
    recall: float
    f1_score: float
    tested_samples: int
    details: Optional[Dict[str, Any]] = None

class OverallEvaluation(BaseModel):
    architecture_eval: EvaluationMetrics
    blast_radius_eval: EvaluationMetrics
    commit_count_evaluated: int
    summary: str
