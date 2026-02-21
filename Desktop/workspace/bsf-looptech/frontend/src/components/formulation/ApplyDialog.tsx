import React, { useState } from 'react';
import {
  Dialog, DialogTitle, DialogContent, DialogActions,
  Button, TextField, Box, Typography, CircularProgress, Alert,
} from '@mui/material';
import { PlayArrow as ApplyIcon } from '@mui/icons-material';
import { applyFormulation } from '../../api/formulationApi';
import type { FormulationRecord } from '../../types/api';

interface ApplyDialogProps {
  open: boolean;
  record: FormulationRecord | null;
  onClose: () => void;
  onComplete: (updated: FormulationRecord) => void;
}

const ApplyDialog: React.FC<ApplyDialogProps> = ({ open, record, onClose, onComplete }) => {
  const [solidifierAmount, setSolidifierAmount] = useState('');
  const [actualCost, setActualCost] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleOpen = () => {
    // Pre-fill from planned formulation
    const planned = record?.planned_formulation;
    setSolidifierAmount(
      planned?.solidifierAmount != null ? String(planned.solidifierAmount) : '',
    );
    setActualCost('');
    setError(null);
  };

  const handleApply = async () => {
    if (!record) return;
    setLoading(true);
    setError(null);
    try {
      const payload: Record<string, unknown> = {};
      if (solidifierAmount) {
        payload.actual_formulation = {
          ...record.planned_formulation,
          solidifierAmount: parseFloat(solidifierAmount),
        };
      }
      if (actualCost) {
        payload.actual_cost = parseFloat(actualCost);
      }
      const result = await applyFormulation(record.id, payload);
      onComplete(result);
      onClose();
    } catch {
      setError('配合適用に失敗しました');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="sm"
      fullWidth
      TransitionProps={{ onEnter: handleOpen }}
    >
      <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <ApplyIcon color="primary" />
        配合を適用
      </DialogTitle>
      <DialogContent>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
          <Typography variant="body2" color="text.secondary">
            実際に使用した配合量とコストを入力してください。
            空欄の場合は計画値がそのまま使用されます。
          </Typography>

          {error && <Alert severity="error">{error}</Alert>}

          {record?.planned_formulation?.solidifierType && (
            <Typography variant="body2">
              固化材: {record.planned_formulation.solidifierType}
            </Typography>
          )}

          <TextField
            type="number"
            label="実績添加量 (kg/t)"
            value={solidifierAmount}
            onChange={(e) => setSolidifierAmount(e.target.value)}
            fullWidth
            InputLabelProps={{ shrink: true }}
            inputProps={{ min: 0, step: 0.1 }}
            placeholder={
              record?.planned_formulation?.solidifierAmount != null
                ? `計画値: ${record.planned_formulation.solidifierAmount}`
                : ''
            }
          />

          <TextField
            type="number"
            label="実績コスト (円)"
            value={actualCost}
            onChange={(e) => setActualCost(e.target.value)}
            fullWidth
            InputLabelProps={{ shrink: true }}
            inputProps={{ min: 0, step: 100 }}
            placeholder={
              record?.estimated_cost != null
                ? `見積: ${record.estimated_cost.toLocaleString()}円`
                : ''
            }
          />
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={loading}>キャンセル</Button>
        <Button
          variant="contained"
          onClick={handleApply}
          disabled={loading}
          startIcon={loading ? <CircularProgress size={16} /> : <ApplyIcon />}
        >
          {loading ? '適用中...' : '適用'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default ApplyDialog;
