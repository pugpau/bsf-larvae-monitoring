import React from 'react';
import { Box, Typography, Button } from '@mui/material';
import type { SvgIconComponent } from '@mui/icons-material';
import { InboxOutlined as InboxOutlinedIcon } from '@mui/icons-material';

interface EmptyStateProps {
  title: string;
  description?: string;
  icon?: SvgIconComponent;
  actionLabel?: string;
  onAction?: () => void;
}

const EmptyState: React.FC<EmptyStateProps> = ({
  title,
  description,
  icon: Icon = InboxOutlinedIcon,
  actionLabel,
  onAction,
}) => (
  <Box
    sx={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      py: 6,
      px: 2,
    }}
  >
    <Icon sx={{ fontSize: 48, color: 'grey.400', mb: 2 }} />
    <Typography variant="body1" sx={{ fontWeight: 500, mb: 0.5, color: 'text.secondary' }}>
      {title}
    </Typography>
    {description && (
      <Typography variant="body2" sx={{ color: 'text.disabled', mb: 2, textAlign: 'center' }}>
        {description}
      </Typography>
    )}
    {actionLabel && onAction && (
      <Button variant="outlined" size="small" onClick={onAction}>
        {actionLabel}
      </Button>
    )}
  </Box>
);

export default EmptyState;
