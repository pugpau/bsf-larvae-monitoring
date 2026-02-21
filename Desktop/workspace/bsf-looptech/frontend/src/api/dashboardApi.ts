/**
 * API client for dashboard overview (/api/v1/dashboard).
 */
import { createAuthenticatedClient } from '../utils/axiosConfig';

const api = createAuthenticatedClient(
  process.env.REACT_APP_API_V1_URL || '/api/v1',
);

export interface StatusCounts {
  [key: string]: number;
}

export interface RecentActivityItem {
  id: string;
  event_type: string;
  entity_type: string;
  action: string;
  title: string;
  severity: 'info' | 'warning' | 'critical';
  created_at: string;
}

export interface DashboardOverview {
  delivery: StatusCounts & { total: number };
  formulation: StatusCounts & { total: number };
  waste: { total: number; pending: number };
  recent_activity: RecentActivityItem[];
}

export const fetchDashboardOverview = async (): Promise<DashboardOverview> => {
  const { data } = await api.get('/dashboard/overview');
  return data;
};
