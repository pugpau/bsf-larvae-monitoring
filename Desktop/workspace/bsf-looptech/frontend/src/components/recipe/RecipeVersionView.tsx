import React, { useState, useEffect } from 'react';
import {
  Box, Typography, Dialog, DialogTitle, DialogContent, DialogActions,
  Button, Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Paper, Chip, CircularProgress, Stack,
} from '@mui/material';
import { fetchRecipeVersion } from '../../api/materialsApi';
import type { RecipeVersionResponse } from '../../types/api';

interface Props {
  open: boolean;
  recipeId: string;
  version: number;
  onClose: () => void;
}

const STATUS_LABELS: Record<string, string> = {
  draft: '下書き',
  active: '有効',
  archived: 'アーカイブ',
};

const RecipeVersionView: React.FC<Props> = ({ open, recipeId, version, onClose }) => {
  const [data, setData] = useState<RecipeVersionResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    setError(null);
    fetchRecipeVersion(recipeId, version)
      .then(setData)
      .catch(() => setError('バージョンデータの取得に失敗しました'))
      .finally(() => setLoading(false));
  }, [open, recipeId, version]);

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        バージョン v{version} の詳細
      </DialogTitle>
      <DialogContent dividers>
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
            <CircularProgress />
          </Box>
        ) : error ? (
          <Typography color="error">{error}</Typography>
        ) : data ? (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            {/* Header info */}
            <Paper variant="outlined" sx={{ p: 2 }}>
              <Stack spacing={1}>
                <Stack direction="row" spacing={2} alignItems="center">
                  <Typography variant="subtitle2" color="text.secondary" sx={{ minWidth: 100 }}>
                    レシピ名
                  </Typography>
                  <Typography sx={{ fontWeight: 500 }}>{data.name}</Typography>
                </Stack>
                <Stack direction="row" spacing={2} alignItems="center">
                  <Typography variant="subtitle2" color="text.secondary" sx={{ minWidth: 100 }}>
                    廃棄物種類
                  </Typography>
                  <Typography>{data.waste_type}</Typography>
                </Stack>
                <Stack direction="row" spacing={2} alignItems="center">
                  <Typography variant="subtitle2" color="text.secondary" sx={{ minWidth: 100 }}>
                    ステータス
                  </Typography>
                  <Chip
                    label={STATUS_LABELS[data.status] || data.status}
                    size="small"
                    variant="outlined"
                  />
                </Stack>
                {data.target_strength != null && (
                  <Stack direction="row" spacing={2} alignItems="center">
                    <Typography variant="subtitle2" color="text.secondary" sx={{ minWidth: 100 }}>
                      目標強度
                    </Typography>
                    <Typography sx={{ fontFamily: "'Fira Code', monospace" }}>
                      {data.target_strength} kN/m²
                    </Typography>
                  </Stack>
                )}
                {data.notes && (
                  <Stack direction="row" spacing={2} alignItems="center">
                    <Typography variant="subtitle2" color="text.secondary" sx={{ minWidth: 100 }}>
                      備考
                    </Typography>
                    <Typography>{data.notes}</Typography>
                  </Stack>
                )}
                {data.change_summary && (
                  <Stack direction="row" spacing={2} alignItems="center">
                    <Typography variant="subtitle2" color="text.secondary" sx={{ minWidth: 100 }}>
                      変更理由
                    </Typography>
                    <Typography color="text.secondary">{data.change_summary}</Typography>
                  </Stack>
                )}
              </Stack>
            </Paper>

            {/* Details */}
            {data.details && data.details.length > 0 && (
              <Box>
                <Typography variant="subtitle2" sx={{ mb: 1 }}>配合明細</Typography>
                <TableContainer component={Paper} variant="outlined">
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>材料種別</TableCell>
                        <TableCell align="right">添加率 (%)</TableCell>
                        <TableCell>備考</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {data.details.map((det, idx) => (
                        <TableRow key={det.id || idx}>
                          <TableCell>
                            <Chip
                              label={det.material_type === 'solidification' ? '固化材' : '抑制剤'}
                              size="small"
                              variant="outlined"
                            />
                          </TableCell>
                          <TableCell
                            align="right"
                            sx={{ fontFamily: "'Fira Code', monospace" }}
                          >
                            {det.addition_rate}
                          </TableCell>
                          <TableCell>{det.notes || '-'}</TableCell>
                        </TableRow>
                      ))}
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

export default RecipeVersionView;
