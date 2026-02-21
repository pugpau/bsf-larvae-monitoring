import React from 'react';
import { TablePagination } from '@mui/material';

interface JaTablePaginationProps {
  count: number;
  page: number;
  rowsPerPage: number;
  onPageChange: (_: unknown, page: number) => void;
  onRowsPerPageChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  rowsPerPageOptions?: number[];
}

const JaTablePagination: React.FC<JaTablePaginationProps> = ({
  rowsPerPageOptions = [25, 50, 100],
  ...props
}) => (
  <TablePagination
    component="div"
    labelRowsPerPage="表示件数:"
    labelDisplayedRows={({ from, to, count }) => `${from}-${to} / ${count}件`}
    rowsPerPageOptions={rowsPerPageOptions}
    {...props}
  />
);

export default JaTablePagination;
