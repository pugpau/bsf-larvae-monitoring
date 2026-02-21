/**
 * 日詳細Drawer — カレンダーの日クリックで表示
 */
import React, { useState, useMemo } from 'react';
import {
  Drawer, Box, Typography, IconButton, Chip, Stack,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Button, Dialog, DialogTitle, DialogContent, DialogActions,
  TextField, Divider,
} from '@mui/material';
import {
  Close as CloseIcon,
  CheckCircle as DeliveredIcon,
  Cancel as CancelIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  ContentCopy as CopyIcon,
} from '@mui/icons-material';
import type { DeliverySchedule } from '../../types/api';
import {
  updateDeliveryScheduleStatus,
  deleteDeliverySchedule,
} from '../../api/deliveryApi';
import { PALETTE, DELIVERY_STATUS_COLORS } from '../../constants/colors';

const STATUS_LABELS: Record<string, { label: string; color: 'default' | 'success' | 'error' }> = {
  scheduled: { label: '予定', color: 'default' },
  delivered: { label: '搬入済', color: 'success' },
  cancelled: { label: 'キャンセル', color: 'error' },
};

interface DeliveryDayDetailDrawerProps {
  open: boolean;
  date: string | null;
  items: DeliverySchedule[];
  onClose: () => void;
  onDataChange: () => void;
  onEdit: (item: DeliverySchedule) => void;
  onCopy: (item: DeliverySchedule) => void;
  onError?: (message: string) => void;
}

const DeliveryDayDetailDrawer: React.FC<DeliveryDayDetailDrawerProps> = ({
  open,
  date,
  items,
  onClose,
  onDataChange,
  onEdit,
  onCopy,
  onError,
}) => {
  const [deliveryDialogOpen, setDeliveryDialogOpen] = useState(false);
  const [deliveryTarget, setDeliveryTarget] = useState<DeliverySchedule | null>(null);
  const [actualWeight, setActualWeight] = useState('');
  const [cancelDialogOpen, setCancelDialogOpen] = useState(false);
  const [cancelTarget, setCancelTarget] = useState<DeliverySchedule | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<DeliverySchedule | null>(null);

  const statusCounts = useMemo(() => {
    const counts = { scheduled: 0, delivered: 0, cancelled: 0 };
    for (const item of items) {
      if (item.status in counts) {
        counts[item.status as keyof typeof counts]++;
      }
    }
    return counts;
  }, [items]);

  const handleDeliverClick = (item: DeliverySchedule) => {
    setDeliveryTarget(item);
    setActualWeight(item.estimated_weight?.toString() || '');
    setDeliveryDialogOpen(true);
  };

  const handleDeliverConfirm = async () => {
    if (!deliveryTarget) return;
    try {
      const weight = actualWeight ? parseFloat(actualWeight) : undefined;
      await updateDeliveryScheduleStatus(deliveryTarget.id, 'delivered', weight);
      setDeliveryDialogOpen(false);
      setDeliveryTarget(null);
      onDataChange();
    } catch {
      onError?.('搬入済への変更に失敗しました');
    }
  };

  const handleCancelClick = (item: DeliverySchedule) => {
    setCancelTarget(item);
    setCancelDialogOpen(true);
  };

  const handleCancelConfirm = async () => {
    if (!cancelTarget) return;
    try {
      await updateDeliveryScheduleStatus(cancelTarget.id, 'cancelled');
      setCancelDialogOpen(false);
      setCancelTarget(null);
      onDataChange();
    } catch {
      onError?.('キャンセルに失敗しました');
    }
  };

  const handleDeleteClick = (item: DeliverySchedule) => {
    setDeleteTarget(item);
    setDeleteDialogOpen(true);
  };

  const handleDeleteConfirm = async () => {
    if (!deleteTarget) return;
    try {
      await deleteDeliverySchedule(deleteTarget.id);
      setDeleteDialogOpen(false);
      setDeleteTarget(null);
      onDataChange();
    } catch {
      onError?.('削除に失敗しました');
    }
  };

  return (
    <>
      <Drawer
        anchor="right"
        open={open}
        onClose={onClose}
        PaperProps={{ sx: { width: { xs: '100%', sm: 600, md: 700 } } }}
      >
        {/* Header */}
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            px: 2,
            py: 1.5,
            borderBottom: `1px solid ${PALETTE.grey[200]}`,
          }}
        >
          <Box>
            <Typography
              variant="h6"
              sx={{
                fontFamily: "'Fira Code', monospace",
                fontWeight: 700,
                fontSize: '1rem',
              }}
            >
              {date || ''}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {items.length}件の搬入予定
            </Typography>
          </Box>
          <IconButton onClick={onClose} aria-label="閉じる">
            <CloseIcon />
          </IconButton>
        </Box>

        {/* Status summary */}
        <Box sx={{ px: 2, py: 1, display: 'flex', gap: 1 }}>
          <Chip
            label={`予定 ${statusCounts.scheduled}`}
            size="small"
            variant="outlined"
            sx={{
              borderColor: DELIVERY_STATUS_COLORS.scheduled,
              color: DELIVERY_STATUS_COLORS.scheduled,
            }}
          />
          <Chip
            label={`搬入済 ${statusCounts.delivered}`}
            size="small"
            variant="outlined"
            sx={{
              borderColor: DELIVERY_STATUS_COLORS.delivered,
              color: DELIVERY_STATUS_COLORS.delivered,
            }}
          />
          <Chip
            label={`キャンセル ${statusCounts.cancelled}`}
            size="small"
            variant="outlined"
            sx={{
              borderColor: DELIVERY_STATUS_COLORS.cancelled,
              color: DELIVERY_STATUS_COLORS.cancelled,
            }}
          />
        </Box>

        <Divider />

        {/* Items table */}
        <TableContainer sx={{ flex: 1 }}>
          <Table size="small" stickyHeader>
            <TableHead>
              <TableRow>
                <TableCell>搬入先</TableCell>
                <TableCell>種類</TableCell>
                <TableCell>名称</TableCell>
                <TableCell align="right">予定重量</TableCell>
                <TableCell align="right">実績重量</TableCell>
                <TableCell align="center">ステータス</TableCell>
                <TableCell align="center">操作</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {items.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} align="center">
                    <Typography variant="body2" color="text.secondary" sx={{ py: 4 }}>
                      この日の搬入予定はありません
                    </Typography>
                  </TableCell>
                </TableRow>
              ) : (
                items.map((item) => {
                  const statusInfo = STATUS_LABELS[item.status] || STATUS_LABELS.scheduled;
                  const isScheduled = item.status === 'scheduled';
                  return (
                    <TableRow key={item.id}>
                      <TableCell sx={{ fontSize: '0.8rem' }}>
                        {item.supplier_name || '-'}
                      </TableCell>
                      <TableCell>
                        <Chip label={item.material_category || '-'} size="small" variant="outlined" />
                      </TableCell>
                      <TableCell sx={{ fontWeight: 500, fontSize: '0.8rem' }}>
                        {item.material_name || '-'}
                      </TableCell>
                      <TableCell
                        align="right"
                        sx={{ fontFamily: "'Fira Code', monospace", fontSize: '0.8rem' }}
                      >
                        {item.estimated_weight != null
                          ? `${item.estimated_weight.toLocaleString()}${item.weight_unit}`
                          : '-'}
                      </TableCell>
                      <TableCell
                        align="right"
                        sx={{ fontFamily: "'Fira Code', monospace", fontSize: '0.8rem' }}
                      >
                        {item.actual_weight != null
                          ? `${item.actual_weight.toLocaleString()}${item.weight_unit}`
                          : '-'}
                      </TableCell>
                      <TableCell align="center">
                        <Chip
                          label={statusInfo.label}
                          size="small"
                          color={statusInfo.color}
                          variant="outlined"
                        />
                      </TableCell>
                      <TableCell align="center">
                        <Stack direction="row" spacing={0} justifyContent="center">
                          <IconButton
                            size="small" color="info" aria-label="コピー"
                            onClick={() => onCopy(item)}
                            title="日付を変えてコピー"
                          >
                            <CopyIcon fontSize="small" />
                          </IconButton>
                          {isScheduled && (
                            <>
                              <IconButton
                                size="small" color="success" aria-label="搬入済"
                                onClick={() => handleDeliverClick(item)}
                                title="搬入済にする"
                              >
                                <DeliveredIcon fontSize="small" />
                              </IconButton>
                              <IconButton
                                size="small" color="warning" aria-label="キャンセル"
                                onClick={() => handleCancelClick(item)}
                                title="キャンセル"
                              >
                                <CancelIcon fontSize="small" />
                              </IconButton>
                              <IconButton
                                size="small" color="primary" aria-label="編集"
                                onClick={() => onEdit(item)}
                              >
                                <EditIcon fontSize="small" />
                              </IconButton>
                              <IconButton
                                size="small" color="error" aria-label="削除"
                                onClick={() => handleDeleteClick(item)}
                              >
                                <DeleteIcon fontSize="small" />
                              </IconButton>
                            </>
                          )}
                        </Stack>
                      </TableCell>
                    </TableRow>
                  );
                })
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </Drawer>

      {/* Delivery confirmation dialog */}
      <Dialog open={deliveryDialogOpen} onClose={() => setDeliveryDialogOpen(false)} maxWidth="xs" fullWidth>
        <DialogTitle>搬入済みにする</DialogTitle>
        <DialogContent>
          <Typography variant="body2" sx={{ mb: 2 }}>
            実績重量を入力してください。搬入記録が自動作成されます。
          </Typography>
          <TextField
            label="実績重量"
            type="number"
            value={actualWeight}
            onChange={(e) => setActualWeight(e.target.value)}
            fullWidth
            size="small"
            inputProps={{ min: 0, step: 0.1 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeliveryDialogOpen(false)}>キャンセル</Button>
          <Button onClick={handleDeliverConfirm} variant="contained" color="success">
            搬入済にする
          </Button>
        </DialogActions>
      </Dialog>

      {/* Cancel confirmation dialog */}
      <Dialog open={cancelDialogOpen} onClose={() => setCancelDialogOpen(false)} maxWidth="xs" fullWidth>
        <DialogTitle>キャンセル確認</DialogTitle>
        <DialogContent>
          <Typography variant="body2">この搬入予定をキャンセルしますか？</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCancelDialogOpen(false)}>戻る</Button>
          <Button onClick={handleCancelConfirm} variant="contained" color="error">
            キャンセルする
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete confirmation dialog */}
      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)} maxWidth="xs" fullWidth>
        <DialogTitle>削除確認</DialogTitle>
        <DialogContent>
          <Typography variant="body2">この搬入予定を削除しますか？この操作は取り消せません。</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)}>キャンセル</Button>
          <Button onClick={handleDeleteConfirm} variant="contained" color="error">
            削除
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

export default DeliveryDayDetailDrawer;
