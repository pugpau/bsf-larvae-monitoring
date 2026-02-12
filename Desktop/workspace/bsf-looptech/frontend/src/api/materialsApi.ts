/**
 * API client for Phase 1/2 materials endpoints (/api/v1/).
 * Suppliers, solidification materials, leaching suppressants, recipes.
 * Phase 2: Paginated responses, CSV export/import.
 */

import type {
  Supplier,
  SolidificationMaterial,
  LeachingSuppressant,
  Recipe,
  PaginatedResponse,
  ListParams,
  ImportResult,
} from '../types/api';
import { createAuthenticatedClient } from '../utils/axiosConfig';

const api = createAuthenticatedClient(
  process.env.REACT_APP_API_V1_URL || '/api/v1',
);


// ── Suppliers ──

export const fetchSuppliers = async (
  params?: ListParams & { is_active?: boolean }
): Promise<PaginatedResponse<Supplier>> => {
  const { data } = await api.get('/suppliers', { params });
  return data;
};

export const fetchSupplier = async (id: string): Promise<Supplier> => {
  const { data } = await api.get(`/suppliers/${id}`);
  return data;
};

export const createSupplier = async (payload: Partial<Supplier>): Promise<Supplier> => {
  const { data } = await api.post('/suppliers', payload);
  return data;
};

export const updateSupplier = async (id: string, payload: Partial<Supplier>): Promise<Supplier> => {
  const { data } = await api.put(`/suppliers/${id}`, payload);
  return data;
};

export const deleteSupplier = async (id: string): Promise<void> => {
  await api.delete(`/suppliers/${id}`);
};

export const exportSuppliersCsv = async (): Promise<Blob> => {
  const { data } = await api.get('/suppliers/export/csv', { responseType: 'blob' });
  return data;
};

export const importSuppliersCsv = async (file: File): Promise<ImportResult> => {
  const formData = new FormData();
  formData.append('file', file);
  const { data } = await api.post('/suppliers/import/csv', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
};


// ── Solidification Materials ──

export const fetchSolidificationMaterials = async (
  params?: ListParams & { material_type?: string; is_active?: boolean }
): Promise<PaginatedResponse<SolidificationMaterial>> => {
  const { data } = await api.get('/solidification-materials', { params });
  return data;
};

export const createSolidificationMaterial = async (
  payload: Partial<SolidificationMaterial>
): Promise<SolidificationMaterial> => {
  const { data } = await api.post('/solidification-materials', payload);
  return data;
};

export const updateSolidificationMaterial = async (
  id: string,
  payload: Partial<SolidificationMaterial>
): Promise<SolidificationMaterial> => {
  const { data } = await api.put(`/solidification-materials/${id}`, payload);
  return data;
};

export const deleteSolidificationMaterial = async (id: string): Promise<void> => {
  await api.delete(`/solidification-materials/${id}`);
};

export const exportSolidificationMaterialsCsv = async (): Promise<Blob> => {
  const { data } = await api.get('/solidification-materials/export/csv', { responseType: 'blob' });
  return data;
};

export const importSolidificationMaterialsCsv = async (file: File): Promise<ImportResult> => {
  const formData = new FormData();
  formData.append('file', file);
  const { data } = await api.post('/solidification-materials/import/csv', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
};


// ── Leaching Suppressants ──

export const fetchLeachingSuppressants = async (
  params?: ListParams & { suppressant_type?: string; is_active?: boolean }
): Promise<PaginatedResponse<LeachingSuppressant>> => {
  const { data } = await api.get('/leaching-suppressants', { params });
  return data;
};

export const createLeachingSuppressant = async (
  payload: Partial<LeachingSuppressant>
): Promise<LeachingSuppressant> => {
  const { data } = await api.post('/leaching-suppressants', payload);
  return data;
};

export const updateLeachingSuppressant = async (
  id: string,
  payload: Partial<LeachingSuppressant>
): Promise<LeachingSuppressant> => {
  const { data } = await api.put(`/leaching-suppressants/${id}`, payload);
  return data;
};

export const deleteLeachingSuppressant = async (id: string): Promise<void> => {
  await api.delete(`/leaching-suppressants/${id}`);
};

export const exportLeachingSuppressantsCsv = async (): Promise<Blob> => {
  const { data } = await api.get('/leaching-suppressants/export/csv', { responseType: 'blob' });
  return data;
};

export const importLeachingSuppressantsCsv = async (file: File): Promise<ImportResult> => {
  const formData = new FormData();
  formData.append('file', file);
  const { data } = await api.post('/leaching-suppressants/import/csv', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
};


// ── Recipes ──

export const fetchRecipes = async (
  params?: ListParams & { waste_type?: string; status?: string }
): Promise<PaginatedResponse<Recipe>> => {
  const { data } = await api.get('/recipes', { params });
  return data;
};

export const fetchRecipe = async (id: string): Promise<Recipe> => {
  const { data } = await api.get(`/recipes/${id}`);
  return data;
};

export const createRecipe = async (payload: {
  name: string;
  waste_type: string;
  supplier_id?: string;
  target_strength?: number;
  target_elution?: Record<string, number>;
  status?: string;
  notes?: string;
  details?: Array<{
    material_id: string;
    material_type: string;
    addition_rate: number;
    order_index?: number;
    notes?: string;
  }>;
}): Promise<Recipe> => {
  const { data } = await api.post('/recipes', payload);
  return data;
};

export const updateRecipe = async (id: string, payload: Partial<Recipe>): Promise<Recipe> => {
  const { data } = await api.put(`/recipes/${id}`, payload);
  return data;
};

export const deleteRecipe = async (id: string): Promise<void> => {
  await api.delete(`/recipes/${id}`);
};

export const addRecipeDetail = async (
  recipeId: string,
  detail: {
    material_id: string;
    material_type: string;
    addition_rate: number;
    order_index?: number;
    notes?: string;
  }
): Promise<Recipe> => {
  const { data } = await api.post(`/recipes/${recipeId}/details`, detail);
  return data;
};

export const removeRecipeDetail = async (recipeId: string, detailId: string): Promise<void> => {
  await api.delete(`/recipes/${recipeId}/details/${detailId}`);
};

export const exportRecipesCsv = async (): Promise<Blob> => {
  const { data } = await api.get('/recipes/export/csv', { responseType: 'blob' });
  return data;
};


// ── Utility ──

export const downloadBlob = (blob: Blob, filename: string): void => {
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  window.URL.revokeObjectURL(url);
};
