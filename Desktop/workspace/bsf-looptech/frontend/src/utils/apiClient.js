/**
 * API client for waste treatment system backend.
 * Provides async functions for waste records and material types.
 * Falls back to localStorage when API is unavailable.
 */

import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_URL || '/api/waste';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 10000,
  headers: { 'Content-Type': 'application/json' },
});

// Track API availability to avoid repeated failed calls
let apiAvailable = null; // null = unknown, true/false = tested

/**
 * Test if the backend API is reachable.
 * Caches the result for the session.
 */
export const checkApiHealth = async () => {
  if (apiAvailable !== null) return apiAvailable;
  try {
    await axios.get('/health', { timeout: 3000 });
    apiAvailable = true;
  } catch {
    apiAvailable = false;
  }
  return apiAvailable;
};

/** Reset API availability (e.g. after user action). */
export const resetApiStatus = () => { apiAvailable = null; };

/** Returns cached API availability status. */
export const isApiAvailable = () => apiAvailable;


// ═══════════════════════════════════════════
// Waste Records
// ═══════════════════════════════════════════

export const fetchWasteRecords = async (params = {}) => {
  const response = await api.get('/records', { params });
  return response.data;
};

export const fetchWasteRecord = async (id) => {
  const response = await api.get(`/records/${id}`);
  return response.data;
};

export const createWasteRecord = async (data) => {
  const response = await api.post('/records', data);
  return response.data;
};

export const updateWasteRecord = async (id, data) => {
  const response = await api.put(`/records/${id}`, data);
  return response.data;
};

export const deleteWasteRecord = async (id) => {
  const response = await api.delete(`/records/${id}`);
  return response.data;
};


// ═══════════════════════════════════════════
// Material Types
// ═══════════════════════════════════════════

export const fetchMaterialTypes = async (params = {}) => {
  const response = await api.get('/materials', { params });
  return response.data;
};

export const fetchMaterialType = async (id) => {
  const response = await api.get(`/materials/${id}`);
  return response.data;
};

export const createMaterialType = async (data) => {
  const response = await api.post('/materials', data);
  return response.data;
};

export const updateMaterialType = async (id, data) => {
  const response = await api.put(`/materials/${id}`, data);
  return response.data;
};

export const deleteMaterialType = async (id) => {
  const response = await api.delete(`/materials/${id}`);
  return response.data;
};


// ═══════════════════════════════════════════
// AI Recommendation
// ═══════════════════════════════════════════

export const recommendFormulation = async (analysis, wasteType) => {
  const response = await api.post('/recommend', { analysis, wasteType });
  return response.data;
};


// ═══════════════════════════════════════════
// ML Prediction & Model Management
// ═══════════════════════════════════════════

const mlApi = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

/** ML-based formulation prediction with fallback chain. */
export const predictFormulation = async (analysis, wasteType, wasteRecordId = null) => {
  const response = await mlApi.post('/predict/formulation', {
    analysis, waste_type: wasteType, waste_record_id: wasteRecordId,
  });
  return response.data;
};

/** Predict whether a formulation will pass elution tests. */
export const predictElution = async (analysis, formulation) => {
  const response = await mlApi.post('/predict/elution', { analysis, formulation });
  return response.data;
};

/** List all registered ML models. */
export const fetchMLModels = async (modelType = null) => {
  const params = modelType ? { model_type: modelType } : {};
  const response = await mlApi.get('/ml/models', { params });
  return response.data;
};

/** Trigger model retraining. */
export const triggerTraining = async (config = {}) => {
  const response = await mlApi.post('/ml/train', config);
  return response.data;
};

/** Activate a specific model version. */
export const activateModel = async (modelId) => {
  const response = await mlApi.put(`/ml/models/${modelId}/activate`);
  return response.data;
};

/** Get prediction accuracy metrics. */
export const fetchAccuracy = async (days = 30) => {
  const response = await mlApi.get('/ml/accuracy', { params: { days } });
  return response.data;
};

/** Get monthly trend data. */
export const fetchTrends = async (months = 6) => {
  const response = await mlApi.get('/ml/trends', { params: { months } });
  return response.data;
};


// ═══════════════════════════════════════════
// Cost Optimization
// ═══════════════════════════════════════════

/** Find minimum-cost formulation via PuLP optimization. */
export const optimizeFormulation = async (analysis, wasteType, options = {}) => {
  const response = await mlApi.post('/optimize/formulation', {
    analysis,
    waste_type: wasteType,
    waste_weight: options.wasteWeight || 1.0,
    max_budget: options.maxBudget || null,
    target_strength: options.targetStrength || null,
    candidate_solidifiers: options.candidateSolidifiers || null,
    candidate_suppressants: options.candidateSuppressants || null,
  });
  return response.data;
};
