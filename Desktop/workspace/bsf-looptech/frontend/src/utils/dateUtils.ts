/**
 * 日付ユーティリティ — カレンダービュー用
 */
import {
  startOfWeek,
  endOfWeek,
  startOfMonth,
  endOfMonth,
  addDays,
  addWeeks,
  addMonths,
  subWeeks,
  subMonths,
  format,
  isToday as isTodayFns,
  getDay,
} from 'date-fns';
import { ja } from 'date-fns/locale';

export type CalendarPeriod = '1week' | '2weeks' | '1month';

export interface DateRange {
  start: Date;
  end: Date;
}

/** 月曜始まりの週の開始日を取得 */
export function getWeekStart(date: Date): Date {
  return startOfWeek(date, { weekStartsOn: 1 });
}

/** 期間に応じた日付範囲を算出 */
export function getDateRange(referenceDate: Date, period: CalendarPeriod): DateRange {
  switch (period) {
    case '1week': {
      const start = getWeekStart(referenceDate);
      return { start, end: endOfWeek(start, { weekStartsOn: 1 }) };
    }
    case '2weeks': {
      const start = getWeekStart(referenceDate);
      return { start, end: addDays(start, 13) };
    }
    case '1month': {
      const start = startOfMonth(referenceDate);
      return { start, end: endOfMonth(referenceDate) };
    }
  }
}

/** 前/次の期間へ移動 */
export function navigateDate(
  referenceDate: Date,
  period: CalendarPeriod,
  direction: 'prev' | 'next',
): Date {
  switch (period) {
    case '1week':
      return direction === 'next'
        ? addWeeks(referenceDate, 1)
        : subWeeks(referenceDate, 1);
    case '2weeks':
      return direction === 'next'
        ? addWeeks(referenceDate, 2)
        : subWeeks(referenceDate, 2);
    case '1month':
      return direction === 'next'
        ? addMonths(referenceDate, 1)
        : subMonths(referenceDate, 1);
  }
}

/** 日付範囲内の全日付を配列で返す */
export function getDaysInRange(range: DateRange): Date[] {
  const days: Date[] = [];
  let current = range.start;
  while (current <= range.end) {
    days.push(current);
    current = addDays(current, 1);
  }
  return days;
}

/** 月カレンダーグリッド (月曜始まり、null埋め) */
export function getMonthGrid(year: number, month: number): (Date | null)[][] {
  const firstDay = new Date(year, month, 1);
  const lastDay = endOfMonth(firstDay);
  const grid: (Date | null)[][] = [];

  // 月曜=0, 火=1, ... 日=6
  const startDow = (getDay(firstDay) + 6) % 7;
  let week: (Date | null)[] = new Array(startDow).fill(null);

  for (let d = 1; d <= lastDay.getDate(); d++) {
    week.push(new Date(year, month, d));
    if (week.length === 7) {
      grid.push(week);
      week = [];
    }
  }
  if (week.length > 0) {
    while (week.length < 7) week.push(null);
    grid.push(week);
  }
  return grid;
}

/** "2/14(金)" 形式 */
export function formatDateShort(date: Date): string {
  return format(date, 'M/d(E)', { locale: ja });
}

/** "YYYY-MM-DD" 形式 */
export function formatDateISO(date: Date): string {
  return format(date, 'yyyy-MM-dd');
}

/** 今日判定 */
export function isToday(date: Date): boolean {
  return isTodayFns(date);
}

/** 期間ラベル */
export function formatPeriodLabel(range: DateRange, period: CalendarPeriod): string {
  if (period === '1month') {
    return format(range.start, 'yyyy年M月', { locale: ja });
  }
  const startStr = format(range.start, 'yyyy年M月d日', { locale: ja });
  const endStr = format(range.end, 'M月d日', { locale: ja });
  return `${startStr} ~ ${endStr}`;
}
