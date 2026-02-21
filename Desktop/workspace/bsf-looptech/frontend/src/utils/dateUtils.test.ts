/**
 * Unit tests for dateUtils.ts -- calendar view date utility functions.
 *
 * These are pure functions with deterministic outputs, making them
 * ideal candidates for comprehensive unit testing.
 */
import {
  getWeekStart,
  getDateRange,
  navigateDate,
  getDaysInRange,
  getMonthGrid,
  formatDateShort,
  formatDateISO,
  isToday,
  formatPeriodLabel,
  type CalendarPeriod,
  type DateRange,
} from './dateUtils';

// ========================================
//  getWeekStart
// ========================================

describe('getWeekStart', () => {
  it('returns Monday when given a Wednesday', () => {
    // 2026-03-04 is a Wednesday
    const wed = new Date(2026, 2, 4);
    const result = getWeekStart(wed);
    expect(result.getDay()).toBe(1); // Monday
    expect(result.getDate()).toBe(2);
    expect(result.getMonth()).toBe(2); // March
  });

  it('returns the same day when given a Monday', () => {
    // 2026-03-02 is a Monday
    const mon = new Date(2026, 2, 2);
    const result = getWeekStart(mon);
    expect(result.getDay()).toBe(1);
    expect(result.getDate()).toBe(2);
  });

  it('returns previous Monday when given a Sunday', () => {
    // 2026-03-08 is a Sunday
    const sun = new Date(2026, 2, 8);
    const result = getWeekStart(sun);
    expect(result.getDay()).toBe(1);
    expect(result.getDate()).toBe(2);
  });

  it('crosses month boundary correctly', () => {
    // 2026-03-01 is a Sunday -> week start is Feb 23 (Mon)
    const marchFirst = new Date(2026, 2, 1);
    const result = getWeekStart(marchFirst);
    expect(result.getMonth()).toBe(1); // February
    expect(result.getDate()).toBe(23);
  });

  it('crosses year boundary correctly', () => {
    // 2026-01-01 is a Thursday -> week start is Dec 29, 2025 (Mon)
    const newYear = new Date(2026, 0, 1);
    const result = getWeekStart(newYear);
    expect(result.getFullYear()).toBe(2025);
    expect(result.getMonth()).toBe(11); // December
    expect(result.getDate()).toBe(29);
  });
});

// ========================================
//  getDateRange
// ========================================

describe('getDateRange', () => {
  describe('1week period', () => {
    it('returns Monday to Sunday for a given date', () => {
      // 2026-03-04 is Wednesday
      const ref = new Date(2026, 2, 4);
      const range = getDateRange(ref, '1week');
      expect(range.start.getDay()).toBe(1); // Monday
      expect(range.end.getDay()).toBe(0); // Sunday
      // Should be 7 days span
      const diffMs = range.end.getTime() - range.start.getTime();
      const diffDays = Math.round(diffMs / (1000 * 60 * 60 * 24));
      expect(diffDays).toBe(6);
    });

    it('start is Monday of the reference date week', () => {
      const ref = new Date(2026, 2, 6); // Friday
      const range = getDateRange(ref, '1week');
      expect(range.start.getDate()).toBe(2); // Mon Mar 2
    });
  });

  describe('2weeks period', () => {
    it('returns Monday to Sunday+7 (14 days span)', () => {
      const ref = new Date(2026, 2, 4); // Wednesday
      const range = getDateRange(ref, '2weeks');
      expect(range.start.getDay()).toBe(1); // Monday
      const diffMs = range.end.getTime() - range.start.getTime();
      const diffDays = Math.round(diffMs / (1000 * 60 * 60 * 24));
      expect(diffDays).toBe(13); // 14 days = 0..13
    });
  });

  describe('1month period', () => {
    it('returns first day to last day of the month', () => {
      const ref = new Date(2026, 2, 15); // March 15
      const range = getDateRange(ref, '1month');
      expect(range.start.getDate()).toBe(1);
      expect(range.start.getMonth()).toBe(2); // March
      expect(range.end.getDate()).toBe(31);
      expect(range.end.getMonth()).toBe(2); // March
    });

    it('handles February correctly', () => {
      const ref = new Date(2026, 1, 10); // Feb 10, 2026 (non-leap)
      const range = getDateRange(ref, '1month');
      expect(range.start.getDate()).toBe(1);
      expect(range.end.getDate()).toBe(28);
    });

    it('handles February in leap year', () => {
      const ref = new Date(2028, 1, 10); // Feb 10, 2028 (leap)
      const range = getDateRange(ref, '1month');
      expect(range.end.getDate()).toBe(29);
    });
  });
});

// ========================================
//  navigateDate
// ========================================

describe('navigateDate', () => {
  const ref = new Date(2026, 2, 4); // March 4, 2026

  describe('1week', () => {
    it('moves forward by 7 days', () => {
      const result = navigateDate(ref, '1week', 'next');
      expect(result.getDate()).toBe(11);
      expect(result.getMonth()).toBe(2);
    });

    it('moves backward by 7 days', () => {
      const result = navigateDate(ref, '1week', 'prev');
      expect(result.getDate()).toBe(25);
      expect(result.getMonth()).toBe(1); // February
    });
  });

  describe('2weeks', () => {
    it('moves forward by 14 days', () => {
      const result = navigateDate(ref, '2weeks', 'next');
      expect(result.getDate()).toBe(18);
      expect(result.getMonth()).toBe(2);
    });

    it('moves backward by 14 days', () => {
      const result = navigateDate(ref, '2weeks', 'prev');
      expect(result.getDate()).toBe(18);
      expect(result.getMonth()).toBe(1); // February
    });
  });

  describe('1month', () => {
    it('moves forward by 1 month', () => {
      const result = navigateDate(ref, '1month', 'next');
      expect(result.getMonth()).toBe(3); // April
      expect(result.getDate()).toBe(4);
    });

    it('moves backward by 1 month', () => {
      const result = navigateDate(ref, '1month', 'prev');
      expect(result.getMonth()).toBe(1); // February
      expect(result.getDate()).toBe(4);
    });
  });

  it('handles year boundary forward', () => {
    const dec = new Date(2026, 11, 15); // Dec 15
    const result = navigateDate(dec, '1month', 'next');
    expect(result.getFullYear()).toBe(2027);
    expect(result.getMonth()).toBe(0); // January
  });

  it('handles year boundary backward', () => {
    const jan = new Date(2026, 0, 5); // Jan 5
    const result = navigateDate(jan, '1month', 'prev');
    expect(result.getFullYear()).toBe(2025);
    expect(result.getMonth()).toBe(11); // December
  });
});

// ========================================
//  getDaysInRange
// ========================================

describe('getDaysInRange', () => {
  it('returns 7 days for a 1-week range', () => {
    const range: DateRange = {
      start: new Date(2026, 2, 2), // Mon Mar 2
      end: new Date(2026, 2, 8),   // Sun Mar 8
    };
    const days = getDaysInRange(range);
    expect(days).toHaveLength(7);
    expect(days[0].getDate()).toBe(2);
    expect(days[6].getDate()).toBe(8);
  });

  it('returns 14 days for a 2-week range', () => {
    const range: DateRange = {
      start: new Date(2026, 2, 2),
      end: new Date(2026, 2, 15),
    };
    const days = getDaysInRange(range);
    expect(days).toHaveLength(14);
  });

  it('returns 1 day when start equals end', () => {
    const date = new Date(2026, 2, 4);
    const range: DateRange = { start: date, end: date };
    const days = getDaysInRange(range);
    expect(days).toHaveLength(1);
    expect(days[0].getDate()).toBe(4);
  });

  it('handles month boundary crossing', () => {
    const range: DateRange = {
      start: new Date(2026, 1, 27), // Feb 27
      end: new Date(2026, 2, 2),    // Mar 2
    };
    const days = getDaysInRange(range);
    expect(days).toHaveLength(4); // 27, 28, 1, 2
    expect(days[0].getMonth()).toBe(1); // Feb
    expect(days[2].getMonth()).toBe(2); // Mar
  });
});

// ========================================
//  getMonthGrid
// ========================================

describe('getMonthGrid', () => {
  it('returns a grid of weeks for March 2026', () => {
    // March 2026: Sun 1st -> Mon start grid should have null for Mon..Sat before 1st
    // Actually March 1, 2026 is Sunday
    const grid = getMonthGrid(2026, 2); // month index 2 = March
    // Every row has 7 cells
    for (const week of grid) {
      expect(week).toHaveLength(7);
    }
    // Check that March has 31 days accounted for
    const allDates = grid.flat().filter((d): d is Date => d !== null);
    expect(allDates).toHaveLength(31);
  });

  it('starts with nulls when the 1st is not Monday', () => {
    // March 2026: Mar 1 is Sunday -> (getDay(Sun) + 6) % 7 = 6
    // So first row has 6 nulls then the 1st
    const grid = getMonthGrid(2026, 2);
    const firstWeek = grid[0];
    // Count leading nulls
    let nullCount = 0;
    for (const cell of firstWeek) {
      if (cell === null) nullCount++;
      else break;
    }
    expect(nullCount).toBe(6); // Sun is last in Mon-start grid
    expect(firstWeek[6]!.getDate()).toBe(1);
  });

  it('has no leading nulls when the 1st is Monday', () => {
    // June 2026: Jun 1 is Monday
    const grid = getMonthGrid(2026, 5); // month index 5 = June
    const firstWeek = grid[0];
    expect(firstWeek[0]).not.toBeNull();
    expect(firstWeek[0]!.getDate()).toBe(1);
  });

  it('pads last week with nulls', () => {
    // March 2026: 31 days. Last day Mar 31 is Tuesday.
    // In Mon-start grid, Tuesday is index 1.
    // So last row: [30(Mon), 31(Tue), null, null, null, null, null]
    const grid = getMonthGrid(2026, 2);
    const lastWeek = grid[grid.length - 1];
    // After Mar 31, remaining should be null
    const nonNull = lastWeek.filter((d) => d !== null);
    const nulls = lastWeek.filter((d) => d === null);
    expect(nonNull.length + nulls.length).toBe(7);
    expect(nulls.length).toBeGreaterThan(0);
  });

  it('handles February 28 days', () => {
    const grid = getMonthGrid(2026, 1); // Feb 2026
    const allDates = grid.flat().filter((d): d is Date => d !== null);
    expect(allDates).toHaveLength(28);
  });

  it('handles February 29 days (leap year)', () => {
    const grid = getMonthGrid(2028, 1); // Feb 2028 (leap)
    const allDates = grid.flat().filter((d): d is Date => d !== null);
    expect(allDates).toHaveLength(29);
  });
});

// ========================================
//  formatDateShort
// ========================================

describe('formatDateShort', () => {
  it('formats in M/d(E) Japanese locale pattern', () => {
    // 2026-03-04 is Wednesday (水)
    const result = formatDateShort(new Date(2026, 2, 4));
    // Should be like "3/4(水)"
    expect(result).toMatch(/3\/4/);
    expect(result).toContain('(');
    expect(result).toContain(')');
  });

  it('formats single-digit month and day without padding', () => {
    // 2026-01-05 is Monday (月)
    const result = formatDateShort(new Date(2026, 0, 5));
    expect(result).toMatch(/^1\/5\(/);
  });

  it('formats double-digit month and day', () => {
    // 2026-12-25 is Friday (金)
    const result = formatDateShort(new Date(2026, 11, 25));
    expect(result).toMatch(/12\/25/);
  });
});

// ========================================
//  formatDateISO
// ========================================

describe('formatDateISO', () => {
  it('formats as yyyy-MM-dd', () => {
    const result = formatDateISO(new Date(2026, 2, 4));
    expect(result).toBe('2026-03-04');
  });

  it('pads single-digit month and day', () => {
    const result = formatDateISO(new Date(2026, 0, 5));
    expect(result).toBe('2026-01-05');
  });

  it('handles December 31', () => {
    const result = formatDateISO(new Date(2026, 11, 31));
    expect(result).toBe('2026-12-31');
  });

  it('handles January 1', () => {
    const result = formatDateISO(new Date(2026, 0, 1));
    expect(result).toBe('2026-01-01');
  });
});

// ========================================
//  isToday
// ========================================

describe('isToday', () => {
  it('returns true for today', () => {
    expect(isToday(new Date())).toBe(true);
  });

  it('returns false for yesterday', () => {
    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);
    expect(isToday(yesterday)).toBe(false);
  });

  it('returns false for tomorrow', () => {
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    expect(isToday(tomorrow)).toBe(false);
  });

  it('returns false for a distant date', () => {
    expect(isToday(new Date(2020, 0, 1))).toBe(false);
  });
});

// ========================================
//  formatPeriodLabel
// ========================================

describe('formatPeriodLabel', () => {
  it('formats 1month as "yyyy年M月"', () => {
    const range: DateRange = {
      start: new Date(2026, 2, 1),
      end: new Date(2026, 2, 31),
    };
    const result = formatPeriodLabel(range, '1month');
    expect(result).toBe('2026年3月');
  });

  it('formats 1week as "yyyy年M月d日 ~ M月d日"', () => {
    const range: DateRange = {
      start: new Date(2026, 2, 2),
      end: new Date(2026, 2, 8),
    };
    const result = formatPeriodLabel(range, '1week');
    expect(result).toBe('2026年3月2日 ~ 3月8日');
  });

  it('formats 2weeks as date range', () => {
    const range: DateRange = {
      start: new Date(2026, 2, 2),
      end: new Date(2026, 2, 15),
    };
    const result = formatPeriodLabel(range, '2weeks');
    expect(result).toBe('2026年3月2日 ~ 3月15日');
  });

  it('handles cross-month range', () => {
    const range: DateRange = {
      start: new Date(2026, 1, 23),
      end: new Date(2026, 2, 1),
    };
    const result = formatPeriodLabel(range, '1week');
    expect(result).toBe('2026年2月23日 ~ 3月1日');
  });
});

// ========================================
//  Integration: getDateRange + getDaysInRange
// ========================================

describe('getDateRange + getDaysInRange integration', () => {
  it('1week produces exactly 7 days', () => {
    const range = getDateRange(new Date(2026, 2, 4), '1week');
    const days = getDaysInRange(range);
    expect(days).toHaveLength(7);
  });

  it('2weeks produces exactly 14 days', () => {
    const range = getDateRange(new Date(2026, 2, 4), '2weeks');
    const days = getDaysInRange(range);
    expect(days).toHaveLength(14);
  });

  it('1month produces correct day count', () => {
    // March 2026 has 31 days
    const range = getDateRange(new Date(2026, 2, 15), '1month');
    const days = getDaysInRange(range);
    expect(days).toHaveLength(31);
  });
});

// ========================================
//  Integration: navigateDate + getDateRange consistency
// ========================================

describe('navigateDate + getDateRange consistency', () => {
  it('navigating 1week forward then back returns same week', () => {
    const ref = new Date(2026, 2, 4);
    const forward = navigateDate(ref, '1week', 'next');
    const back = navigateDate(forward, '1week', 'prev');
    const originalRange = getDateRange(ref, '1week');
    const roundTripRange = getDateRange(back, '1week');
    expect(formatDateISO(roundTripRange.start)).toBe(formatDateISO(originalRange.start));
    expect(formatDateISO(roundTripRange.end)).toBe(formatDateISO(originalRange.end));
  });

  it('navigating 1month forward then back returns same month', () => {
    const ref = new Date(2026, 2, 15);
    const forward = navigateDate(ref, '1month', 'next');
    const back = navigateDate(forward, '1month', 'prev');
    const originalRange = getDateRange(ref, '1month');
    const roundTripRange = getDateRange(back, '1month');
    expect(formatDateISO(roundTripRange.start)).toBe(formatDateISO(originalRange.start));
    expect(formatDateISO(roundTripRange.end)).toBe(formatDateISO(originalRange.end));
  });
});
