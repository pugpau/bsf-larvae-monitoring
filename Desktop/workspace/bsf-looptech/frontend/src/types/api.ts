/** Shared API response wrapper */
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  meta?: {
    total: number;
    page: number;
    limit: number;
  };
}

/** Paginated response from backend */
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

/** List query parameters */
export interface ListParams {
  q?: string;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  limit?: number;
  offset?: number;
}

/** CSV import result */
export interface ImportResult {
  imported: number;
  skipped: number;
  errors: string[];
}

/** Supplier (搬入先マスタ) */
export interface Supplier {
  id: string;
  name: string;
  contact_person?: string;
  phone?: string;
  email?: string;
  address?: string;
  waste_types: string[];
  notes?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

/** Material (材料マスタ — 拡張版) */
export interface Material {
  id: string;
  name: string;
  category: string;
  description?: string;
  supplier?: string;
  unit_cost?: number;
  unit?: string;
  specific_gravity?: number;
  particle_size?: number;
  ph?: number;
  moisture_content?: number;
  attributes?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

/** Solidification Material (固化材マスタ) */
export interface SolidificationMaterial {
  id: string;
  name: string;
  material_type: 'cement' | 'calcium' | 'ite' | 'other';
  base_material?: string;
  effective_components?: Record<string, number>;
  applicable_soil_types: string[];
  min_addition_rate?: number;
  max_addition_rate?: number;
  unit_cost?: number;
  unit?: string;
  notes?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

/** Leaching Suppressant (溶出抑制剤マスタ) */
export interface LeachingSuppressant {
  id: string;
  name: string;
  suppressant_type: string;
  target_metals: string[];
  min_addition_rate?: number;
  max_addition_rate?: number;
  ph_range_min?: number;
  ph_range_max?: number;
  unit_cost?: number;
  unit?: string;
  notes?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

/** Recipe (配合レシピ) */
export interface Recipe {
  id: string;
  name: string;
  supplier_id?: string;
  waste_type: string;
  target_strength?: number;
  target_elution?: Record<string, number>;
  status: 'draft' | 'active' | 'archived';
  current_version: number;
  details: RecipeDetail[];
  notes?: string;
  created_at: string;
  updated_at: string;
}

/** Recipe Detail (配合明細) */
export interface RecipeDetail {
  id: string;
  recipe_id: string;
  material_id: string;
  material_type: 'solidification' | 'suppressant' | 'other';
  addition_rate: number;
  order_index: number;
  notes?: string;
}

/** Recipe Version List Item (バージョン履歴一覧) */
export interface RecipeVersionListItem {
  id: string;
  version: number;
  change_summary?: string;
  created_by?: string;
  created_at?: string;
}

/** Recipe Version Detail (バージョン明細) */
export interface RecipeVersionDetail {
  id: string;
  version_id: string;
  material_id: string;
  material_type: 'solidification' | 'suppressant' | 'other';
  addition_rate: number;
  order_index: number;
  notes?: string;
}

/** Recipe Version (バージョンスナップショット) */
export interface RecipeVersionResponse {
  id: string;
  recipe_id: string;
  version: number;
  name: string;
  supplier_id?: string;
  waste_type: string;
  target_strength?: number;
  target_elution?: Record<string, number>;
  status: string;
  notes?: string;
  change_summary?: string;
  created_by?: string;
  details: RecipeVersionDetail[];
  created_at?: string;
}

/** Recipe Diff Field (差分フィールド) */
export interface RecipeDiffField {
  field: string;
  old_value: unknown;
  new_value: unknown;
}

/** Recipe Diff Response (バージョン差分) */
export interface RecipeDiffResponse {
  recipe_id: string;
  version_from: number;
  version_to: number;
  header_changes: RecipeDiffField[];
  details_added: RecipeVersionDetail[];
  details_removed: RecipeVersionDetail[];
  details_modified: Array<Record<string, unknown>>;
}

/** Formulation data (配合情報) */
export interface FormulationData {
  solidifierType?: string;
  solidifierAmount?: number;
  solidifierUnit?: string;
  suppressorAmount?: number;
  [key: string]: unknown;
}

/** Elution test result (溶出試験結果) */
export interface ElutionTestResult {
  passed: boolean;
  [metal: string]: number | boolean | undefined;
}

/** Waste Record (搬入記録) */
export interface WasteRecord {
  id: string;
  source: string;
  deliveryDate: string;
  wasteType: string;
  weight?: number;
  weightUnit: string;
  status: 'pending' | 'analyzed' | 'formulated' | 'tested' | 'completed' | 'failed';
  analysis?: Record<string, number | null>;
  formulation?: FormulationData | null;
  elutionResult?: ElutionTestResult | null;
  notes?: string;
  created_at: string;
  updated_at: string;
}

/** Formulation Record source type */
export type FormulationSourceType = 'manual' | 'ml' | 'similarity' | 'rule' | 'optimization' | 'recipe';

/** Formulation Record status */
export type FormulationStatus = 'proposed' | 'accepted' | 'applied' | 'verified' | 'rejected';

/** Formulation Record (配合ワークフローレコード) */
export interface FormulationRecord {
  id: string;
  waste_record_id: string;
  recipe_id?: string;
  recipe_version?: number;
  prediction_id?: string;
  source_type: FormulationSourceType;
  status: FormulationStatus;
  planned_formulation?: FormulationData;
  actual_formulation?: FormulationData;
  elution_result?: Record<string, unknown>;
  elution_passed?: boolean;
  estimated_cost?: number;
  actual_cost?: number;
  confidence?: number;
  reasoning?: string[];
  notes?: string;
  created_by?: string;
  created_at: string;
  updated_at: string;
  // Enriched fields
  waste_type?: string;
  waste_source?: string;
  recipe_name?: string;
}

/** Recommend response */
export interface RecommendResponse {
  candidates: FormulationRecord[];
  waste_record_id: string;
  waste_type?: string;
}

/** Incoming Material (搬入物マスター) */
export interface IncomingMaterial {
  id: string;
  supplier_id: string;
  supplier_name?: string;
  material_category: string;
  name: string;
  description?: string;
  default_weight_unit: string;
  notes?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

/** Delivery Schedule (搬入予定) */
export interface DeliverySchedule {
  id: string;
  incoming_material_id: string;
  supplier_name?: string;
  material_category?: string;
  material_name?: string;
  scheduled_date: string;
  estimated_weight?: number;
  actual_weight?: number;
  weight_unit: string;
  status: 'scheduled' | 'delivered' | 'cancelled';
  waste_record_id?: string;
  notes?: string;
  created_at: string;
  updated_at: string;
}

/** Chat Session (チャットセッション) */
export interface ChatSession {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

/** Context chunk reference from knowledge base */
export interface ContextChunk {
  title: string;
  content: string;
  score: number;
}

/** Chat Message (チャットメッセージ) */
export interface ChatMessage {
  id: string;
  session_id: string;
  role: 'user' | 'assistant';
  content: string;
  context_chunks?: ContextChunk[];
  token_count?: number;
  created_at: string;
}

/** Chat Session with messages (セッション詳細) */
export interface ChatSessionDetail extends ChatSession {
  messages: ChatMessage[];
}

/** Chat API response (RAG回答) */
export interface ChatResponse {
  session_id: string;
  answer: string;
  context: ContextChunk[];
  token_count?: number;
}


// ═══════════════════════════════════════════
// Auth Types
// ═══════════════════════════════════════════

export type UserRole = 'admin' | 'manager' | 'operator' | 'viewer';

export interface UserProfile {
  id: string;
  username: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  permissions?: string[];
}

export interface LoginApiResponse {
  access_token: string;
  token_type: string;
  user: UserProfile;
}

export interface LoginResult {
  success: boolean;
  error?: string;
}

export interface AuthContextValue {
  user: UserProfile | null;
  loading: boolean;
  error: string | null;
  login: (username: string, password: string) => Promise<LoginResult>;
  logout: () => Promise<void>;
  refreshAccessToken: () => Promise<string>;
  hasPermission: (permission: string) => boolean;
  hasRole: (role: string) => boolean;
  isAuthenticated: boolean;
}


// ═══════════════════════════════════════════
// ML Types
// ═══════════════════════════════════════════

export interface MLModel {
  id: string;
  name: string;
  model_type: string;
  version: number;
  training_records: number;
  metrics: Record<string, number>;
  is_active: boolean;
  created_at: string;
}

export interface TrainingResult {
  success: boolean;
  real_records: number;
  synthetic_records: number;
  total_records: number;
  classifier_metrics: Record<string, number>;
  regressor_metrics: Record<string, number>;
  warnings: string[];
}

export interface AccuracyMetrics {
  total_predictions: number;
  ml_predictions: number;
  similarity_predictions: number;
  rule_predictions: number;
  ml_ratio: number;
  avg_confidence: number;
  verified_count: number;
  verified_correct: number;
  accuracy: number;
}

export interface TrendData {
  monthly_predictions?: Array<{
    month: string;
    total: number;
    ml: number;
    similarity: number;
    rule: number;
  }>;
  monthly_accuracy?: Array<{
    month: string;
    accuracy: number;
    total: number;
  }>;
  monthly_waste?: Array<{
    month: string;
    records: number;
    formulated: number;
  }>;
}

export interface FormulationPrediction {
  recommendation: Record<string, unknown>;
  confidence: number;
  method: string;
  reasoning: string[];
  model_version?: number;
  similar_records?: WasteRecord[];
}

export interface ElutionPrediction {
  passed: boolean;
  confidence: number;
  method: string;
  metal_predictions: Record<string, number>;
  reasoning: string[];
}


// ═══════════════════════════════════════════
// Optimization Types
// ═══════════════════════════════════════════

export interface CostItem {
  material_name: string;
  material_type: string;
  amount: number;
  unit: string;
  unit_cost: number;
  total_cost: number;
}

export interface OptimizationResult {
  status: string;
  recommendation: Record<string, unknown>;
  total_cost: number;
  cost_breakdown: CostItem[];
  constraints_satisfied: Record<string, unknown>;
  solver_time_ms: number;
  reasoning: string[];
}

export interface OptimizeOptions {
  wasteWeight?: number;
  maxBudget?: number | null;
  targetStrength?: number | null;
  candidateSolidifiers?: string[] | null;
  candidateSuppressants?: string[] | null;
}


// ═══════════════════════════════════════════
// KPI Types
// ═══════════════════════════════════════════

export interface KPIMetric {
  label: string;
  value: number;
  unit: string;
  trend: number | null;
  status: 'normal' | 'warning' | 'critical';
}

export interface KPIRealtimeData {
  period_days: number;
  processing_volume: KPIMetric;
  formulation_success_rate: KPIMetric;
  material_cost: KPIMetric;
  ml_usage_rate: KPIMetric;
  avg_processing_time: KPIMetric;
  violation_rate: KPIMetric;
  updated_at: string;
}

export interface KPITrendPoint {
  period: string;
  processing_volume: number;
  success_rate: number;
  material_cost: number;
  ml_usage_rate: number;
  avg_processing_time_hours: number;
  violation_rate: number;
}

export interface KPIAlert {
  severity: 'warning' | 'critical';
  metric: string;
  message: string;
  value: number;
  threshold: number;
  record_id?: string;
  created_at: string;
}

export interface KPITrendsResponse {
  data: KPITrendPoint[];
}

export interface KPIAlertsResponse {
  alerts: KPIAlert[];
}


// ═══════════════════════════════════════════
// Chat Streaming Types
// ═══════════════════════════════════════════

export interface ChatStreamCallbacks {
  onChunk?: (data: string) => void;
  onContext?: (data: unknown) => void;
  onDone?: () => void;
  onError?: (error: Error) => void;
}


// ═══════════════════════════════════════════
// Knowledge Types
// ═══════════════════════════════════════════

export interface KnowledgeEntry {
  id: string;
  title: string;
  content: string;
  category?: string;
  created_at: string;
}
