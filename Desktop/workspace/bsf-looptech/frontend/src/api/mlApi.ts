/**
 * ML Prediction, Model Management & Cost Optimization API
 */
import { createAuthenticatedClient } from '../utils/axiosConfig';
import type {
  FormulationPrediction, ElutionPrediction, MLModel,
  TrainingResult, AccuracyMetrics, TrendData, OptimizationResult,
  OptimizeOptions,
} from '../types/api';

const mlApi = createAuthenticatedClient('/api/v1', 30000);

/** ML-based formulation prediction with fallback chain. */
export const predictFormulation = async (
  analysis: Record<string, number | null>,
  wasteType: string,
  wasteRecordId: string | null = null
): Promise<FormulationPrediction> => {
  const response = await mlApi.post('/predict/formulation', {
    analysis, waste_type: wasteType, waste_record_id: wasteRecordId,
  });
  return response.data;
};

/** Predict whether a formulation will pass elution tests. */
export const predictElution = async (
  analysis: Record<string, number | null>,
  formulation: Record<string, unknown>
): Promise<ElutionPrediction> => {
  const response = await mlApi.post('/predict/elution', { analysis, formulation });
  return response.data;
};

/** List all registered ML models. */
export const fetchMLModels = async (modelType: string | null = null): Promise<MLModel[]> => {
  const params = modelType ? { model_type: modelType } : {};
  const response = await mlApi.get('/ml/models', { params });
  return response.data;
};

/** Trigger model retraining. */
export const triggerTraining = async (config: Record<string, unknown> = {}): Promise<TrainingResult> => {
  const response = await mlApi.post('/ml/train', config);
  return response.data;
};

/** Activate a specific model version. */
export const activateModel = async (modelId: string): Promise<MLModel> => {
  const response = await mlApi.put(`/ml/models/${modelId}/activate`);
  return response.data;
};

/** Get prediction accuracy metrics. */
export const fetchAccuracy = async (days = 30): Promise<AccuracyMetrics> => {
  const response = await mlApi.get('/ml/accuracy', { params: { days } });
  return response.data;
};

/** Get monthly trend data. */
export const fetchTrends = async (months = 6): Promise<TrendData> => {
  const response = await mlApi.get('/ml/trends', { params: { months } });
  return response.data;
};

/** Find minimum-cost formulation via PuLP optimization. */
export const optimizeFormulation = async (
  analysis: Record<string, number | null>,
  wasteType: string,
  options: OptimizeOptions = {}
): Promise<OptimizationResult> => {
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
