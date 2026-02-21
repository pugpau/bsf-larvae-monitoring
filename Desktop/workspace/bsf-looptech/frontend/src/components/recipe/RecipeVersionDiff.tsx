import React, { useState, useEffect } from 'react';
import {
  Box, Typography, Dialog, DialogTitle, DialogContent, DialogActions,
  Button, Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Paper, Chip, CircularProgress,
} from '@mui/material';
import {
  Add as AddIcon,
  Remove as RemoveIcon,
  Edit as EditIcon,
} from '@mui/icons-material';
import { fetchRecipeVersionDiff, fetchRecipeVersionDiffWithCurrent } from '../../api/materialsApi';
import type { RecipeDiffResponse, RecipeDiffField, RecipeVersionDetail } from '../../types/api';

interface Props {
  open: boolean;
  recipeId: string;
  v1: number;
  v2: number;
  useCurrent?: boolean;
  onClose: () => void;
}

const FIELD_LABELS: Record<string, string> = {
  name: 'レシピ名',
  supplier_id: '搬入先',
  waste_type: '廃棄物種類',
  target_strength: '目標強度',
  target_elution: '目標溶出値',
  status: 'ステータス',
  notes: '備考',
};

const formatValue = (value: unknown): string => {
  if (value === null || value === undefined) return '-';
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
};

const RecipeVersionDiff: React.FC<Props> = ({ open, recipeId, v1, v2, useCurrent, onClose }) => {
  const [diff, setDiff] = useState<RecipeDiffResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    setError(null);
    const fetchFn = useCurrent
      ? fetchRecipeVersionDiffWithCurrent(recipeId, v1)
      : fetchRecipeVersionDiff(recipeId, v1, v2);
    fetchFn
      .then(setDiff)
      .catch(() => setError('差分データの取得に失敗しました'))
      .finally(() => setLoading(false));
  }, [open, recipeId, v1, v2, useCurrent]);

  const hasChanges = diff && (
    diff.header_changes.length > 0 ||
    diff.details_added.length > 0 ||
    diff.details_removed.length > 0 ||
    diff.details_modified.length > 0
  );

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        バージョン差分: v{v1} → {useCurrent ? '現在' : `v${v2}`}
      </DialogTitle>
      <DialogContent dividers>
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
            <CircularProgress />
          </Box>
        ) : error ? (
          <Typography color="error">{error}</Typography>
        ) : diff && !hasChanges ? (
          <Typography color="text.secondary" sx={{ py: 4, textAlign: 'center' }}>
            差分はありません
          </Typography>
        ) : diff ? (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            {/* Header Changes */}
            {diff.header_changes.length > 0 && (
              <Box>
                <Typography variant="subtitle2" sx={{ mb: 1 }}>
                  ヘッダー変更
                </Typography>
                <TableContainer component={Paper} variant="outlined">
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>フィールド</TableCell>
                        <TableCell>v{v1} (旧)</TableCell>
                        <TableCell>{useCurrent ? '現在' : `v${v2}`} (新)</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {diff.header_changes.map((change: RecipeDiffField) => (
                        <TableRow key={change.field}>
                          <TableCell sx={{ fontWeight: 500 }}>
                            {FIELD_LABELS[change.field] || change.field}
                          </TableCell>
                          <TableCell sx={{ color: 'error.main', fontFamily: "'Fira Code', monospace", fontSize: '0.85rem' }}>
                            {formatValue(change.old_value)}
                          </TableCell>
                          <TableCell sx={{ color: 'success.main', fontFamily: "'Fira Code', monospace", fontSize: '0.85rem' }}>
                            {formatValue(change.new_value)}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </Box>
            )}

            {/* Details Added */}
            {diff.details_added.length > 0 && (
              <Box>
                <Typography variant="subtitle2" sx={{ mb: 1, display: 'flex', alignItems: 'center', gap: 0.5 }}>
                  <AddIcon fontSize="small" color="success" />
                  追加された材料
                </Typography>
                <TableContainer component={Paper} variant="outlined">
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>材料種類</TableCell>
                        <TableCell align="right">添加率</TableCell>
                        <TableCell>備考</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {diff.details_added.map((d: RecipeVersionDetail) => (
                        <TableRow key={d.id}>
                          <TableCell>
                            <Chip label={d.material_type} size="small" color="success" variant="outlined" />
                          </TableCell>
                          <TableCell align="right" sx={{ fontFamily: "'Fira Code', monospace" }}>
                            {d.addition_rate}
                          </TableCell>
                          <TableCell>{d.notes || '-'}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </Box>
            )}

            {/* Details Removed */}
            {diff.details_removed.length > 0 && (
              <Box>
                <Typography variant="subtitle2" sx={{ mb: 1, display: 'flex', alignItems: 'center', gap: 0.5 }}>
                  <RemoveIcon fontSize="small" color="error" />
                  削除された材料
                </Typography>
                <TableContainer component={Paper} variant="outlined">
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>材料種類</TableCell>
                        <TableCell align="right">添加率</TableCell>
                        <TableCell>備考</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {diff.details_removed.map((d: RecipeVersionDetail) => (
                        <TableRow key={d.id}>
                          <TableCell>
                            <Chip label={d.material_type} size="small" color="error" variant="outlined" />
                          </TableCell>
                          <TableCell align="right" sx={{ fontFamily: "'Fira Code', monospace" }}>
                            {d.addition_rate}
                          </TableCell>
                          <TableCell>{d.notes || '-'}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </Box>
            )}

            {/* Details Modified */}
            {diff.details_modified.length > 0 && (
              <Box>
                <Typography variant="subtitle2" sx={{ mb: 1, display: 'flex', alignItems: 'center', gap: 0.5 }}>
                  <EditIcon fontSize="small" color="info" />
                  変更された材料
                </Typography>
                <TableContainer component={Paper} variant="outlined">
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>フィールド</TableCell>
                        <TableCell>旧値</TableCell>
                        <TableCell>新値</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {diff.details_modified.map((mod, idx) => {
                        const entries = Object.entries(mod).filter(([k]) => k !== 'material_id');
                        return entries.map(([field, change]) => (
                          <TableRow key={`${idx}-${field}`}>
                            <TableCell sx={{ fontWeight: 500 }}>{field}</TableCell>
                            <TableCell sx={{ color: 'error.main', fontFamily: "'Fira Code', monospace", fontSize: '0.85rem' }}>
                              {formatValue((change as Record<string, unknown>)?.old)}
                            </TableCell>
                            <TableCell sx={{ color: 'success.main', fontFamily: "'Fira Code', monospace", fontSize: '0.85rem' }}>
                              {formatValue((change as Record<string, unknown>)?.new)}
                            </TableCell>
                          </TableRow>
                        ));
                      })}
                    </TableBody>
                  </Table>
                </TableContainer>
              </Box>
            )}
          </Box>
        ) : null}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>閉じる</Button>
      </DialogActions>
    </Dialog>
  );
};

export default RecipeVersionDiff;
