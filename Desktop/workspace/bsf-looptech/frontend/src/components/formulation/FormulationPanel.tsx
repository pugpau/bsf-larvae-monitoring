import React, { useState, useEffect, useCallback } from 'react';
import {
  Box, Typography, Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Paper, IconButton, Button, Chip, Stack, TextField, MenuItem,
  Tooltip,
} from '@mui/material';
import {
  AutoAwesome as RecommendIcon,
  CheckCircle as AcceptIcon,
  PlayArrow as ApplyIcon,
  Verified as VerifyIcon,
  Cancel as RejectIcon,
  Delete as DeleteIcon,
  Add as AddIcon,
  FileDownload as ExportIcon,
} from '@mui/icons-material';
import {
  fetchFormulations, acceptFormulation, rejectFormulation, deleteFormulation,
  exportFormulationsCsv,
} from '../../api/formulationApi';
import { downloadBlob } from '../../api/materialsApi';
import type { FormulationRecord, FormulationStatus, FormulationSourceType } from '../../types/api';
import { useNotification } from '../../hooks/useNotification';
import TableSkeleton from '../common/TableSkeleton';
import EmptyState from '../common/EmptyState';
import JaTablePagination from '../common/JaTablePagination';
import NotificationSnackbar from '../common/NotificationSnackbar';
import RecommendDialog from './RecommendDialog';
import ApplyDialog from './ApplyDialog';
import VerifyDialog from './VerifyDialog';
import FormulationDetailDrawer from './FormulationDetailDrawer';

// ── Status config ──

const STATUS_CONFIG: Record<FormulationStatus, {
  label: string;
  color: 'default' | 'primary' | 'success' | 'warning' | 'error' | 'info';
}> = {
  proposed: { label: '提案', color: 'info' },
  accepted: { label: '承認済', color: 'primary' },
  applied: { label: '適用済', color: 'warning' },
  verified: { label: '検証済', color: 'success' },
  rejected: { label: '却下', color: 'error' },
};

const SOURCE_LABELS: Record<FormulationSourceType, string> = {
  manual: '手動',
  ml: 'ML予測',
  similarity: '類似度',
  rule: 'ルール',
  optimization: '最適化',
  recipe: 'レシピ',
};

const ROWS_PER_PAGE_OPTIONS = [10, 25, 50];

// ── Main component ──

interface FormulationPanelProps {
  /** Tab 0→1 連携: 推薦ダイアログを自動で開く対象の搬入記録ID */
  initialWasteRecordId?: string | null;
  /** 搬入記録ID消費後のコールバック */
  onConsumeWasteRecordId?: () => void;
}

const FormulationPanel: React.FC<FormulationPanelProps> = ({
  initialWasteRecordId,
  onConsumeWasteRecordId,
}) => {
  const [items, setItems] = useState<FormulationRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [statusFilter, setStatusFilter] = useState('');
  const [sourceFilter, setSourceFilter] = useState('');

  // Dialogs
  const [recommendOpen, setRecommendOpen] = useState(false);
  const [recommendWasteId, setRecommendWasteId] = useState<string | null>(null);
  const [applyTarget, setApplyTarget] = useState<FormulationRecord | null>(null);
  const [verifyTarget, setVerifyTarget] = useState<FormulationRecord | null>(null);
  const [detailTarget, setDetailTarget] = useState<FormulationRecord | null>(null);

  // Tab 0→1 連携: initialWasteRecordId が渡されたら推薦ダイアログを自動で開く
  useEffect(() => {
    if (initialWasteRecordId) {
      setRecommendWasteId(initialWasteRecordId);
      setRecommendOpen(true);
      onConsumeWasteRecordId?.();
    }
  }, [initialWasteRecordId, onConsumeWasteRecordId]);

  const { notification, notify, closeNotification } = useNotification();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const result = await fetchFormulations({
        status: statusFilter || undefined,
        source_type: sourceFilter || undefined,
        sort_by: 'created_at',
        sort_order: 'desc',
        limit: rowsPerPage,
        offset: page * rowsPerPage,
      });
      setItems(result.items);
      setTotal(result.total);
    } catch {
      notify('配合データの読み込みに失敗しました', 'error');
    } finally {
      setLoading(false);
    }
  }, [statusFilter, sourceFilter, page, rowsPerPage, notify]);

  useEffect(() => { load(); }, [load]);

  // ── Actions ──

  const handleAccept = async (record: FormulationRecord) => {
    try {
      await acceptFormulation(record.id);
      notify('配合を承認しました');
      load();
    } catch {
      notify('承認に失敗しました', 'error');
    }
  };

  const handleReject = async (record: FormulationRecord) => {
    try {
      await rejectFormulation(record.id);
      notify('配合を却下しました');
      load();
    } catch {
      notify('却下に失敗しました', 'error');
    }
  };

  const handleDelete = async (record: FormulationRecord) => {
    try {
      await deleteFormulation(record.id);
      notify('配合を削除しました');
      load();
    } catch {
      notify('削除に失敗しました', 'error');
    }
  };

  const handleExport = async () => {
    try {
      const blob = await exportFormulationsCsv({
        status: statusFilter || undefined,
        source_type: sourceFilter || undefined,
      });
      downloadBlob(blob, 'formulations.csv');
      notify('CSVをエクスポートしました');
    } catch {
      notify('CSVエクスポートに失敗しました', 'error');
    }
  };

  const handleRecommendComplete = (candidates: FormulationRecord[]) => {
    notify(`${candidates.length}件の配合候補を生成しました`);
    load();
  };

  const handleApplyComplete = () => {
    setApplyTarget(null);
    notify('配合を適用しました');
    load();
  };

  const handleVerifyComplete = (updated: FormulationRecord) => {
    setVerifyTarget(null);
    const msg = updated.elution_passed ? '溶出試験合格' : '溶出試験不合格';
    notify(msg, updated.elution_passed ? 'success' : 'warning');
    load();
  };

  // ── Render actions per status ──

  const renderActions = (record: FormulationRecord) => {
    const { status } = record;
    return (
      <Stack direction="row" spacing={0.5}>
        {status === 'proposed' && (
          <>
            <Tooltip title="承認">
              <IconButton size="small" color="primary" onClick={() => handleAccept(record)}>
                <AcceptIcon fontSize="small" />
              </IconButton>
            </Tooltip>
            <Tooltip title="却下">
              <IconButton size="small" color="error" onClick={() => handleReject(record)}>
                <RejectIcon fontSize="small" />
              </IconButton>
            </Tooltip>
            <Tooltip title="削除">
              <IconButton size="small" onClick={() => handleDelete(record)}>
                <DeleteIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          </>
        )}
        {status === 'accepted' && (
          <>
            <Tooltip title="適用">
              <IconButton size="small" color="primary" onClick={() => setApplyTarget(record)}>
                <ApplyIcon fontSize="small" />
              </IconButton>
            </Tooltip>
            <Tooltip title="却下">
              <IconButton size="small" color="error" onClick={() => handleReject(record)}>
                <RejectIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          </>
        )}
        {status === 'applied' && (
          <>
            <Tooltip title="溶出検証">
              <IconButton size="small" color="success" onClick={() => setVerifyTarget(record)}>
                <VerifyIcon fontSize="small" />
              </IconButton>
            </Tooltip>
            <Tooltip title="却下">
              <IconButton size="small" color="error" onClick={() => handleReject(record)}>
                <RejectIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          </>
        )}
      </Stack>
    );
  };

  return (
    <Paper sx={{ p: 2 }}>
      <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
        配合ワークフロー
      </Typography>

      {/* Toolbar */}
      <Stack direction="row" spacing={2} sx={{ mb: 2, flexWrap: 'wrap' }} alignItems="center">
        <TextField
          select
          label="ステータス"
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setPage(0); }}
          size="small"
          sx={{ minWidth: 140 }}
          InputLabelProps={{ shrink: true }}
        >
          <MenuItem value="">全て</MenuItem>
          {Object.entries(STATUS_CONFIG).map(([key, cfg]) => (
            <MenuItem key={key} value={key}>{cfg.label}</MenuItem>
          ))}
        </TextField>

        <TextField
          select
          label="推薦元"
          value={sourceFilter}
          onChange={(e) => { setSourceFilter(e.target.value); setPage(0); }}
          size="small"
          sx={{ minWidth: 140 }}
          InputLabelProps={{ shrink: true }}
        >
          <MenuItem value="">全て</MenuItem>
          {Object.entries(SOURCE_LABELS).map(([key, label]) => (
            <MenuItem key={key} value={key}>{label}</MenuItem>
          ))}
        </TextField>

        <Box sx={{ flexGrow: 1 }} />

        <Button
          size="small"
          variant="outlined"
          startIcon={<ExportIcon />}
          onClick={handleExport}
        >
          CSV出力
        </Button>

        <Button
          variant="contained"
          startIcon={<RecommendIcon />}
          onClick={() => { setRecommendWasteId(null); setRecommendOpen(true); }}
        >
          AI推薦
        </Button>
      </Stack>

      {/* Table */}
      <TableContainer>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>搬入元</TableCell>
              <TableCell>廃棄物種別</TableCell>
              <TableCell>推薦元</TableCell>
              <TableCell>ステータス</TableCell>
              <TableCell align="right">信頼度</TableCell>
              <TableCell align="right">見積コスト</TableCell>
              <TableCell>レシピ</TableCell>
              <TableCell align="center">操作</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {loading ? (
              <TableSkeleton columns={8} />
            ) : items.length === 0 ? (
              <TableRow>
                <TableCell colSpan={8}>
                  <EmptyState
                    title="配合データがありません"
                    description="AI推薦ボタンから配合候補を生成できます"
                    actionLabel="AI推薦"
                    onAction={() => setRecommendOpen(true)}
                  />
                </TableCell>
              </TableRow>
            ) : (
              items.map((record) => {
                const statusCfg = STATUS_CONFIG[record.status];
                return (
                  <TableRow key={record.id} hover sx={{ cursor: 'pointer' }} onClick={() => setDetailTarget(record)}>
                    <TableCell>{record.waste_source ?? '-'}</TableCell>
                    <TableCell>{record.waste_type ?? '-'}</TableCell>
                    <TableCell>
                      <Chip
                        label={SOURCE_LABELS[record.source_type] ?? record.source_type}
                        size="small"
                        variant="outlined"
                      />
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={statusCfg?.label ?? record.status}
                        size="small"
                        color={statusCfg?.color ?? 'default'}
                      />
                    </TableCell>
                    <TableCell align="right">
                      {record.confidence != null
                        ? `${(record.confidence * 100).toFixed(0)}%`
                        : '-'}
                    </TableCell>
                    <TableCell align="right">
                      {record.estimated_cost != null
                        ? `${record.estimated_cost.toLocaleString()}円`
                        : '-'}
                    </TableCell>
                    <TableCell>{record.recipe_name ?? '-'}</TableCell>
                    <TableCell align="center" onClick={(e) => e.stopPropagation()}>
                      {renderActions(record)}
                    </TableCell>
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>
      </TableContainer>

      <JaTablePagination
        count={total}
        page={page}
        onPageChange={(_, p) => setPage(p)}
        rowsPerPage={rowsPerPage}
        onRowsPerPageChange={(e) => { setRowsPerPage(parseInt(e.target.value, 10)); setPage(0); }}
        rowsPerPageOptions={ROWS_PER_PAGE_OPTIONS}
      />

      {/* Dialogs */}
      <RecommendDialog
        open={recommendOpen}
        initialWasteRecordId={recommendWasteId}
        onClose={() => { setRecommendOpen(false); setRecommendWasteId(null); }}
        onComplete={handleRecommendComplete}
      />
      <ApplyDialog
        open={Boolean(applyTarget)}
        record={applyTarget}
        onClose={() => setApplyTarget(null)}
        onComplete={handleApplyComplete}
      />
      <VerifyDialog
        open={Boolean(verifyTarget)}
        record={verifyTarget}
        onClose={() => setVerifyTarget(null)}
        onComplete={handleVerifyComplete}
      />
      <FormulationDetailDrawer
        open={Boolean(detailTarget)}
        record={detailTarget}
        onClose={() => setDetailTarget(null)}
      />

      <NotificationSnackbar
        open={notification.open}
        message={notification.message}
        severity={notification.severity}
        onClose={closeNotification}
      />
    </Paper>
  );
};

export default FormulationPanel;
