/**
 * Design System Colors — materialTheme.js パレットのミラー
 * コンポーネント内でのハードコード hex を排除するための定数定義
 */

export const PALETTE = {
  primary: {
    light: '#3B82F6',
    main: '#1E40AF',
    dark: '#1E3A8A',
  },
  secondary: {
    light: '#60A5FA',
    main: '#3B82F6',
    dark: '#2563EB',
  },
  error: {
    light: '#FEE2E2',
    main: '#DC2626',
    dark: '#B91C1C',
  },
  warning: {
    light: '#FEF3C7',
    main: '#D97706',
    dark: '#B45309',
  },
  info: {
    light: '#E0F2FE',
    main: '#0284C7',
    dark: '#0369A1',
  },
  success: {
    light: '#DCFCE7',
    main: '#16A34A',
    dark: '#15803D',
  },
  grey: {
    50: '#F8FAFC',
    100: '#F1F5F9',
    200: '#E2E8F0',
    300: '#CBD5E1',
    400: '#94A3B8',
    500: '#64748B',
    600: '#475569',
    700: '#334155',
    800: '#1E293B',
    900: '#0F172A',
  },
} as const;

/** Recharts チャートシリーズ用 8色配列 */
export const CHART_SERIES_COLORS = [
  PALETTE.primary.main,
  PALETTE.secondary.main,
  PALETTE.info.main,
  PALETTE.success.main,
  PALETTE.warning.main,
  PALETTE.error.main,
  '#7C3AED',
  PALETTE.grey[500],
] as const;

/** KPIDashboard / TrendAnalysis 用の名前付きチャートカラー */
export const CHART_COLORS = {
  primary: PALETTE.primary.main,
  secondary: PALETTE.secondary.main,
  success: PALETTE.success.main,
  warning: PALETTE.warning.main,
  error: PALETTE.error.main,
  info: PALETTE.info.main,
  processing_volume: PALETTE.primary.main,
  success_rate: PALETTE.success.main,
} as const;

/** CartesianGrid の stroke */
export const GRID_STROKE = PALETTE.grey[200];

/** pass / warn / fail ステータスカラー */
export function getStatusColor(status: 'pass' | 'warn' | 'fail'): string {
  switch (status) {
    case 'pass': return PALETTE.success.main;
    case 'warn': return PALETTE.warning.main;
    case 'fail': return PALETTE.error.main;
  }
}

/** 信頼度 0-1 → カラー (閾値 0.7 / 0.4) */
export function getConfidenceColor(value: number): string {
  if (value >= 0.7) return PALETTE.success.main;
  if (value >= 0.4) return PALETTE.warning.main;
  return PALETTE.error.main;
}

/** KPI ステータスカラー */
export function getKPIStatusColor(status: 'normal' | 'warning' | 'critical'): string | undefined {
  if (status === 'critical') return PALETTE.error.main;
  if (status === 'warning') return PALETTE.warning.main;
  return undefined;
}

/** 搬入予定ステータスカラー */
export const DELIVERY_STATUS_COLORS = {
  scheduled: PALETTE.primary.light,
  delivered: PALETTE.success.main,
  cancelled: PALETTE.error.main,
} as const;

/** 相関係数 → { label, color } */
export function getCorrelationColor(r: number): { label: string; color: string } {
  const abs = Math.abs(r);
  if (abs >= 0.7) return { label: '強い相関', color: PALETTE.error.main };
  if (abs >= 0.4) return { label: '中程度', color: PALETTE.warning.main };
  if (abs >= 0.2) return { label: '弱い相関', color: PALETTE.secondary.main };
  return { label: '相関なし', color: PALETTE.grey[500] };
}
