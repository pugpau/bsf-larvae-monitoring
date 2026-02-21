import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Box, Button, Stack, TextField, Typography, Chip,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Paper, InputAdornment, CircularProgress,
} from '@mui/material';
import {
  Check as CheckIcon, Close as CloseIcon,
  Search as SearchIcon,
} from '@mui/icons-material';
import {
  fetchIncomingMaterials,
  createDeliverySchedule,
  updateDeliverySchedule,
} from '../../api/deliveryApi';
import type { IncomingMaterial, DeliverySchedule } from '../../types/api';
import { useNotification } from '../../hooks/useNotification';
import NotificationSnackbar from '../common/NotificationSnackbar';

interface DeliveryScheduleFormProps {
  initialData?: DeliverySchedule | null;
  copyMode?: boolean;
  onSubmitSuccess: () => void;
  onCancel: () => void;
}

const DeliveryScheduleForm: React.FC<DeliveryScheduleFormProps> = ({
  initialData,
  copyMode = false,
  onSubmitSuccess,
  onCancel,
}) => {
  const isEdit = Boolean(initialData) && !copyMode;
  const hasPrefill = Boolean(initialData);
  const { notification, notify, closeNotification } = useNotification();

  // Search state
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<IncomingMaterial[]>([]);
  const [searching, setSearching] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const searchTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Selected material
  const [selectedMaterial, setSelectedMaterial] = useState<IncomingMaterial | null>(null);

  // Form fields
  const [scheduledDate, setScheduledDate] = useState('');
  const [estimatedWeight, setEstimatedWeight] = useState('');
  const [weightUnit, setWeightUnit] = useState('t');
  const [notes, setNotes] = useState('');
  const [saving, setSaving] = useState(false);

  // Pre-fill form when editing or copying
  useEffect(() => {
    if (!initialData) return;
    setScheduledDate(copyMode ? '' : (initialData.scheduled_date || ''));
    setEstimatedWeight(initialData.estimated_weight?.toString() || '');
    setWeightUnit(initialData.weight_unit || 't');
    setNotes(initialData.notes || '');
  }, [initialData, copyMode]);

  // Debounced search
  const doSearch = useCallback(async (query: string) => {
    setSearching(true);
    setHasSearched(true);
    try {
      const result = await fetchIncomingMaterials({
        q: query || undefined,
        is_active: true,
        limit: 50,
      });
      setSearchResults(result.items);
    } catch {
      notify('搬入物の検索に失敗しました', 'error');
    } finally {
      setSearching(false);
    }
  }, [notify]);

  const handleSearchChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const query = e.target.value;
    setSearchQuery(query);
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current);
    searchTimerRef.current = setTimeout(() => doSearch(query), 300);
  }, [doSearch]);

  // Load all materials on mount (for new mode)
  useEffect(() => {
    if (!hasPrefill) {
      doSearch('');
    }
  }, [hasPrefill, doSearch]);

  // Select a material from search results
  const handleSelectMaterial = useCallback((mat: IncomingMaterial) => {
    setSelectedMaterial(mat);
    setWeightUnit(mat.default_weight_unit || 't');
  }, []);

  // Clear selection
  const handleClearSelection = useCallback(() => {
    setSelectedMaterial(null);
  }, []);

  const handleSubmit = async () => {
    const materialId = hasPrefill ? initialData?.incoming_material_id : selectedMaterial?.id;
    if (!materialId || !scheduledDate) return;
    setSaving(true);
    try {
      const payload = {
        incoming_material_id: materialId,
        scheduled_date: scheduledDate,
        estimated_weight: estimatedWeight ? parseFloat(estimatedWeight) : undefined,
        weight_unit: weightUnit,
        notes: notes || undefined,
      };
      if (isEdit && initialData) {
        await updateDeliverySchedule(initialData.id, payload);
        notify('搬入予定を更新しました');
      } else {
        await createDeliverySchedule(payload);
        notify(copyMode ? '搬入予定をコピーしました' : '搬入予定を登録しました');
      }
      onSubmitSuccess();
    } catch {
      notify('保存に失敗しました', 'error');
    } finally {
      setSaving(false);
    }
  };

  const canSubmit = (hasPrefill ? initialData?.incoming_material_id : selectedMaterial?.id) && scheduledDate && !saving;

  return (
    <Box sx={{ maxWidth: 800 }}>
      <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
        {isEdit ? '搬入予定の編集' : copyMode ? '搬入予定のコピー（日付変更）' : '搬入予定の新規登録'}
      </Typography>

      <Stack spacing={2.5}>
        {/* Material selection: search for new, read-only for edit/copy */}
        {!hasPrefill && !selectedMaterial && (
          <Box>
            <TextField
              label="搬入物マスタ検索"
              value={searchQuery}
              onChange={handleSearchChange}
              fullWidth size="small"
              placeholder="搬入先、種類、名称で検索..."
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon color="action" />
                  </InputAdornment>
                ),
                endAdornment: searching ? (
                  <InputAdornment position="end">
                    <CircularProgress size={18} />
                  </InputAdornment>
                ) : null,
              }}
            />

            {hasSearched && (
              <TableContainer component={Paper} variant="outlined" sx={{ mt: 1, maxHeight: 300 }}>
                <Table size="small" stickyHeader>
                  <TableHead>
                    <TableRow>
                      <TableCell>搬入先</TableCell>
                      <TableCell>種類</TableCell>
                      <TableCell>名称</TableCell>
                      <TableCell>単位</TableCell>
                      <TableCell align="center">選択</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {searchResults.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={5} align="center" sx={{ color: 'text.secondary', py: 3 }}>
                          {searching ? '検索中...' : '該当する搬入物が見つかりません'}
                        </TableCell>
                      </TableRow>
                    ) : (
                      searchResults.map((mat) => (
                        <TableRow
                          key={mat.id}
                          hover
                          sx={{ cursor: 'pointer' }}
                          onClick={() => handleSelectMaterial(mat)}
                        >
                          <TableCell>{mat.supplier_name || '-'}</TableCell>
                          <TableCell>
                            <Chip label={mat.material_category} size="small" variant="outlined" />
                          </TableCell>
                          <TableCell sx={{ fontWeight: 500 }}>{mat.name}</TableCell>
                          <TableCell sx={{ fontFamily: "'Fira Code', monospace", fontSize: '0.8rem' }}>
                            {mat.default_weight_unit}
                          </TableCell>
                          <TableCell align="center">
                            <Button size="small" variant="outlined" onClick={(e) => { e.stopPropagation(); handleSelectMaterial(mat); }}>
                              選択
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </Box>
        )}

        {/* Selected material display (new mode) */}
        {!hasPrefill && selectedMaterial && (
          <Paper variant="outlined" sx={{ p: 2 }}>
            <Stack direction="row" justifyContent="space-between" alignItems="center">
              <Box>
                <Typography variant="caption" color="text.secondary">選択された搬入物</Typography>
                <Typography variant="body1" sx={{ fontWeight: 600 }}>
                  {selectedMaterial.supplier_name} / {selectedMaterial.material_category} / {selectedMaterial.name}
                </Typography>
              </Box>
              <Button size="small" color="warning" onClick={handleClearSelection}>
                変更
              </Button>
            </Stack>
          </Paper>
        )}

        {/* Read-only display for edit/copy mode */}
        {hasPrefill && initialData && (
          <TextField
            label="搬入物"
            value={`${initialData.supplier_name || ''} / ${initialData.material_category || ''} / ${initialData.material_name || ''}`}
            fullWidth size="small" disabled
          />
        )}

        <TextField
          label="予定日"
          type="date"
          value={scheduledDate}
          onChange={(e) => setScheduledDate(e.target.value)}
          fullWidth size="small" required
          InputLabelProps={{ shrink: true }}
        />

        <Stack direction="row" spacing={2}>
          <TextField
            label="予定重量"
            type="number"
            value={estimatedWeight}
            onChange={(e) => setEstimatedWeight(e.target.value)}
            fullWidth size="small"
            inputProps={{ min: 0, step: 0.1 }}
          />
          <TextField
            label="単位"
            value={weightUnit}
            onChange={(e) => setWeightUnit(e.target.value)}
            size="small"
            sx={{ width: 120 }}
          />
        </Stack>

        <TextField
          label="備考"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          fullWidth size="small" multiline rows={2}
        />

        <Stack direction="row" spacing={1} justifyContent="flex-end">
          <Button onClick={onCancel} startIcon={<CloseIcon />}>キャンセル</Button>
          <Button
            onClick={handleSubmit}
            variant="contained"
            startIcon={<CheckIcon />}
            disabled={!canSubmit}
          >
            {isEdit ? '更新' : '登録'}
          </Button>
        </Stack>
      </Stack>

      <NotificationSnackbar
        open={notification.open}
        message={notification.message}
        severity={notification.severity}
        onClose={closeNotification}
      />
    </Box>
  );
};

export default DeliveryScheduleForm;
