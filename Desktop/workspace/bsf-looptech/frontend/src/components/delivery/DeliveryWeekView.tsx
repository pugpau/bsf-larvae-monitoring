/**
 * 週間 / 2週間ビュー — 日ごとの列にカード表示
 */
import React, { useMemo } from 'react';
import {
  Box, Paper, Typography, Chip, Stack, Tooltip,
} from '@mui/material';
import type { DeliverySchedule } from '../../types/api';
import type { CalendarPeriod, DateRange } from '../../utils/dateUtils';
import { getDaysInRange, formatDateShort, formatDateISO, isToday } from '../../utils/dateUtils';
import { PALETTE, DELIVERY_STATUS_COLORS } from '../../constants/colors';

interface DeliveryWeekViewProps {
  period: CalendarPeriod;
  dateRange: DateRange;
  itemsByDate: Map<string, DeliverySchedule[]>;
  loading: boolean;
  onDayClick: (dateISO: string) => void;
}

const STATUS_SHORT: Record<string, string> = {
  scheduled: '予定',
  delivered: '済',
  cancelled: '取消',
};

const DeliveryWeekView: React.FC<DeliveryWeekViewProps> = ({
  period,
  dateRange,
  itemsByDate,
  loading,
  onDayClick,
}) => {
  const days = useMemo(() => getDaysInRange(dateRange), [dateRange]);
  const is2Weeks = period === '2weeks';

  // 2週間: 2行に分割
  const rows = useMemo(() => {
    if (!is2Weeks) return [days];
    return [days.slice(0, 7), days.slice(7)];
  }, [days, is2Weeks]);

  return (
    <Box>
      {rows.map((weekDays, rowIdx) => (
        <Box
          key={rowIdx}
          sx={{
            display: 'flex',
            gap: '1px',
            mb: is2Weeks ? 1 : 0,
            bgcolor: PALETTE.grey[200],
            border: `1px solid ${PALETTE.grey[200]}`,
            borderRadius: 1,
            overflow: 'hidden',
          }}
        >
          {weekDays.map((day) => {
            const dateKey = formatDateISO(day);
            const dayItems = itemsByDate.get(dateKey) || [];
            const today = isToday(day);
            const dow = day.getDay();
            const isWeekend = dow === 0 || dow === 6;

            return (
              <DayColumn
                key={dateKey}
                date={day}
                dateKey={dateKey}
                items={dayItems}
                isToday={today}
                isWeekend={isWeekend}
                compact={is2Weeks}
                loading={loading}
                onClick={() => onDayClick(dateKey)}
              />
            );
          })}
        </Box>
      ))}
    </Box>
  );
};

interface DayColumnProps {
  date: Date;
  dateKey: string;
  items: DeliverySchedule[];
  isToday: boolean;
  isWeekend: boolean;
  compact: boolean;
  loading: boolean;
  onClick: () => void;
}

const DayColumn: React.FC<DayColumnProps> = ({
  date,
  dateKey,
  items,
  isToday: today,
  isWeekend,
  compact,
  loading,
  onClick,
}) => {
  const statusCounts = useMemo(() => {
    const counts = { scheduled: 0, delivered: 0, cancelled: 0 };
    for (const item of items) {
      if (item.status in counts) {
        counts[item.status as keyof typeof counts]++;
      }
    }
    return counts;
  }, [items]);

  const bgColor = today
    ? `${PALETTE.primary.light}12`
    : isWeekend
      ? PALETTE.grey[50]
      : 'background.paper';

  return (
    <Box
      sx={{
        flex: '1 1 0',
        minWidth: compact ? 110 : 150,
        bgcolor: bgColor,
        display: 'flex',
        flexDirection: 'column',
        cursor: 'pointer',
        '&:hover': { bgcolor: PALETTE.grey[100] },
      }}
      onClick={onClick}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onClick();
        }
      }}
      role="button"
      tabIndex={0}
      aria-label={`${formatDateShort(date)} ${items.length}件の搬入予定`}
    >
      {/* Day header */}
      <Box
        sx={{
          px: 1,
          py: 0.5,
          borderBottom: today
            ? `2px solid ${PALETTE.primary.main}`
            : `1px solid ${PALETTE.grey[200]}`,
          bgcolor: today ? `${PALETTE.primary.light}18` : PALETTE.grey[50],
        }}
      >
        <Typography
          variant="caption"
          sx={{
            fontFamily: "'Fira Code', monospace",
            fontWeight: today ? 700 : 400,
            color: today ? PALETTE.primary.main : PALETTE.grey[700],
            fontSize: '0.75rem',
          }}
        >
          {formatDateShort(date)}
        </Typography>
        {items.length > 0 && (
          <Stack direction="row" spacing={0.5} sx={{ mt: 0.25, flexWrap: 'wrap', gap: 0.25 }}>
            <Chip
              label={`${items.length}件`}
              size="small"
              sx={{
                height: 18,
                fontSize: '0.65rem',
                fontFamily: "'Fira Code', monospace",
                bgcolor: PALETTE.grey[200],
                color: PALETTE.grey[700],
              }}
            />
            {!compact && statusCounts.delivered > 0 && (
              <Chip
                label={`${statusCounts.delivered}${STATUS_SHORT.delivered}`}
                size="small"
                sx={{
                  height: 18,
                  fontSize: '0.6rem',
                  bgcolor: PALETTE.success.light,
                  color: PALETTE.success.dark,
                }}
              />
            )}
            {!compact && statusCounts.cancelled > 0 && (
              <Chip
                label={`${statusCounts.cancelled}${STATUS_SHORT.cancelled}`}
                size="small"
                sx={{
                  height: 18,
                  fontSize: '0.6rem',
                  bgcolor: PALETTE.error.light,
                  color: PALETTE.error.dark,
                }}
              />
            )}
          </Stack>
        )}
      </Box>

      {/* Scrollable items */}
      <Box
        sx={{
          flex: 1,
          overflowY: 'auto',
          maxHeight: compact ? 'calc(40vh - 60px)' : 'calc(75vh - 200px)',
          p: 0.5,
        }}
      >
        {loading ? (
          <Box sx={{ p: 1 }}>
            <Typography variant="caption" color="text.secondary">
              ...
            </Typography>
          </Box>
        ) : items.length === 0 ? (
          <Box sx={{ p: 1, textAlign: 'center' }}>
            <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
              -
            </Typography>
          </Box>
        ) : (
          items.map((item) => (
            <ItemCard key={item.id} item={item} compact={compact} />
          ))
        )}
      </Box>
    </Box>
  );
};

interface ItemCardProps {
  item: DeliverySchedule;
  compact: boolean;
}

const ItemCard: React.FC<ItemCardProps> = ({ item, compact }) => {
  const borderColor = DELIVERY_STATUS_COLORS[item.status] || PALETTE.grey[400];

  if (compact) {
    return (
      <Tooltip
        title={`${item.supplier_name || ''} / ${item.material_category || ''} / ${item.material_name || ''}`}
        arrow
        placement="top"
      >
        <Paper
          variant="outlined"
          sx={{
            px: 0.5,
            py: 0.25,
            mb: 0.25,
            borderLeft: `3px solid ${borderColor}`,
            borderColor: PALETTE.grey[200],
            fontSize: '0.65rem',
            lineHeight: 1.3,
            overflow: 'hidden',
            whiteSpace: 'nowrap',
            textOverflow: 'ellipsis',
          }}
        >
          <Typography
            variant="caption"
            sx={{ fontSize: '0.65rem', fontWeight: 500, display: 'block' }}
            noWrap
          >
            {item.material_name || '-'}
          </Typography>
          <Typography
            variant="caption"
            sx={{
              fontSize: '0.6rem',
              fontFamily: "'Fira Code', monospace",
              color: PALETTE.grey[500],
            }}
          >
            {item.estimated_weight != null
              ? `${item.estimated_weight}${item.weight_unit}`
              : '-'}
          </Typography>
        </Paper>
      </Tooltip>
    );
  }

  return (
    <Paper
      variant="outlined"
      sx={{
        px: 1,
        py: 0.5,
        mb: 0.5,
        borderLeft: `3px solid ${borderColor}`,
        borderColor: PALETTE.grey[200],
        '&:hover': { bgcolor: PALETTE.grey[50] },
      }}
    >
      <Typography
        variant="caption"
        sx={{ fontSize: '0.7rem', color: PALETTE.grey[500], display: 'block' }}
        noWrap
      >
        {item.supplier_name || '-'}
      </Typography>
      <Typography
        variant="caption"
        sx={{ fontSize: '0.75rem', fontWeight: 600, display: 'block' }}
        noWrap
      >
        {item.material_name || '-'}
      </Typography>
      <Stack direction="row" spacing={0.5} alignItems="center">
        <Chip
          label={item.material_category || '-'}
          size="small"
          variant="outlined"
          sx={{ height: 16, fontSize: '0.6rem' }}
        />
        <Typography
          variant="caption"
          sx={{
            fontFamily: "'Fira Code', monospace",
            fontSize: '0.7rem',
            color: PALETTE.grey[600],
          }}
        >
          {item.estimated_weight != null
            ? `${item.estimated_weight}${item.weight_unit}`
            : '-'}
        </Typography>
      </Stack>
    </Paper>
  );
};

export default DeliveryWeekView;
