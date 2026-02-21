/**
 * API client for waste record endpoints (/api/waste/).
 * CRUD, search, pagination, CSV export/import.
 */

import type {
  WasteRecord,
  PaginatedResponse,
  ImportResult,
} from '../types/api';
import { createAuthenticatedClient } from '../utils/axiosConfig';

const api = createAuthenticatedClient(
  process.env.REACT_APP_API_URL
    ? `${process.env.REACT_APP_API_URL}/api/waste`
    : '/api/waste',
);

export interface WasteListParams {
  q?: string;
  status?: string;
  wasteType?: string;
  source?: string;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  limit?: number;
  offset?: number;
}

export const fetchWasteRecords = async (
  params?: WasteListParams,
): Promise<PaginatedResponse<WasteRecord>> => {
  const { data } = await api.get('/records', { params });
  return data;
};

export const fetchWasteRecord = async (id: string): Promise<WasteRecord> => {
  const { data } = await api.get(`/records/${id}`);
  return data;
};

export const createWasteRecord = async (
  payload: Partial<WasteRecord>,
): Promise<WasteRecord> => {
  const { data } = await api.post('/records', payload);
  return data;
};

export const updateWasteRecord = async (
  id: string,
  payload: Partial<WasteRecord>,
): Promise<WasteRecord> => {
  const { data } = await api.put(`/records/${id}`, payload);
  return data;
};

export const deleteWasteRecord = async (id: string): Promise<void> => {
  await api.delete(`/records/${id}`);
};

export const exportWasteRecordsCsv = async (): Promise<Blob> => {
  const { data } = await api.get('/records/export/csv', { responseType: 'blob' });
  return data;
};

export const importWasteRecordsCsv = async (file: File): Promise<ImportResult> => {
  const formData = new FormData();
  formData.append('file', file);
  const { data } = await api.post('/records/import/csv', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
};
