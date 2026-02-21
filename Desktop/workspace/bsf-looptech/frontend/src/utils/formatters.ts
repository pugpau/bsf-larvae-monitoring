/**
 * 数値フォーマッター — コンポーネント内の散在するフォーマット処理を一元化
 */

/** 濃度値 (mg/L) → 小数4桁 */
export function formatConcentration(n: number): string {
  return n.toFixed(4);
}

/** パーセンテージ (表示用、%付き) */
export function formatPercentage(n: number): string {
  return `${n.toFixed(1)}%`;
}

/** パーセンテージ (値のみ、%なし) */
export function formatPercentageValue(n: number): string {
  return n.toFixed(1);
}

/** 通貨 (円) */
export function formatCurrency(n: number): string {
  return `${n.toLocaleString()}円`;
}

/** 件数 */
export function formatCount(n: number): string {
  return n.toLocaleString();
}

/** 汎用小数フォーマッター */
export function formatDecimal(n: number, places: number): string {
  return n.toFixed(places);
}

/** KPIDashboard の formatValue 置換 */
export function formatKPIValue(value: number, unit: string): string {
  if (unit === '%') return value.toFixed(1);
  if (unit === '円') return value.toLocaleString();
  if (unit === '時間') return value.toFixed(1);
  return String(value);
}
