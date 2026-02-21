/**
 * KPI Dashboard API
 */
import { createAuthenticatedClient } from '../utils/axiosConfig';
import type { KPIRealtimeData, KPITrendsResponse, KPIAlertsResponse } from '../types/api';

const kpiClient = createAuthenticatedClient('/api/v1', 30000);

/** Get realtime KPI metrics. */
export const fetchKPIRealtime = async (days = 7): Promise<KPIRealtimeData> => {
  const response = await kpiClient.get('/kpi/realtime', { params: { days } });
  return response.data;
};

/** Get monthly KPI trend data. */
export const fetchKPITrends = async (months = 6): Promise<KPITrendsResponse> => {
  const response = await kpiClient.get('/kpi/trends', { params: { months } });
  return response.data;
};

/** Get active KPI alerts. */
export const fetchKPIAlerts = async (days = 7): Promise<KPIAlertsResponse> => {
  const response = await kpiClient.get('/kpi/alerts', { params: { days } });
  return response.data;
};
