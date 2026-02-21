import React from 'react';
import {
  Dialog, DialogTitle, DialogContent, DialogActions,
  Button, Typography,
} from '@mui/material';

interface ConfirmDeleteDialogProps {
  open: boolean;
  targetName: string | undefined;
  onConfirm: () => void;
  onCancel: () => void;
}

const ConfirmDeleteDialog: React.FC<ConfirmDeleteDialogProps> = ({
  open, targetName, onConfirm, onCancel,
}) => (
  <Dialog open={open} onClose={onCancel}>
    <DialogTitle>削除確認</DialogTitle>
    <DialogContent>
      <Typography>{targetName ? `「${targetName}」を削除しますか？` : '削除しますか？'}</Typography>
    </DialogContent>
    <DialogActions>
      <Button onClick={onCancel}>キャンセル</Button>
      <Button onClick={onConfirm} color="error" variant="contained">削除</Button>
    </DialogActions>
  </Dialog>
);

export default ConfirmDeleteDialog;
