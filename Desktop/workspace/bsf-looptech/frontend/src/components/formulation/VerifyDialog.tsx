import React, { useState } from 'react';
import {
  Dialog, DialogTitle, DialogContent, DialogActions,
  Button, TextField, Box, Typography, CircularProgress, Alert,
  FormControlLabel, Switch, Divider,
} from '@mui/material';
import { Verified as VerifyIcon } from '@mui/icons-material';
import { verifyFormulation } from '../../api/formulationApi';
import type { FormulationRecord } from '../../types/api';

/** 土壌汚染対策法 溶出基準 (mg/L) */
const ELUTION_METALS = ['Pb', 'As', 'Cd', 'Cr6', 'Hg', 'Se', 'F', 'B'] as const;

interface VerifyDialogProps {
  open: boolean;
  record: FormulationRecord | null;
  onClose: () => void;
  onComplete: (updated: FormulationRecord) => void;
}

const VerifyDialog: React.FC<VerifyDialogProps> = ({ open, record, onClose, onComplete }) => {
  const [metals, setMetals] = useState<Record<string, string>>({});
  const [passed, setPassed] = useState(true);
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleOpen = () => {
    const initial: Record<string, string> = {};
    for (const m of ELUTION_METALS) {
      initial[m] = '';
    }
    setMetals(initial);
    setPassed(true);
    setNotes('');
    setError(null);
  };

  const handleMetalChange = (metal: string, value: string) => {
    setMetals((prev) => ({ ...prev, [metal]: value }));
  };

  const handleVerify = async () => {
    if (!record) return;
    setLoading(true);
    setError(null);
    try {
      const elutionResult: Record<string, unknown> = {};
      for (const [key, val] of Object.entries(metals)) {
        if (val !== '') {
          elutionResult[key] = parseFloat(val);
        }
      }
      if (Object.keys(elutionResult).length === 0) {
        setError('少なくとも1つの溶出試験結果を入力してください');
        setLoading(false);
        return;
      }
      const result = await verifyFormulation(record.id, {
        elution_result: elutionResult,
        elution_passed: passed,
        notes: notes || undefined,
      });
      onComplete(result);
      onClose();
    } catch {
      setError('検証に失敗しました');
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
        <VerifyIcon color="primary" />
        溶出試験検証
      </DialogTitle>
      <DialogContent>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
          <Typography variant="body2" color="text.secondary">
            溶出試験結果を入力して配合の合否を判定します。
          </Typography>

          {error && <Alert severity="error">{error}</Alert>}

          <FormControlLabel
            control={
              <Switch
                checked={passed}
                onChange={(e) => setPassed(e.target.checked)}
                color="success"
              />
            }
            label={passed ? '合格' : '不合格'}
          />

          <Divider />

          <Typography variant="subtitle2">溶出試験結果 (mg/L)</Typography>
          <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1.5 }}>
            {ELUTION_METALS.map((metal) => (
              <TextField
                key={metal}
                type="number"
                label={metal}
                value={metals[metal] ?? ''}
                onChange={(e) => handleMetalChange(metal, e.target.value)}
                size="small"
                InputLabelProps={{ shrink: true }}
                inputProps={{ min: 0, step: 0.0001 }}
              />
            ))}
          </Box>

          <TextField
            label="備考"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            fullWidth
            multiline
            rows={2}
            InputLabelProps={{ shrink: true }}
          />
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={loading}>キャンセル</Button>
        <Button
          variant="contained"
          onClick={handleVerify}
          disabled={loading}
          color={passed ? 'success' : 'error'}
          startIcon={loading ? <CircularProgress size={16} /> : <VerifyIcon />}
        >
          {loading ? '検証中...' : passed ? '合格で検証' : '不合格で検証'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default VerifyDialog;
