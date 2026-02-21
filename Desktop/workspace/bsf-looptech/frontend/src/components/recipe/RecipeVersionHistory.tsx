import React, { useState, useEffect, useCallback } from 'react';
import {
  Box, Typography, Dialog, DialogTitle, DialogContent, DialogActions,
  Button, List, ListItem, ListItemText, ListItemSecondaryAction,
  IconButton, Chip, CircularProgress, Divider, Alert, Snackbar,
  Tooltip, DialogContentText,
} from '@mui/material';
import {
  Restore as RestoreIcon,
  CompareArrows as DiffIcon,
  Visibility as ViewIcon,
} from '@mui/icons-material';
import { fetchRecipeVersions, rollbackRecipeVersion } from '../../api/materialsApi';
import type { RecipeVersionListItem } from '../../types/api';
import RecipeVersionDiff from './RecipeVersionDiff';
import RecipeVersionView from './RecipeVersionView';

interface Props {
  open: boolean;
  recipeId: string;
  recipeName: string;
  currentVersion: number;
  onClose: (changed: boolean) => void;
}

const RecipeVersionHistory: React.FC<Props> = ({
  open,
  recipeId,
  recipeName,
  currentVersion,
  onClose,
}) => {
  const [versions, setVersions] = useState<RecipeVersionListItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [rolling, setRolling] = useState(false);
  const [changed, setChanged] = useState(false);
  const [diffOpen, setDiffOpen] = useState(false);
  const [diffVersions, setDiffVersions] = useState<{ v1: number; v2: number; useCurrent?: boolean } | null>(null);
  const [viewOpen, setViewOpen] = useState(false);
  const [viewVersion, setViewVersion] = useState<number | null>(null);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' as 'success' | 'error' });
  const [rollbackConfirm, setRollbackConfirm] = useState<{ open: boolean; version: number | null }>({
    open: false,
    version: null,
  });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchRecipeVersions(recipeId);
      setVersions(data);
    } catch {
      setSnackbar({ open: true, message: 'バージョン履歴の読み込みに失敗しました', severity: 'error' });
    } finally {
      setLoading(false);
    }
  }, [recipeId]);

  useEffect(() => {
    if (open) load();
  }, [open, load]);

  const handleRollbackConfirm = async () => {
    if (rollbackConfirm.version === null) return;
    const version = rollbackConfirm.version;
    setRollbackConfirm({ open: false, version: null });
    setRolling(true);
    try {
      await rollbackRecipeVersion(recipeId, version);
      setChanged(true);
      setSnackbar({ open: true, message: `バージョン ${version} にロールバックしました`, severity: 'success' });
      await load();
    } catch {
      setSnackbar({ open: true, message: 'ロールバックに失敗しました', severity: 'error' });
    } finally {
      setRolling(false);
    }
  };

  const handleShowDiff = (v1: number, v2: number, useCurrent = false) => {
    setDiffVersions({ v1, v2, useCurrent });
    setDiffOpen(true);
  };

  const handleViewVersion = (v: number) => {
    setViewVersion(v);
    setViewOpen(true);
  };

  const formatDate = (dateStr?: string): string => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleString('ja-JP', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <>
      <Dialog open={open} onClose={() => onClose(changed)} maxWidth="sm" fullWidth>
        <DialogTitle>
          バージョン履歴 - {recipeName}
          <Typography variant="body2" color="text.secondary">
            現在のバージョン: v{currentVersion}
          </Typography>
        </DialogTitle>
        <DialogContent dividers>
          {loading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
              <CircularProgress />
            </Box>
          ) : versions.length === 0 ? (
            <Typography color="text.secondary" sx={{ py: 4, textAlign: 'center' }}>
              バージョン履歴はありません。レシピを更新すると自動的に記録されます。
            </Typography>
          ) : (
            <List disablePadding>
              {versions.map((ver, idx) => (
                <React.Fragment key={ver.id}>
                  {idx > 0 && <Divider />}
                  <ListItem>
                    <ListItemText
                      primary={
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Chip
                            label={`v${ver.version}`}
                            size="small"
                            color="primary"
                            variant="outlined"
                          />
                          <Typography variant="body2">
                            {formatDate(ver.created_at)}
                          </Typography>
                        </Box>
                      }
                      secondary={ver.change_summary || '変更内容なし'}
                    />
                    <ListItemSecondaryAction>
                      <Tooltip title={`v${ver.version} を表示`}>
                        <IconButton
                          size="small"
                          onClick={() => handleViewVersion(ver.version)}
                          aria-label="バージョン表示"
                        >
                          <ViewIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title={`v${ver.version} と現在を比較`}>
                        <IconButton
                          size="small"
                          onClick={() => handleShowDiff(ver.version, currentVersion, true)}
                          color="info"
                          aria-label="現在と比較"
                        >
                          <DiffIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title={`v${ver.version} にロールバック`}>
                        <span>
                          <IconButton
                            size="small"
                            onClick={() => setRollbackConfirm({ open: true, version: ver.version })}
                            color="warning"
                            disabled={rolling}
                            aria-label="ロールバック"
                          >
                            <RestoreIcon fontSize="small" />
                          </IconButton>
                        </span>
                      </Tooltip>
                    </ListItemSecondaryAction>
                  </ListItem>
                </React.Fragment>
              ))}
            </List>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => onClose(changed)}>閉じる</Button>
        </DialogActions>
      </Dialog>

      {/* Rollback Confirmation */}
      <Dialog
        open={rollbackConfirm.open}
        onClose={() => setRollbackConfirm({ open: false, version: null })}
      >
        <DialogTitle>ロールバック確認</DialogTitle>
        <DialogContent>
          <DialogContentText>
            バージョン v{rollbackConfirm.version} にロールバックしますか？
            現在の状態はバージョン履歴に保存されます。
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRollbackConfirm({ open: false, version: null })}>
            キャンセル
          </Button>
          <Button onClick={handleRollbackConfirm} color="warning" variant="contained">
            ロールバック
          </Button>
        </DialogActions>
      </Dialog>

      {diffOpen && diffVersions && (
        <RecipeVersionDiff
          open={diffOpen}
          recipeId={recipeId}
          v1={diffVersions.v1}
          v2={diffVersions.v2}
          useCurrent={diffVersions.useCurrent}
          onClose={() => setDiffOpen(false)}
        />
      )}

      {viewOpen && viewVersion !== null && (
        <RecipeVersionView
          open={viewOpen}
          recipeId={recipeId}
          version={viewVersion}
          onClose={() => setViewOpen(false)}
        />
      )}

      <Snackbar
        open={snackbar.open}
        autoHideDuration={3000}
        onClose={() => setSnackbar(s => ({ ...s, open: false }))}
      >
        <Alert severity={snackbar.severity} variant="filled">{snackbar.message}</Alert>
      </Snackbar>
    </>
  );
};

export default RecipeVersionHistory;
