/**
 * API client for formulation workflow (/api/v1/formulations).
 */

import type {
  FormulationRecord,
  PaginatedResponse,
  RecommendResponse,
} from '../types/api';
import { createAuthenticatedClient } from '../utils/axiosConfig';

const api = createAuthenticatedClient(
  process.env.REACT_APP_API_V1_URL || '/api/v1',
);

// ── List / Get ──

export interface FormulationListParams {
  waste_record_id?: string;
  status?: string;
  source_type?: string;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  limit?: number;
  offset?: number;
}

export const fetchFormulations = async (
  params?: FormulationListParams,
): Promise<PaginatedResponse<FormulationRecord>> => {
  const { data } = await api.get('/formulations', { params });
  return data;
};

export const fetchFormulation = async (id: string): Promise<FormulationRecord> => {
  const { data } = await api.get(`/formulations/${id}`);
  return data;
};

export const fetchFormulationsByWasteRecord = async (
  wasteRecordId: string,
): Promise<{ items: FormulationRecord[]; total: number }> => {
  const { data } = await api.get(`/formulations/by-waste-record/${wasteRecordId}`);
  return data;
};

// ── Export ──

export const exportFormulationsCsv = async (params?: {
  status?: string;
  source_type?: string;
}): Promise<Blob> => {
  const { data } = await api.get('/formulations/export/csv', {
    params,
    responseType: 'blob',
  });
  return data;
};

// ── Create / Update / Delete ──

export interface FormulationCreatePayload {
  waste_record_id: string;
  recipe_id?: string;
  recipe_version?: number;
  source_type?: string;
  planned_formulation?: Record<string, unknown>;
  estimated_cost?: number;
  confidence?: number;
  reasoning?: string[];
  notes?: string;
}

export const createFormulation = async (
  payload: FormulationCreatePayload,
): Promise<FormulationRecord> => {
  const { data } = await api.post('/formulations', payload);
  return data;
};

export const updateFormulation = async (
  id: string,
  payload: Partial<FormulationRecord>,
): Promise<FormulationRecord> => {
  const { data } = await api.put(`/formulations/${id}`, payload);
  return data;
};

export const deleteFormulation = async (id: string): Promise<void> => {
  await api.delete(`/formulations/${id}`);
};

// ── Workflow actions ──

export const recommendFormulations = async (
  wasteRecordId: string,
  topK: number = 3,
): Promise<RecommendResponse> => {
  const { data } = await api.post('/formulations/recommend', {
    waste_record_id: wasteRecordId,
    top_k: topK,
  });
  return data;
};

export const acceptFormulation = async (id: string): Promise<FormulationRecord> => {
  const { data } = await api.post(`/formulations/${id}/accept`);
  return data;
};

export interface ApplyPayload {
  actual_formulation?: Record<string, unknown>;
  actual_cost?: number;
}

export const applyFormulation = async (
  id: string,
  payload?: ApplyPayload,
): Promise<FormulationRecord> => {
  const { data } = await api.post(`/formulations/${id}/apply`, payload ? {
    status: 'applied',
    ...payload,
  } : undefined);
  return data;
};

export interface VerifyPayload {
  elution_result: Record<string, unknown>;
  elution_passed: boolean;
  notes?: string;
}

export const verifyFormulation = async (
  id: string,
  payload: VerifyPayload,
): Promise<FormulationRecord> => {
  const { data } = await api.post(`/formulations/${id}/verify`, {
    status: 'verified',
    ...payload,
  });
  return data;
};

export const rejectFormulation = async (
  id: string,
  notes?: string,
): Promise<FormulationRecord> => {
  const { data } = await api.post(`/formulations/${id}/reject`, notes ? {
    status: 'rejected',
    notes,
  } : undefined);
  return data;
};
