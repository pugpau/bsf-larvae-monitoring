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

/** Waste Record (搬入記録) */
export interface WasteRecord {
  id: string;
  source: string;
  deliveryDate: string;
  wasteType: string;
  weight?: number;
  weightUnit: string;
  status: 'pending' | 'analyzed' | 'formulated';
  analysis?: Record<string, number | null>;
  formulation?: Record<string, unknown> | null;
  elutionResult?: Record<string, unknown> | null;
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
