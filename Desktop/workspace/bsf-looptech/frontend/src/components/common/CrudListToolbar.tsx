import React from 'react';
import {
  Box, Typography, Stack, TextField, IconButton, Button,
  InputAdornment, Tooltip,
} from '@mui/material';
import {
  Add as AddIcon,
  Search as SearchIcon,
  FileDownload as ExportIcon,
  FileUpload as ImportIcon,
} from '@mui/icons-material';

interface CrudListToolbarProps {
  title: string;
  searchQuery: string;
  onSearchChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onExport: () => void;
  onImportClick: () => void;
  onNewClick: () => void;
  fileInputRef: React.RefObject<HTMLInputElement>;
  onFileChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
}

const CrudListToolbar: React.FC<CrudListToolbarProps> = ({
  title, searchQuery, onSearchChange, onExport, onImportClick,
  onNewClick, fileInputRef, onFileChange,
}) => (
  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
    <Typography variant="h2">{title}</Typography>
    <Stack direction="row" spacing={1} alignItems="center">
      <TextField
        placeholder="検索..."
        value={searchQuery}
        onChange={onSearchChange}
        size="small"
        sx={{ width: 220 }}
        InputProps={{
          startAdornment: (
            <InputAdornment position="start">
              <SearchIcon fontSize="small" color="action" />
            </InputAdornment>
          ),
        }}
      />
      <Tooltip title="CSVエクスポート">
        <IconButton size="small" onClick={onExport} color="primary" aria-label="CSVエクスポート">
          <ExportIcon />
        </IconButton>
      </Tooltip>
      <Tooltip title="CSVインポート">
        <IconButton size="small" onClick={onImportClick} color="primary" aria-label="CSVインポート">
          <ImportIcon />
        </IconButton>
      </Tooltip>
      <input ref={fileInputRef} type="file" accept=".csv" style={{ display: 'none' }} onChange={onFileChange} />
      <Button variant="contained" startIcon={<AddIcon />} size="small" onClick={onNewClick}>
        新規登録
      </Button>
    </Stack>
  </Box>
);

export default CrudListToolbar;
