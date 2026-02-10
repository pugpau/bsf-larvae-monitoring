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
