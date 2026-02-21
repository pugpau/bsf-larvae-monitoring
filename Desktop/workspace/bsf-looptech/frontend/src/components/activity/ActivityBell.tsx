/**
 * ActivityBell — notification bell icon with badge + drawer showing recent activity.
 * Polls /api/v1/activity/feed every 30s for new events.
 */
import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Badge, IconButton, Drawer, Box, Typography, List, ListItem, ListItemText,
  Chip, Divider, Button, CircularProgress, Stack,
} from '@mui/material';
import {
  Notifications as BellIcon,
  Close as CloseIcon,
  CheckCircle as InfoIcon,
  Warning as WarningIcon,
  Error as CriticalIcon,
} from '@mui/icons-material';
import { fetchActivityFeed, type ActivityLogItem } from '../../api/activityApi';

const POLL_INTERVAL = 30_000;
const FEED_LIMIT = 20;

const SEVERITY_ICON: Record<string, React.ReactNode> = {
  info: <InfoIcon fontSize="small" color="primary" />,
  warning: <WarningIcon fontSize="small" color="warning" />,
  critical: <CriticalIcon fontSize="small" color="error" />,
};

const SEVERITY_COLOR: Record<string, 'default' | 'primary' | 'warning' | 'error'> = {
  info: 'primary',
  warning: 'warning',
  critical: 'error',
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

const ActivityBell: React.FC = () => {
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<ActivityLogItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [lastSeenCount, setLastSeenCount] = useState(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const load = useCallback(async () => {
    try {
      const result = await fetchActivityFeed({ limit: FEED_LIMIT });
      setItems(result.items);
      setTotal(result.total);
    } catch {
      // silently ignore — activity is non-critical
    }
  }, []);

  // Initial load + polling
  useEffect(() => {
    load();
    intervalRef.current = setInterval(load, POLL_INTERVAL);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [load]);

  const handleOpen = () => {
    setOpen(true);
    setLastSeenCount(total);
  };

  const handleClose = () => {
    setOpen(false);
  };

  const handleRefresh = async () => {
    setLoading(true);
    await load();
    setLoading(false);
    setLastSeenCount(total);
  };

  const badgeCount = Math.max(0, total - lastSeenCount);

  return (
    <>
      <IconButton
        size="small"
        aria-label="アクティビティ"
        onClick={handleOpen}
        sx={{ color: 'text.secondary' }}
      >
        <Badge badgeContent={badgeCount} color="error" max={99}>
          <BellIcon />
        </Badge>
      </IconButton>

      <Drawer
        anchor="right"
        open={open}
        onClose={handleClose}
        PaperProps={{ sx: { width: { xs: '100%', sm: 380 } } }}
      >
        <Box sx={{ p: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h6" sx={{ fontWeight: 600 }}>
            アクティビティ
          </Typography>
          <Stack direction="row" spacing={1}>
            <Button size="small" onClick={handleRefresh} disabled={loading}>
              {loading ? <CircularProgress size={16} /> : '更新'}
            </Button>
            <IconButton size="small" onClick={handleClose}>
              <CloseIcon />
            </IconButton>
          </Stack>
        </Box>

        <Divider />

        {items.length === 0 ? (
          <Box sx={{ p: 4, textAlign: 'center' }}>
            <Typography color="text.secondary">
              アクティビティはありません
            </Typography>
          </Box>
        ) : (
          <List dense disablePadding>
            {items.map((item) => (
              <React.Fragment key={item.id}>
                <ListItem sx={{ py: 1.5, px: 2, alignItems: 'flex-start' }}>
                  <Box sx={{ mr: 1.5, mt: 0.5 }}>
                    {SEVERITY_ICON[item.severity] ?? SEVERITY_ICON.info}
                  </Box>
                  <ListItemText
                    primary={
                      <Stack direction="row" spacing={1} alignItems="center">
                        <Typography variant="body2" sx={{ fontWeight: 500 }}>
                          {item.title}
                        </Typography>
                        <Chip
                          label={item.entity_type}
                          size="small"
                          variant="outlined"
                          color={SEVERITY_COLOR[item.severity] ?? 'default'}
                          sx={{ height: 20, fontSize: '0.7rem' }}
                        />
                      </Stack>
                    }
                    secondary={
                      <Box>
                        {item.description && (
                          <Typography variant="caption" display="block" color="text.secondary">
                            {item.description}
                          </Typography>
                        )}
                        <Typography variant="caption" color="text.disabled">
                          {timeAgo(item.created_at)}
                        </Typography>
                      </Box>
                    }
                  />
                </ListItem>
                <Divider component="li" />
              </React.Fragment>
            ))}
          </List>
        )}

        {total > FEED_LIMIT && (
          <Box sx={{ p: 2, textAlign: 'center' }}>
            <Typography variant="caption" color="text.secondary">
              全{total}件中 最新{FEED_LIMIT}件を表示
            </Typography>
          </Box>
        )}
      </Drawer>
    </>
  );
};

export default ActivityBell;
