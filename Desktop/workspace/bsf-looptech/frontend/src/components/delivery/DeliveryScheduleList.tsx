import React, { useState, useMemo, useCallback, useEffect } from 'react';
import {
  Box, Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Paper, IconButton, Button, Chip, Stack,
  Dialog, DialogActions, DialogContent, DialogTitle, TextField, Typography,
  Toolbar, ToggleButtonGroup, ToggleButton,
} from '@mui/material';
import {
  Add as AddIcon, Edit as EditIcon, Delete as DeleteIcon,
  CheckCircle as DeliveredIcon, Cancel as CancelIcon,
  ContentCopy as CopyIcon, FileDownload as ExportIcon,
  ChevronLeft as PrevIcon, ChevronRight as NextIcon,
  Today as TodayIcon,
  ViewList as TableViewIcon,
  CalendarMonth as MonthIcon,
  ViewWeek as WeekIcon,
  Science as FormulationIcon,
} from '@mui/icons-material';
import {
  fetchDeliverySchedules, deleteDeliverySchedule,
  updateDeliveryScheduleStatus, exportDeliverySchedulesCsv,
} from '../../api/deliveryApi';
import { downloadBlob } from '../../api/materialsApi';
import type { DeliverySchedule } from '../../types/api';
import { useNotification } from '../../hooks/useNotification';
import { useDeliveryCalendar } from '../../hooks/useDeliveryCalendar';
import NotificationSnackbar from '../common/NotificationSnackbar';
import TableSkeleton from '../common/TableSkeleton';
import EmptyState from '../common/EmptyState';
import JaTablePagination from '../common/JaTablePagination';
import DeliveryScheduleForm from './DeliveryScheduleForm';
import DeliveryWeekView from './DeliveryWeekView';
import DeliveryMonthView from './DeliveryMonthView';
import ConfirmDeleteDialog from '../common/ConfirmDeleteDialog';
import DeliveryDayDetailDrawer from './DeliveryDayDetailDrawer';
import { formatPeriodLabel } from '../../utils/dateUtils';
import type { CalendarPeriod } from '../../utils/dateUtils';
import { DELIVERY_STATUS_COLORS } from '../../constants/colors';
import { DATA_CELL_SMALL_SX } from '../../styles/dataCell';

type ViewMode = 'table' | '1week' | '2weeks' | '1month';

const STATUS_LABELS: Record<string, { label: string; color: 'default' | 'success' | 'error' }> = {
  scheduled: { label: '予定', color: 'default' },
  delivered: { label: '搬入済', color: 'success' },
  cancelled: { label: 'キャンセル', color: 'error' },
};

const STORAGE_KEY = 'bsf-looptech:delivery_view_mode';

function getInitialViewMode(): ViewMode {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored && ['table', '1week', '2weeks', '1month'].includes(stored)) {
      return stored as ViewMode;
    }
  } catch { /* ignore */ }
  return 'table';
}

interface DeliveryScheduleListProps {
  onStartFormulation?: (wasteRecordId: string) => void;
}

const DeliveryScheduleList: React.FC<DeliveryScheduleListProps> = ({ onStartFormulation }) => {
  const [viewMode, setViewMode] = useState<ViewMode>(getInitialViewMode);

  // ── Table view state ──
  const [items, setItems] = useState<DeliverySchedule[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);
  const [showForm, setShowForm] = useState(false);
  const [editingItem, setEditingItem] = useState<DeliverySchedule | null>(null);
  const [copyMode, setCopyMode] = useState(false);
  const { notification, notify, closeNotification } = useNotification();

  // ── Table dialogs ──
  const [deliveryDialogOpen, setDeliveryDialogOpen] = useState(false);
  const [deliveryTarget, setDeliveryTarget] = useState<DeliverySchedule | null>(null);
  const [actualWeight, setActualWeight] = useState('');
  const [cancelDialogOpen, setCancelDialogOpen] = useState(false);
  const [cancelTarget, setCancelTarget] = useState<DeliverySchedule | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<DeliverySchedule | null>(null);

  // ── Calendar state ──
  const calendar = useDeliveryCalendar();

  const isCalendarMode = viewMode !== 'table';

  // Sync calendar period with viewMode
  useEffect(() => {
    if (isCalendarMode) {
      calendar.setPeriod(viewMode as CalendarPeriod);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [viewMode, isCalendarMode]);

  // ── Table data loading ──
  const loadTable = useCallback(async () => {
    setLoading(true);
    try {
      const result = await fetchDeliverySchedules({
        limit: rowsPerPage,
        offset: page * rowsPerPage,
        sort_by: 'scheduled_date',
        sort_order: 'desc',
      });
      setItems(result.items);
      setTotal(result.total);
    } catch {
      notify('搬入予定の読み込みに失敗しました', 'error');
    } finally {
      setLoading(false);
    }
  }, [page, rowsPerPage, notify]);

  useEffect(() => {
    if (!isCalendarMode) loadTable();
  }, [loadTable, isCalendarMode]);

  // ── View mode change ──
  const handleViewModeChange = (_: React.MouseEvent<HTMLElement>, value: ViewMode | null) => {
    if (!value) return;
    setViewMode(value);
    try {
      localStorage.setItem(STORAGE_KEY, value);
    } catch { /* ignore */ }
  };

  // ── Form handlers ──
  const handleNew = () => {
    setEditingItem(null);
    setCopyMode(false);
    setShowForm(true);
  };

  const handleEdit = (item: DeliverySchedule) => {
    setEditingItem(item);
    setCopyMode(false);
    setShowForm(true);
  };

  const handleCopy = (item: DeliverySchedule) => {
    setEditingItem(item);
    setCopyMode(true);
    setShowForm(true);
  };

  const handleFormSuccess = () => {
    setShowForm(false);
    setEditingItem(null);
    setCopyMode(false);
    if (isCalendarMode) {
      calendar.reload();
    } else {
      loadTable();
    }
  };

  const handleFormCancel = () => {
    setShowForm(false);
    setEditingItem(null);
    setCopyMode(false);
  };

  // ── Table action handlers ──
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
      notify('搬入済みに更新しました（搬入記録を自動作成）');
      setDeliveryDialogOpen(false);
      setDeliveryTarget(null);
      loadTable();
    } catch {
      notify('ステータス更新に失敗しました', 'error');
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
      notify('キャンセルしました');
      setCancelDialogOpen(false);
      setCancelTarget(null);
      loadTable();
    } catch {
      notify('キャンセルに失敗しました', 'error');
    }
  };

  const handleDeleteConfirm = async () => {
    if (!deleteTarget) return;
    try {
      await deleteDeliverySchedule(deleteTarget.id);
      notify('削除しました');
      setDeleteTarget(null);
      loadTable();
    } catch {
      notify('削除に失敗しました', 'error');
    }
  };

  const handleExport = async () => {
    try {
      const blob = await exportDeliverySchedulesCsv();
      downloadBlob(blob, 'delivery_schedules.csv');
      notify('CSVをエクスポートしました');
    } catch {
      notify('エクスポートに失敗しました', 'error');
    }
  };

  // ── Calendar day click ──
  const handleDayClick = (dateISO: string) => {
    calendar.setSelectedDate(dateISO);
  };

  const handleDrawerDataChange = () => {
    calendar.reload();
    notify('更新しました');
  };

  // ── Status filter counts ──
  const calendarStatusCounts = useMemo(() => {
    const counts = { total: 0, scheduled: 0, delivered: 0, cancelled: 0 };
    for (const item of calendar.items) {
      counts.total++;
      const s = item.status as keyof typeof counts;
      if (s in counts) {
        counts[s]++;
      }
    }
    return counts;
  }, [calendar.items]);

  const colSpan = 9;

  if (showForm) {
    return (
      <DeliveryScheduleForm
        initialData={editingItem}
        copyMode={copyMode}
        onSubmitSuccess={handleFormSuccess}
        onCancel={handleFormCancel}
      />
    );
  }

  return (
    <Box>
      {/* ── Toolbar ── */}
      <Toolbar disableGutters sx={{ gap: 1, flexWrap: 'wrap', mb: 1 }}>
        <Typography variant="h6" sx={{ fontWeight: 600, fontSize: '1rem', mr: 1 }}>
          搬入予定
        </Typography>

        <ToggleButtonGroup
          value={viewMode}
          exclusive
          onChange={handleViewModeChange}
          size="small"
          sx={{ mr: 'auto' }}
        >
          <ToggleButton value="table" aria-label="テーブル">
            <TableViewIcon fontSize="small" sx={{ mr: 0.5 }} />
            <Typography variant="caption" sx={{ fontSize: '0.7rem' }}>テーブル</Typography>
          </ToggleButton>
          <ToggleButton value="1week" aria-label="週間">
            <WeekIcon fontSize="small" sx={{ mr: 0.5 }} />
            <Typography variant="caption" sx={{ fontSize: '0.7rem' }}>週間</Typography>
          </ToggleButton>
          <ToggleButton value="2weeks" aria-label="2週間">
            <WeekIcon fontSize="small" sx={{ mr: 0.5 }} />
            <Typography variant="caption" sx={{ fontSize: '0.7rem' }}>2週間</Typography>
          </ToggleButton>
          <ToggleButton value="1month" aria-label="月間">
            <MonthIcon fontSize="small" sx={{ mr: 0.5 }} />
            <Typography variant="caption" sx={{ fontSize: '0.7rem' }}>月間</Typography>
          </ToggleButton>
        </ToggleButtonGroup>

        <Button size="small" variant="outlined" startIcon={<ExportIcon />} onClick={handleExport}>
          CSV出力
        </Button>
        <Button size="small" variant="contained" startIcon={<AddIcon />} onClick={handleNew}>
          新規登録
        </Button>
      </Toolbar>

      {/* ── Calendar navigation ── */}
      {isCalendarMode && (
        <Box sx={{ mb: 1 }}>
          <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
            <IconButton size="small" onClick={calendar.navigatePrev} aria-label="前の期間">
              <PrevIcon />
            </IconButton>
            <Typography
              variant="subtitle2"
              sx={{
                fontFamily: "'Fira Code', monospace",
                fontSize: '0.85rem',
                fontWeight: 600,
                minWidth: 200,
                textAlign: 'center',
              }}
            >
              {formatPeriodLabel(calendar.dateRange, calendar.period)}
            </Typography>
            <IconButton size="small" onClick={calendar.navigateNext} aria-label="次の期間">
              <NextIcon />
            </IconButton>
            <Button
              size="small"
              variant="outlined"
              startIcon={<TodayIcon />}
              onClick={calendar.navigateToday}
              sx={{ ml: 1 }}
            >
              今日
            </Button>

            {/* Status filter chips */}
            <Box sx={{ ml: 'auto', display: 'flex', gap: 0.5 }}>
              <Chip
                label={`全て (${calendarStatusCounts.total})`}
                size="small"
                variant={calendar.statusFilter === null ? 'filled' : 'outlined'}
                onClick={() => calendar.setStatusFilter(null)}
                sx={{ cursor: 'pointer' }}
              />
              <Chip
                label={`予定 (${calendarStatusCounts.scheduled})`}
                size="small"
                variant={calendar.statusFilter === 'scheduled' ? 'filled' : 'outlined'}
                onClick={() => calendar.setStatusFilter('scheduled')}
                sx={{
                  cursor: 'pointer',
                  borderColor: DELIVERY_STATUS_COLORS.scheduled,
                  ...(calendar.statusFilter === 'scheduled' && {
                    bgcolor: DELIVERY_STATUS_COLORS.scheduled,
                    color: '#fff',
                  }),
                }}
              />
              <Chip
                label={`搬入済 (${calendarStatusCounts.delivered})`}
                size="small"
                variant={calendar.statusFilter === 'delivered' ? 'filled' : 'outlined'}
                onClick={() => calendar.setStatusFilter('delivered')}
                sx={{
                  cursor: 'pointer',
                  borderColor: DELIVERY_STATUS_COLORS.delivered,
                  ...(calendar.statusFilter === 'delivered' && {
                    bgcolor: DELIVERY_STATUS_COLORS.delivered,
                    color: '#fff',
                  }),
                }}
              />
              <Chip
                label={`キャンセル (${calendarStatusCounts.cancelled})`}
                size="small"
                variant={calendar.statusFilter === 'cancelled' ? 'filled' : 'outlined'}
                onClick={() => calendar.setStatusFilter('cancelled')}
                sx={{
                  cursor: 'pointer',
                  borderColor: DELIVERY_STATUS_COLORS.cancelled,
                  ...(calendar.statusFilter === 'cancelled' && {
                    bgcolor: DELIVERY_STATUS_COLORS.cancelled,
                    color: '#fff',
                  }),
                }}
              />
            </Box>
          </Stack>
        </Box>
      )}

      {/* ── Table view ── */}
      {!isCalendarMode && (
        <TableContainer component={Paper} variant="outlined">
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>予定日</TableCell>
                <TableCell>搬入先</TableCell>
                <TableCell>種類</TableCell>
                <TableCell>名称</TableCell>
                <TableCell align="right">予定重量</TableCell>
                <TableCell align="right">実績重量</TableCell>
                <TableCell>単位</TableCell>
                <TableCell align="center">ステータス</TableCell>
                <TableCell align="center">操作</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {loading ? (
                <TableSkeleton columns={colSpan} />
              ) : items.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={colSpan}>
                    <EmptyState title="搬入予定が登録されていません" />
                  </TableCell>
                </TableRow>
              ) : (
                items.map((item) => {
                  const statusInfo = STATUS_LABELS[item.status] || STATUS_LABELS.scheduled;
                  const isScheduled = item.status === 'scheduled';
                  return (
                    <TableRow key={item.id}>
                      <TableCell sx={DATA_CELL_SMALL_SX}>
                        {item.scheduled_date}
                      </TableCell>
                      <TableCell>{item.supplier_name || '-'}</TableCell>
                      <TableCell>
                        <Chip label={item.material_category || '-'} size="small" variant="outlined" />
                      </TableCell>
                      <TableCell sx={{ fontWeight: 500 }}>{item.material_name || '-'}</TableCell>
                      <TableCell align="right" sx={DATA_CELL_SMALL_SX}>
                        {item.estimated_weight != null ? item.estimated_weight.toLocaleString() : '-'}
                      </TableCell>
                      <TableCell align="right" sx={DATA_CELL_SMALL_SX}>
                        {item.actual_weight != null ? item.actual_weight.toLocaleString() : '-'}
                      </TableCell>
                      <TableCell sx={DATA_CELL_SMALL_SX}>
                        {item.weight_unit}
                      </TableCell>
                      <TableCell align="center">
                        <Chip label={statusInfo.label} size="small" color={statusInfo.color} variant="outlined" />
                      </TableCell>
                      <TableCell align="center">
                        <Stack direction="row" spacing={0} justifyContent="center">
                          {item.status === 'delivered' && item.waste_record_id && onStartFormulation && (
                            <IconButton
                              size="small"
                              color="primary"
                              aria-label="配合開始"
                              onClick={() => onStartFormulation(item.waste_record_id!)}
                              title="配合管理タブで配合を開始"
                            >
                              <FormulationIcon fontSize="small" />
                            </IconButton>
                          )}
                          <IconButton size="small" color="info" aria-label="コピー" onClick={() => handleCopy(item)} title="日付を変えてコピー">
                            <CopyIcon fontSize="small" />
                          </IconButton>
                          {isScheduled && (
                            <>
                              <IconButton size="small" color="success" aria-label="搬入済" onClick={() => handleDeliverClick(item)} title="搬入済にする">
                                <DeliveredIcon fontSize="small" />
                              </IconButton>
                              <IconButton size="small" color="warning" aria-label="キャンセル" onClick={() => handleCancelClick(item)} title="キャンセル">
                                <CancelIcon fontSize="small" />
                              </IconButton>
                              <IconButton size="small" color="primary" aria-label="編集" onClick={() => handleEdit(item)}>
                                <EditIcon fontSize="small" />
                              </IconButton>
                              <IconButton size="small" color="error" aria-label="削除" onClick={() => setDeleteTarget(item)}>
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
          <JaTablePagination
            count={total} page={page}
            onPageChange={(_, p) => setPage(p)}
            rowsPerPage={rowsPerPage}
            onRowsPerPageChange={(e) => { setRowsPerPage(parseInt(e.target.value, 10)); setPage(0); }}
          />
        </TableContainer>
      )}

      {/* ── Calendar views ── */}
      {viewMode === '1week' && (
        <DeliveryWeekView
          period="1week"
          dateRange={calendar.dateRange}
          itemsByDate={calendar.itemsByDate}
          loading={calendar.loading}
          onDayClick={handleDayClick}
        />
      )}
      {viewMode === '2weeks' && (
        <DeliveryWeekView
          period="2weeks"
          dateRange={calendar.dateRange}
          itemsByDate={calendar.itemsByDate}
          loading={calendar.loading}
          onDayClick={handleDayClick}
        />
      )}
      {viewMode === '1month' && (
        <DeliveryMonthView
          dateRange={calendar.dateRange}
          itemsByDate={calendar.itemsByDate}
          loading={calendar.loading}
          onDayClick={handleDayClick}
        />
      )}

      {/* ── Day detail drawer ── */}
      <DeliveryDayDetailDrawer
        open={Boolean(calendar.selectedDate)}
        date={calendar.selectedDate}
        items={calendar.selectedDateItems}
        onClose={() => calendar.setSelectedDate(null)}
        onDataChange={handleDrawerDataChange}
        onEdit={(item) => {
          calendar.setSelectedDate(null);
          handleEdit(item);
        }}
        onCopy={(item) => {
          calendar.setSelectedDate(null);
          handleCopy(item);
        }}
        onError={(msg) => notify(msg, 'error')}
      />

      {/* ── Table view dialogs ── */}
      <Dialog open={deliveryDialogOpen} onClose={() => setDeliveryDialogOpen(false)} maxWidth="xs" fullWidth>
        <DialogTitle>搬入済みにする</DialogTitle>
        <DialogContent>
          <Typography variant="body2" sx={{ mb: 2 }}>
            実績重量を入力してください。搬入記録（waste_record）が自動作成されます。
          </Typography>
          <TextField
            label="実績重量" type="number" value={actualWeight}
            onChange={(e) => setActualWeight(e.target.value)}
            fullWidth size="small" inputProps={{ min: 0, step: 0.1 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeliveryDialogOpen(false)}>キャンセル</Button>
          <Button onClick={handleDeliverConfirm} variant="contained" color="success">搬入済にする</Button>
        </DialogActions>
      </Dialog>

      <Dialog open={cancelDialogOpen} onClose={() => setCancelDialogOpen(false)} maxWidth="xs" fullWidth>
        <DialogTitle>キャンセル確認</DialogTitle>
        <DialogContent>
          <Typography variant="body2">この搬入予定をキャンセルしますか？</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCancelDialogOpen(false)}>戻る</Button>
          <Button onClick={handleCancelConfirm} variant="contained" color="error">キャンセルする</Button>
        </DialogActions>
      </Dialog>

      <ConfirmDeleteDialog
        open={deleteTarget !== null}
        targetName={deleteTarget ? `${deleteTarget.scheduled_date} ${deleteTarget.material_name || ''}` : undefined}
        onConfirm={handleDeleteConfirm}
        onCancel={() => setDeleteTarget(null)}
      />

      <NotificationSnackbar
        open={notification.open}
        message={notification.message}
        severity={notification.severity}
        onClose={closeNotification}
      />
    </Box>
  );
};

export default DeliveryScheduleList;
