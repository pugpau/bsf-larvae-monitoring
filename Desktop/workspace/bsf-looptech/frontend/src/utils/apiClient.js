/**
 * API client for waste treatment system backend.
 * Provides async functions for waste records and material types.
 * Falls back to localStorage when API is unavailable.
 */

import axios, { createAuthenticatedClient } from './axiosConfig';

const API_BASE = process.env.REACT_APP_API_URL || '/api/waste';

const api = createAuthenticatedClient(API_BASE);

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

const mlApi = createAuthenticatedClient('/api/v1', 30000);

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


// ═══════════════════════════════════════════
// RAG Chat & Knowledge Base
// ═══════════════════════════════════════════

/** Create a new chat session. */
export const createChatSession = async (title = 'New Chat') => {
  const response = await mlApi.post('/chat/sessions', { title });
  return response.data;
};

/** List all chat sessions. */
export const fetchChatSessions = async () => {
  const response = await mlApi.get('/chat/sessions');
  return response.data;
};

/** Get chat session detail with messages. */
export const fetchChatSession = async (sessionId) => {
  const response = await mlApi.get(`/chat/sessions/${sessionId}`);
  return response.data;
};

/** Delete a chat session. */
export const deleteChatSession = async (sessionId) => {
  const response = await mlApi.delete(`/chat/sessions/${sessionId}`);
  return response.data;
};

/** Ask a question via RAG (non-streaming). */
export const askChat = async (sessionId, question) => {
  const response = await mlApi.post('/chat/ask', {
    session_id: sessionId,
    question,
  });
  return response.data;
};

/**
 * Ask a question via RAG with SSE streaming.
 * Returns an EventSource-like reader. Call onChunk for token chunks,
 * onContext for context data, onDone when complete.
 */
export const askChatStream = (sessionId, question, { onChunk, onContext, onDone, onError }) => {
  const url = '/api/v1/chat/ask/stream';
  const body = JSON.stringify({ session_id: sessionId, question });

  const headers = { 'Content-Type': 'application/json' };
  const token = localStorage.getItem('accessToken');
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  fetch(url, {
    method: 'POST',
    headers,
    body,
    credentials: 'include',
  }).then(async (res) => {
    if (!res.ok) {
      onError?.(new Error(`HTTP ${res.status}`));
      return;
    }
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          if (data === '[DONE]') {
            onDone?.();
          } else {
            onChunk?.(data);
          }
        } else if (line.startsWith('event: context')) {
          // Next data line will be context JSON
        } else if (line.startsWith('event: done')) {
          // Next data line will be final JSON
        }
      }
    }
  }).catch((err) => {
    onError?.(err);
  });
};

/** Add knowledge to the knowledge base. */
export const createKnowledge = async (data) => {
  const response = await mlApi.post('/knowledge', data);
  return response.data;
};

/** List knowledge base entries. */
export const fetchKnowledge = async () => {
  const response = await mlApi.get('/knowledge');
  return response.data;
};

/** Seed knowledge base with default BSF domain data. */
export const seedKnowledge = async () => {
  const response = await mlApi.post('/knowledge/seed');
  return response.data;
};


// ═══════════════════════════════════════════
// KPI Dashboard
// ═══════════════════════════════════════════

/** Get realtime KPI metrics. */
export const fetchKPIRealtime = async (days = 7) => {
  const response = await mlApi.get('/kpi/realtime', { params: { days } });
  return response.data;
};

/** Get monthly KPI trend data. */
export const fetchKPITrends = async (months = 6) => {
  const response = await mlApi.get('/kpi/trends', { params: { months } });
  return response.data;
};

/** Get active KPI alerts. */
export const fetchKPIAlerts = async (days = 7) => {
  const response = await mlApi.get('/kpi/alerts', { params: { days } });
  return response.data;
};
