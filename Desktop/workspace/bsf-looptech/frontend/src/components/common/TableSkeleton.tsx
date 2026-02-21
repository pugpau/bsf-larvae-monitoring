import React from 'react';
import { TableRow, TableCell, Skeleton } from '@mui/material';

interface TableSkeletonProps {
  rows?: number;
  columns: number;
}

const TableSkeleton: React.FC<TableSkeletonProps> = ({ rows = 5, columns }) => (
  <>
    {Array.from({ length: rows }, (_, rowIndex) => (
      <TableRow key={rowIndex}>
        {Array.from({ length: columns }, (_, colIndex) => (
          <TableCell key={colIndex}>
            <Skeleton variant="text" animation="wave" />
          </TableCell>
        ))}
      </TableRow>
    ))}
  </>
);

export default TableSkeleton;
