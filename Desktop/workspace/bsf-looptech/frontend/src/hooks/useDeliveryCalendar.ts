/**
 * カレンダー状態管理フック — 搬入予定カレンダービュー用
 */
import { useState, useEffect, useCallback, useMemo } from 'react';
import type { DeliverySchedule } from '../types/api';
import { fetchDeliverySchedules } from '../api/deliveryApi';
import {
  type CalendarPeriod,
  type DateRange,
  getDateRange,
  navigateDate,
  formatDateISO,
} from '../utils/dateUtils';

export interface UseDeliveryCalendarReturn {
  period: CalendarPeriod;
  setPeriod: (p: CalendarPeriod) => void;
  referenceDate: Date;
  dateRange: DateRange;
  navigatePrev: () => void;
  navigateNext: () => void;
  navigateToday: () => void;
  items: DeliverySchedule[];
  loading: boolean;
  itemsByDate: Map<string, DeliverySchedule[]>;
  selectedDate: string | null;
  setSelectedDate: (date: string | null) => void;
  selectedDateItems: DeliverySchedule[];
  statusFilter: string | null;
  setStatusFilter: (s: string | null) => void;
  reload: () => void;
}

export function useDeliveryCalendar(): UseDeliveryCalendarReturn {
  const [period, setPeriod] = useState<CalendarPeriod>('1week');
  const [referenceDate, setReferenceDate] = useState<Date>(new Date());
  const [items, setItems] = useState<DeliverySchedule[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string | null>(null);

  const dateRange = useMemo(
    () => getDateRange(referenceDate, period),
    [referenceDate, period],
  );

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const maxItems = period === '1month' ? 1550 : 1000;
      const result = await fetchDeliverySchedules({
        date_from: formatDateISO(dateRange.start),
        date_to: formatDateISO(dateRange.end),
        limit: maxItems,
        offset: 0,
        sort_by: 'scheduled_date',
        sort_order: 'asc',
      });
      setItems(result.items);
    } catch {
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, [dateRange, period]);

  useEffect(() => {
    load();
  }, [load]);

  const filteredItems = useMemo(() => {
    if (!statusFilter) return items;
    return items.filter((item) => item.status === statusFilter);
  }, [items, statusFilter]);

  const itemsByDate = useMemo(() => {
    const map = new Map<string, DeliverySchedule[]>();
    for (const item of filteredItems) {
      const key = item.scheduled_date;
      if (!map.has(key)) {
        map.set(key, []);
      }
      map.get(key)!.push(item);
    }
    return map;
  }, [filteredItems]);

  const selectedDateItems = useMemo(() => {
    if (!selectedDate) return [];
    return itemsByDate.get(selectedDate) || [];
  }, [selectedDate, itemsByDate]);

  const navigatePrev = useCallback(() => {
    setReferenceDate((prev) => navigateDate(prev, period, 'prev'));
  }, [period]);

  const navigateNext = useCallback(() => {
    setReferenceDate((prev) => navigateDate(prev, period, 'next'));
  }, [period]);

  const navigateToday = useCallback(() => {
    setReferenceDate(new Date());
  }, []);

  return {
    period,
    setPeriod,
    referenceDate,
    dateRange,
    navigatePrev,
    navigateNext,
    navigateToday,
    items: filteredItems,
    loading,
    itemsByDate,
    selectedDate,
    setSelectedDate,
    selectedDateItems,
    statusFilter,
    setStatusFilter,
    reload: load,
  };
}
