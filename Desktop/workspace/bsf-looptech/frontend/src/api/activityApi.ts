/**
 * Activity feed API client.
 */
import { createAuthenticatedClient } from '../utils/axiosConfig';

const client = createAuthenticatedClient('/api/v1');

export interface ActivityLogItem {
  id: string;
  event_type: string;
  entity_type: string;
  entity_id: string | null;
  user_id: string | null;
  action: string;
  title: string;
  description: string | null;
  severity: 'info' | 'warning' | 'critical';
  metadata_json: Record<string, unknown> | null;
  created_at: string;
}

export interface ActivityFeedResponse {
  items: ActivityLogItem[];
  total: number;
  limit: number;
  offset: number;
}

export async function fetchActivityFeed(params?: {
  limit?: number;
  offset?: number;
  event_type?: string;
  entity_type?: string;
  severity?: string;
}): Promise<ActivityFeedResponse> {
  const res = await client.get<ActivityFeedResponse>('/activity/feed', { params });
  return res.data;
}

export async function fetchEntityActivity(
  entityType: string,
  entityId: string,
  limit?: number,
): Promise<{ items: ActivityLogItem[]; total: number }> {
  const res = await client.get<{ items: ActivityLogItem[]; total: number }>(
    `/activity/${entityType}/${entityId}`,
    { params: { limit } },
  );
  return res.data;
}
