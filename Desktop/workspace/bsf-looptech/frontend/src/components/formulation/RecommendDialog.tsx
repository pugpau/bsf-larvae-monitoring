import React, { useState, useEffect, useCallback } from 'react';
import {
  Dialog, DialogTitle, DialogContent, DialogActions,
  Button, TextField, MenuItem, Box, Typography,
  CircularProgress, Alert,
} from '@mui/material';
import { AutoAwesome as RecommendIcon } from '@mui/icons-material';
import { fetchWasteRecords } from '../../api/wasteApi';
import { recommendFormulations } from '../../api/formulationApi';
import type { WasteRecord, FormulationRecord } from '../../types/api';

interface RecommendDialogProps {
  open: boolean;
  /** Tab 0→1 連携: 事前選択する搬入記録ID */
  initialWasteRecordId?: string | null;
  onClose: () => void;
  onComplete: (candidates: FormulationRecord[]) => void;
}

const RecommendDialog: React.FC<RecommendDialogProps> = ({ open, initialWasteRecordId, onClose, onComplete }) => {
  const [wasteRecords, setWasteRecords] = useState<WasteRecord[]>([]);
  const [selectedWasteId, setSelectedWasteId] = useState('');
  const [topK, setTopK] = useState(3);
  const [loading, setLoading] = useState(false);
  const [loadingRecords, setLoadingRecords] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadWasteRecords = useCallback(async () => {
    setLoadingRecords(true);
    try {
      const result = await fetchWasteRecords({ limit: 100, sort_by: 'created_at', sort_order: 'desc' });
      // Filter to records with analysis data (status: analyzed or pending with analysis)
      const eligible = result.items.filter(
        (r) => r.analysis && Object.keys(r.analysis).length > 0,
      );
      setWasteRecords(eligible);
    } catch {
      setError('搬入記録の取得に失敗しました');
    } finally {
      setLoadingRecords(false);
    }
  }, []);

  useEffect(() => {
    if (open) {
      setSelectedWasteId(initialWasteRecordId ?? '');
      setTopK(3);
      setError(null);
      loadWasteRecords();
    }
  }, [open, initialWasteRecordId, loadWasteRecords]);

  const handleRecommend = async () => {
    if (!selectedWasteId) return;
    setLoading(true);
    setError(null);
    try {
      const result = await recommendFormulations(selectedWasteId, topK);
      onComplete(result.candidates);
      onClose();
    } catch (err) {
      const message = err instanceof Error ? err.message : '推薦の生成に失敗しました';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <RecommendIcon color="primary" />
        配合推薦
      </DialogTitle>
      <DialogContent>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
          <Typography variant="body2" color="text.secondary">
            搬入記録を選択して、ML/類似度/ルールベースの配合候補を自動生成します。
          </Typography>

          {error && <Alert severity="error">{error}</Alert>}

          <TextField
            select
            label="搬入記録"
            value={selectedWasteId}
            onChange={(e) => setSelectedWasteId(e.target.value)}
            fullWidth
            disabled={loadingRecords}
            InputLabelProps={{ shrink: true }}
          >
            {loadingRecords ? (
              <MenuItem disabled>読み込み中...</MenuItem>
            ) : wasteRecords.length === 0 ? (
              <MenuItem disabled>分析データのある搬入記録がありません</MenuItem>
            ) : (
              wasteRecords.map((r) => (
                <MenuItem key={r.id} value={r.id}>
                  {r.source} - {r.wasteType} ({r.deliveryDate})
                  {r.status !== 'pending' && ` [${r.status}]`}
                </MenuItem>
              ))
            )}
          </TextField>

          <TextField
            type="number"
            label="候補数"
            value={topK}
            onChange={(e) => setTopK(Math.max(1, Math.min(10, parseInt(e.target.value, 10) || 1)))}
            inputProps={{ min: 1, max: 10 }}
            fullWidth
            InputLabelProps={{ shrink: true }}
          />
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={loading}>キャンセル</Button>
        <Button
          variant="contained"
          onClick={handleRecommend}
          disabled={!selectedWasteId || loading}
          startIcon={loading ? <CircularProgress size={16} /> : <RecommendIcon />}
        >
          {loading ? '推薦中...' : '推薦を実行'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default RecommendDialog;
