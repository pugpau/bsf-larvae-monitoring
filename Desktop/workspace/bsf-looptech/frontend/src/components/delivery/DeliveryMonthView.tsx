/**
 * 月間カレンダービュー — 日ごとの件数表示 + ミニステータスバー
 */
import React, { useMemo } from 'react';
import {
  Box, Paper, Typography, Grid,
} from '@mui/material';
import type { DeliverySchedule } from '../../types/api';
import { getMonthGrid, formatDateISO, isToday } from '../../utils/dateUtils';
import type { DateRange } from '../../utils/dateUtils';
import { PALETTE, DELIVERY_STATUS_COLORS } from '../../constants/colors';

interface DeliveryMonthViewProps {
  dateRange: DateRange;
  itemsByDate: Map<string, DeliverySchedule[]>;
  loading: boolean;
  onDayClick: (dateISO: string) => void;
}

const DOW_LABELS = ['月', '火', '水', '木', '金', '土', '日'] as const;

const DeliveryMonthView: React.FC<DeliveryMonthViewProps> = ({
  dateRange,
  itemsByDate,
  loading,
  onDayClick,
}) => {
  const year = dateRange.start.getFullYear();
  const month = dateRange.start.getMonth();
  const grid = useMemo(() => getMonthGrid(year, month), [year, month]);

  return (
    <Box>
      {/* Day-of-week header */}
      <Grid container spacing={0} sx={{ mb: 0.5 }}>
        {DOW_LABELS.map((label, i) => (
          <Grid item xs={12 / 7} key={label}>
            <Box
              sx={{
                textAlign: 'center',
                py: 0.5,
                bgcolor: PALETTE.grey[100],
                borderRadius: i === 0 ? '4px 0 0 0' : i === 6 ? '0 4px 0 0' : 0,
              }}
            >
              <Typography
                variant="caption"
                sx={{
                  fontWeight: 600,
                  fontSize: '0.75rem',
                  color: i >= 5 ? PALETTE.grey[400] : PALETTE.grey[700],
                }}
              >
                {label}
              </Typography>
            </Box>
          </Grid>
        ))}
      </Grid>

      {/* Calendar grid */}
      {grid.map((week, weekIdx) => (
        <Grid container spacing={0} key={weekIdx} sx={{ borderBottom: `1px solid ${PALETTE.grey[200]}` }}>
          {week.map((day, dayIdx) => {
            if (!day) {
              return (
                <Grid item xs={12 / 7} key={`empty-${dayIdx}`}>
                  <Box sx={{ minHeight: 80, bgcolor: PALETTE.grey[50], borderRight: `1px solid ${PALETTE.grey[200]}` }} />
                </Grid>
              );
            }

            const dateKey = formatDateISO(day);
            const dayItems = itemsByDate.get(dateKey) || [];
            const today = isToday(day);
            const count = dayItems.length;
            const dow = dayIdx;
            const isWeekend = dow >= 5;

            const sc = { scheduled: 0, delivered: 0, cancelled: 0 };
            for (const it of dayItems) {
              const s = it.status as keyof typeof sc;
              if (s in sc) sc[s]++;
            }
            const { scheduled, delivered, cancelled } = sc;

            return (
              <Grid item xs={12 / 7} key={dateKey}>
                <Paper
                  variant="outlined"
                  sx={{
                    minHeight: 80,
                    p: 0.5,
                    cursor: 'pointer',
                    borderRadius: 0,
                    borderRight: `1px solid ${PALETTE.grey[200]}`,
                    borderBottom: 'none',
                    bgcolor: today
                      ? `${PALETTE.primary.light}10`
                      : isWeekend
                        ? PALETTE.grey[50]
                        : 'background.paper',
                    outline: today ? `2px solid ${PALETTE.primary.main}` : 'none',
                    outlineOffset: -2,
                    '&:hover': {
                      bgcolor: PALETTE.grey[100],
                    },
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                  }}
                  onClick={() => onDayClick(dateKey)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      onDayClick(dateKey);
                    }
                  }}
                  role="button"
                  tabIndex={0}
                  aria-label={`${day.getMonth() + 1}月${day.getDate()}日 ${count}件の搬入予定`}
                >
                  {/* Date number */}
                  <Typography
                    variant="caption"
                    sx={{
                      fontFamily: "'Fira Code', monospace",
                      fontWeight: today ? 700 : 400,
                      fontSize: '0.8rem',
                      color: today
                        ? PALETTE.primary.main
                        : isWeekend
                          ? PALETTE.grey[400]
                          : PALETTE.grey[700],
                    }}
                  >
                    {day.getDate()}
                  </Typography>

                  {/* Count */}
                  {!loading && count > 0 && (
                    <Typography
                      sx={{
                        fontFamily: "'Fira Code', monospace",
                        fontSize: '1.25rem',
                        fontWeight: 700,
                        textAlign: 'center',
                        color: getDensityColor(count),
                        lineHeight: 1.2,
                      }}
                    >
                      {count}
                    </Typography>
                  )}

                  {/* Mini status bar */}
                  {!loading && count > 0 && (
                    <Box
                      sx={{
                        display: 'flex',
                        height: 4,
                        borderRadius: 2,
                        overflow: 'hidden',
                        mt: 'auto',
                      }}
                    >
                      {scheduled > 0 && (
                        <Box
                          sx={{
                            width: `${(scheduled / count) * 100}%`,
                            bgcolor: DELIVERY_STATUS_COLORS.scheduled,
                          }}
                        />
                      )}
                      {delivered > 0 && (
                        <Box
                          sx={{
                            width: `${(delivered / count) * 100}%`,
                            bgcolor: DELIVERY_STATUS_COLORS.delivered,
                          }}
                        />
                      )}
                      {cancelled > 0 && (
                        <Box
                          sx={{
                            width: `${(cancelled / count) * 100}%`,
                            bgcolor: DELIVERY_STATUS_COLORS.cancelled,
                          }}
                        />
                      )}
                    </Box>
                  )}
                </Paper>
              </Grid>
            );
          })}
        </Grid>
      ))}

      {/* Legend */}
      <Box sx={{ display: 'flex', gap: 2, mt: 1, justifyContent: 'flex-end' }}>
        <LegendItem color={DELIVERY_STATUS_COLORS.scheduled} label="予定" />
        <LegendItem color={DELIVERY_STATUS_COLORS.delivered} label="搬入済" />
        <LegendItem color={DELIVERY_STATUS_COLORS.cancelled} label="キャンセル" />
      </Box>
    </Box>
  );
};

function getDensityColor(count: number): string {
  if (count >= 50) return PALETTE.primary.dark;
  if (count >= 20) return PALETTE.primary.main;
  return PALETTE.primary.light;
}

const LegendItem: React.FC<{ color: string; label: string }> = ({ color, label }) => (
  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
    <Box
      sx={{
        width: 12,
        height: 4,
        borderRadius: 2,
        bgcolor: color,
      }}
    />
    <Typography variant="caption" sx={{ fontSize: '0.7rem', color: PALETTE.grey[500] }}>
      {label}
    </Typography>
  </Box>
);

export default DeliveryMonthView;
