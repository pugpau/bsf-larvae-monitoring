/**
 * API client for incoming materials and delivery schedules (/api/v1/).
 */

import type {
  IncomingMaterial,
  DeliverySchedule,
  PaginatedResponse,
  ListParams,
  ImportResult,
} from '../types/api';
import { createAuthenticatedClient } from '../utils/axiosConfig';

const api = createAuthenticatedClient(
  process.env.REACT_APP_API_V1_URL || '/api/v1',
);

// ── Incoming Materials ──

export interface IncomingMaterialListParams extends ListParams {
  supplier_id?: string;
  material_category?: string;
  is_active?: boolean;
}

export const fetchIncomingMaterials = async (
  params?: IncomingMaterialListParams,
): Promise<PaginatedResponse<IncomingMaterial>> => {
  const { data } = await api.get('/incoming-materials', { params });
  return data;
};

export const fetchIncomingMaterial = async (id: string): Promise<IncomingMaterial> => {
  const { data } = await api.get(`/incoming-materials/${id}`);
  return data;
};

export const createIncomingMaterial = async (
  payload: Partial<IncomingMaterial>,
): Promise<IncomingMaterial> => {
  const { data } = await api.post('/incoming-materials', payload);
  return data;
};

export const updateIncomingMaterial = async (
  id: string,
  payload: Partial<IncomingMaterial>,
): Promise<IncomingMaterial> => {
  const { data } = await api.put(`/incoming-materials/${id}`, payload);
  return data;
};

export const deleteIncomingMaterial = async (id: string): Promise<void> => {
  await api.delete(`/incoming-materials/${id}`);
};

export const exportIncomingMaterialsCsv = async (): Promise<Blob> => {
  const { data } = await api.get('/incoming-materials/export/csv', { responseType: 'blob' });
  return data;
};

export const importIncomingMaterialsCsv = async (file: File): Promise<ImportResult> => {
  const formData = new FormData();
  formData.append('file', file);
  const { data } = await api.post('/incoming-materials/import/csv', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
};

/** Cascading: get distinct categories for a supplier */
export const fetchCategoriesBySupplier = async (supplierId: string): Promise<string[]> => {
  const { data } = await api.get(`/incoming-materials/categories/${supplierId}`);
  return data;
};

/** Cascading: get materials filtered by supplier (+ optional category) */
export const fetchMaterialsBySupplier = async (
  supplierId: string,
  category?: string,
): Promise<IncomingMaterial[]> => {
  const params = category ? { category } : {};
  const { data } = await api.get(`/incoming-materials/by-supplier/${supplierId}`, { params });
  return data;
};

// ── Delivery Schedules ──

export interface DeliveryScheduleListParams extends ListParams {
  status?: string;
  incoming_material_id?: string;
  date_from?: string;
  date_to?: string;
}

export const fetchDeliverySchedules = async (
  params?: DeliveryScheduleListParams,
): Promise<PaginatedResponse<DeliverySchedule>> => {
  const { data } = await api.get('/delivery-schedules', { params });
  return data;
};

export const fetchDeliverySchedule = async (id: string): Promise<DeliverySchedule> => {
  const { data } = await api.get(`/delivery-schedules/${id}`);
  return data;
};

export const createDeliverySchedule = async (
  payload: Record<string, unknown>,
): Promise<DeliverySchedule> => {
  const { data } = await api.post('/delivery-schedules', payload);
  return data;
};

export const updateDeliverySchedule = async (
  id: string,
  payload: Record<string, unknown>,
): Promise<DeliverySchedule> => {
  const { data } = await api.put(`/delivery-schedules/${id}`, payload);
  return data;
};

export const updateDeliveryScheduleStatus = async (
  id: string,
  status: string,
  actualWeight?: number,
): Promise<DeliverySchedule> => {
  const { data } = await api.put(`/delivery-schedules/${id}/status`, {
    status,
    actual_weight: actualWeight,
  });
  return data;
};

export const deleteDeliverySchedule = async (id: string): Promise<void> => {
  await api.delete(`/delivery-schedules/${id}`);
};

export const exportDeliverySchedulesCsv = async (status?: string): Promise<Blob> => {
  const params = status ? { status } : {};
  const { data } = await api.get('/delivery-schedules/export/csv', {
    params,
    responseType: 'blob',
  });
  return data;
};
