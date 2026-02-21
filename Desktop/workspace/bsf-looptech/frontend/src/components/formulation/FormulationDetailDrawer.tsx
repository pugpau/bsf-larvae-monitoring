import React from 'react';
import {
  Drawer, Box, Typography, IconButton, Divider, Chip, Stack,
  Stepper, Step, StepLabel, StepConnector,
  Table, TableBody, TableCell, TableRow,
} from '@mui/material';
import { Close as CloseIcon } from '@mui/icons-material';
import type { FormulationRecord, FormulationStatus, FormulationSourceType } from '../../types/api';

// ── Status workflow steps ──

interface WorkflowStep {
  key: FormulationStatus;
  label: string;
}

const WORKFLOW_STEPS: WorkflowStep[] = [
  { key: 'proposed', label: '提案' },
  { key: 'accepted', label: '承認' },
  { key: 'applied', label: '適用' },
  { key: 'verified', label: '検証' },
];

const STATUS_LABELS: Record<FormulationStatus, string> = {
  proposed: '提案',
  accepted: '承認済',
  applied: '適用済',
  verified: '検証済',
  rejected: '却下',
};

const STATUS_COLORS: Record<FormulationStatus, 'info' | 'primary' | 'warning' | 'success' | 'error'> = {
  proposed: 'info',
  accepted: 'primary',
  applied: 'warning',
  verified: 'success',
  rejected: 'error',
};

const SOURCE_LABELS: Record<FormulationSourceType, string> = {
  manual: '手動',
  ml: 'ML予測',
  similarity: '類似度',
  rule: 'ルール',
  optimization: '最適化',
  recipe: 'レシピ',
};

// ── Helpers ──

function getActiveStep(status: FormulationStatus): number {
  if (status === 'rejected') return -1;
  const idx = WORKFLOW_STEPS.findIndex((s) => s.key === status);
  return idx >= 0 ? idx : 0;
}

function formatValue(value: unknown): string {
  if (value == null) return '-';
  if (typeof value === 'number') return value.toLocaleString();
  if (typeof value === 'boolean') return value ? 'はい' : 'いいえ';
  return String(value);
}

function formatFormulation(data: Record<string, unknown> | undefined): React.ReactNode {
  if (!data || Object.keys(data).length === 0) return '-';
  return (
    <Table size="small" sx={{ '& td': { py: 0.25, border: 0, fontFamily: "'Fira Code', monospace", fontSize: '0.75rem' } }}>
      <TableBody>
        {Object.entries(data).map(([key, val]) => (
          <TableRow key={key}>
            <TableCell sx={{ pl: 0, color: 'text.secondary', width: 120 }}>{key}</TableCell>
            <TableCell>{formatValue(val)}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

// ── Elution metals ──

const ELUTION_THRESHOLDS: Record<string, number> = {
  Pb: 0.01, As: 0.01, Cd: 0.01, Cr6: 0.05,
  Hg: 0.0005, Se: 0.01, F: 0.8, B: 1.0,
};

function formatElution(data: Record<string, unknown> | undefined, passed?: boolean): React.ReactNode {
  if (!data || Object.keys(data).length === 0) return '-';
  return (
    <Box>
      <Chip
        label={passed ? '合格' : '不合格'}
        size="small"
        color={passed ? 'success' : 'error'}
        sx={{ mb: 1 }}
      />
      <Table size="small" sx={{ '& td': { py: 0.25, border: 0, fontFamily: "'Fira Code', monospace", fontSize: '0.75rem' } }}>
        <TableBody>
          {Object.entries(data)
            .filter(([, v]) => typeof v === 'number')
            .map(([metal, val]) => {
              const value = val as number;
              const threshold = ELUTION_THRESHOLDS[metal];
              const exceeded = threshold != null && value > threshold;
              return (
                <TableRow key={metal}>
                  <TableCell sx={{ pl: 0, color: 'text.secondary', width: 60 }}>{metal}</TableCell>
                  <TableCell sx={{ color: exceeded ? 'error.main' : 'text.primary', fontWeight: exceeded ? 700 : 400 }}>
                    {value.toFixed(4)}
                  </TableCell>
                  <TableCell sx={{ color: 'text.secondary' }}>
                    {threshold != null ? `/ ${threshold}` : ''}
                  </TableCell>
                </TableRow>
              );
            })}
        </TableBody>
      </Table>
    </Box>
  );
}

// ── Component ──

interface FormulationDetailDrawerProps {
  open: boolean;
  record: FormulationRecord | null;
  onClose: () => void;
}

const FormulationDetailDrawer: React.FC<FormulationDetailDrawerProps> = ({ open, record, onClose }) => {
  if (!record) return null;

  const activeStep = getActiveStep(record.status);
  const isRejected = record.status === 'rejected';

  return (
    <Drawer anchor="right" open={open} onClose={onClose} PaperProps={{ sx: { width: { xs: '100%', sm: 420 } } }}>
      <Box sx={{ p: 2 }}>
        {/* Header */}
        <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
          <Typography variant="h6" sx={{ fontWeight: 600, fontSize: '1rem' }}>
            配合詳細
          </Typography>
          <IconButton size="small" onClick={onClose} aria-label="閉じる">
            <CloseIcon />
          </IconButton>
        </Stack>

        {/* Status + Source */}
        <Stack direction="row" spacing={1} sx={{ mb: 2 }}>
          <Chip
            label={STATUS_LABELS[record.status]}
            size="small"
            color={STATUS_COLORS[record.status]}
          />
          <Chip
            label={SOURCE_LABELS[record.source_type] ?? record.source_type}
            size="small"
            variant="outlined"
          />
          {record.confidence != null && (
            <Chip
              label={`信頼度 ${(record.confidence * 100).toFixed(0)}%`}
              size="small"
              variant="outlined"
            />
          )}
        </Stack>

        {/* Timeline Stepper */}
        <Box sx={{ mb: 3 }}>
          <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
            ワークフロー
          </Typography>
          {isRejected ? (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, p: 1, borderRadius: 1, bgcolor: 'error.50' }}>
              <Chip label="却下" size="small" color="error" />
              <Typography variant="body2" color="text.secondary">
                {record.notes || 'ステータスが却下に変更されました'}
              </Typography>
            </Box>
          ) : (
            <Stepper
              activeStep={activeStep}
              alternativeLabel
              connector={<StepConnector />}
              sx={{ '& .MuiStepLabel-label': { fontSize: '0.75rem' } }}
            >
              {WORKFLOW_STEPS.map((step) => (
                <Step key={step.key} completed={activeStep > WORKFLOW_STEPS.findIndex((s) => s.key === step.key)}>
                  <StepLabel>{step.label}</StepLabel>
                </Step>
              ))}
            </Stepper>
          )}
        </Box>

        <Divider sx={{ mb: 2 }} />

        {/* Basic info */}
        <Section label="基本情報">
          <InfoRow label="搬入元" value={record.waste_source} />
          <InfoRow label="廃棄物種別" value={record.waste_type} />
          <InfoRow label="レシピ" value={record.recipe_name} />
          {record.recipe_version != null && (
            <InfoRow label="バージョン" value={`v${record.recipe_version}`} />
          )}
          <InfoRow label="作成日時" value={record.created_at ? new Date(record.created_at).toLocaleString('ja-JP') : undefined} />
          <InfoRow label="更新日時" value={record.updated_at ? new Date(record.updated_at).toLocaleString('ja-JP') : undefined} />
        </Section>

        {/* Cost */}
        {(record.estimated_cost != null || record.actual_cost != null) && (
          <Section label="コスト">
            {record.estimated_cost != null && (
              <InfoRow label="見積" value={`${record.estimated_cost.toLocaleString()}円`} />
            )}
            {record.actual_cost != null && (
              <InfoRow label="実績" value={`${record.actual_cost.toLocaleString()}円`} />
            )}
          </Section>
        )}

        {/* Planned formulation */}
        {record.planned_formulation && Object.keys(record.planned_formulation).length > 0 && (
          <Section label="計画配合">
            {formatFormulation(record.planned_formulation as Record<string, unknown>)}
          </Section>
        )}

        {/* Actual formulation */}
        {record.actual_formulation && Object.keys(record.actual_formulation).length > 0 && (
          <Section label="実績配合">
            {formatFormulation(record.actual_formulation as Record<string, unknown>)}
          </Section>
        )}

        {/* Elution result */}
        {record.elution_result && Object.keys(record.elution_result).length > 0 && (
          <Section label="溶出試験結果">
            {formatElution(record.elution_result, record.elution_passed)}
          </Section>
        )}

        {/* Reasoning */}
        {record.reasoning && record.reasoning.length > 0 && (
          <Section label="推薦理由">
            <Box component="ul" sx={{ m: 0, pl: 2 }}>
              {record.reasoning.map((reason, i) => (
                <Typography key={i} component="li" variant="body2" sx={{ fontSize: '0.8rem' }}>
                  {reason}
                </Typography>
              ))}
            </Box>
          </Section>
        )}

        {/* Notes */}
        {record.notes && (
          <Section label="備考">
            <Typography variant="body2" sx={{ fontSize: '0.8rem', whiteSpace: 'pre-wrap' }}>
              {record.notes}
            </Typography>
          </Section>
        )}
      </Box>
    </Drawer>
  );
};

// ── Sub-components ──

const Section: React.FC<{ label: string; children: React.ReactNode }> = ({ label, children }) => (
  <Box sx={{ mb: 2 }}>
    <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 0.5, fontSize: '0.85rem' }}>
      {label}
    </Typography>
    {children}
  </Box>
);

const InfoRow: React.FC<{ label: string; value?: string | null }> = ({ label, value }) => (
  <Stack direction="row" spacing={1} sx={{ mb: 0.25 }}>
    <Typography variant="body2" sx={{ color: 'text.secondary', minWidth: 80, fontSize: '0.8rem' }}>
      {label}
    </Typography>
    <Typography variant="body2" sx={{ fontSize: '0.8rem', fontFamily: "'Fira Code', monospace" }}>
      {value || '-'}
    </Typography>
  </Stack>
);

export default FormulationDetailDrawer;
