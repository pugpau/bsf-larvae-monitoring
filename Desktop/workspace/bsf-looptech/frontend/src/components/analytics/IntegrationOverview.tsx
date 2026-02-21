/**
 * IntegrationOverview — 統合パイプラインビュー
 * Shows delivery/formulation pipeline status + recent activity at a glance.
 */
import React, { useState, useEffect, useCallback } from 'react';
import {
  Box, Grid, Typography, Chip, CircularProgress,
  List, ListItem, ListItemText, Divider, Stack, Alert,
} from '@mui/material';
import {
  LocalShipping as DeliveryIcon,
  Science as FormulationIcon,
  Inventory as WasteIcon,
  CheckCircle as InfoIcon,
  Warning as WarningIcon,
  Error as CriticalIcon,
} from '@mui/icons-material';
import {
  fetchDashboardOverview,
  type DashboardOverview,
  type RecentActivityItem,
} from '../../api/dashboardApi';

// ── Status display config ──

const DELIVERY_STATUS: Record<string, { label: string; color: 'default' | 'primary' | 'success' | 'error' }> = {
  scheduled: { label: '予定', color: 'primary' },
  delivered: { label: '搬入済', color: 'success' },
  cancelled: { label: '取消', color: 'error' },
};

const FORMULATION_STATUS: Record<string, { label: string; color: 'default' | 'primary' | 'success' | 'warning' | 'error' | 'info' }> = {
  proposed: { label: '提案', color: 'info' },
  accepted: { label: '承認', color: 'primary' },
  applied: { label: '適用', color: 'warning' },
  verified: { label: '検証済', color: 'success' },
  rejected: { label: '却下', color: 'error' },
};

const SEVERITY_ICON: Record<string, React.ReactNode> = {
  info: <InfoIcon fontSize="small" color="primary" />,
  warning: <WarningIcon fontSize="small" color="warning" />,
  critical: <CriticalIcon fontSize="small" color="error" />,
};

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const minutes = Math.floor(diff / 60_000);
  if (minutes < 1) return '今';
  if (minutes < 60) return `${minutes}分前`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}時間前`;
  const days = Math.floor(hours / 24);
  return `${days}日前`;
}

// ── Pipeline card subcomponent ──

interface PipelineCardProps {
  title: string;
  icon: React.ReactNode;
  total: number;
  statuses: Record<string, { label: string; color: 'default' | 'primary' | 'success' | 'warning' | 'error' | 'info' }>;
  counts: Record<string, number>;
}

const PipelineCard: React.FC<PipelineCardProps> = ({ title, icon, total, statuses, counts }) => (
  <Box className="kpi-card" sx={{ p: 2 }}>
    <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1.5 }}>
      {icon}
      <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
        {title}
      </Typography>
      <Typography variant="caption" color="text.secondary">
        ({total}件)
      </Typography>
    </Stack>
    <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
      {Object.entries(statuses).map(([key, cfg]) => {
        const count = counts[key] ?? 0;
        if (count === 0) return null;
        return (
          <Chip
            key={key}
            label={`${cfg.label}: ${count}`}
            size="small"
            color={cfg.color}
            variant="outlined"
            sx={{ fontSize: '0.75rem' }}
          />
        );
      })}
    </Stack>
  </Box>
);

// ── Main component ──

const IntegrationOverview: React.FC = () => {
  const [data, setData] = useState<DashboardOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    try {
      setError('');
      const result = await fetchDashboardOverview();
      setData(result);
    } catch {
      setError('統合ビューの読み込みに失敗しました');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 3 }}>
        <CircularProgress size={28} />
      </Box>
    );
  }

  if (error) {
    return <Alert severity="warning" sx={{ mb: 2 }}>{error}</Alert>;
  }

  if (!data) return null;

  const recentItems = data.recent_activity.slice(0, 5);

  return (
    <Box className="section-panel">
      <Typography className="section-panel__title">統合パイプラインビュー</Typography>

      {/* Pipeline Status Cards */}
      <Grid container spacing={2} sx={{ mb: 2 }}>
        <Grid item xs={12} sm={4}>
          <PipelineCard
            title="搬入予定"
            icon={<DeliveryIcon fontSize="small" color="primary" />}
            total={data.delivery.total}
            statuses={DELIVERY_STATUS}
            counts={data.delivery}
          />
        </Grid>
        <Grid item xs={12} sm={4}>
          <PipelineCard
            title="配合管理"
            icon={<FormulationIcon fontSize="small" color="primary" />}
            total={data.formulation.total}
            statuses={FORMULATION_STATUS}
            counts={data.formulation}
          />
        </Grid>
        <Grid item xs={12} sm={4}>
          <Box className="kpi-card" sx={{ p: 2 }}>
            <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1.5 }}>
              <WasteIcon fontSize="small" color="primary" />
              <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                搬入記録
              </Typography>
              <Typography variant="caption" color="text.secondary">
                ({data.waste.total}件)
              </Typography>
            </Stack>
            <Stack direction="row" spacing={0.5}>
              <Chip
                label={`処理待ち: ${data.waste.pending}`}
                size="small"
                color={data.waste.pending > 0 ? 'warning' : 'default'}
                variant="outlined"
                sx={{ fontSize: '0.75rem' }}
              />
              <Chip
                label={`処理済: ${data.waste.total - data.waste.pending}`}
                size="small"
                color="success"
                variant="outlined"
                sx={{ fontSize: '0.75rem' }}
              />
            </Stack>
          </Box>
        </Grid>
      </Grid>

      {/* Recent Activity */}
      {recentItems.length > 0 && (
        <Box>
          <Typography variant="subtitle2" sx={{ mb: 1, color: 'text.secondary' }}>
            最近のアクティビティ
          </Typography>
          <List dense disablePadding sx={{ bgcolor: 'background.paper', borderRadius: 1 }}>
            {recentItems.map((item: RecentActivityItem, idx: number) => (
              <React.Fragment key={item.id}>
                {idx > 0 && <Divider component="li" />}
                <ListItem sx={{ py: 0.75, px: 1.5 }}>
                  <Box sx={{ mr: 1 }}>
                    {SEVERITY_ICON[item.severity] ?? SEVERITY_ICON.info}
                  </Box>
                  <ListItemText
                    primary={
                      <Typography variant="body2" sx={{ fontSize: '0.8rem' }}>
                        {item.title}
                      </Typography>
                    }
                    secondary={
                      <Typography variant="caption" color="text.disabled">
                        {timeAgo(item.created_at)}
                      </Typography>
                    }
                  />
                </ListItem>
              </React.Fragment>
            ))}
          </List>
        </Box>
      )}
    </Box>
  );
};

export default IntegrationOverview;
