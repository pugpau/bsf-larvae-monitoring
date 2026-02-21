import { useState, useEffect, useCallback, useRef } from 'react';
import { useNotification } from './useNotification';
import { downloadBlob } from '../api/materialsApi';
import type { PaginatedResponse } from '../types/api';

interface CrudApiFunctions<T> {
  fetch: (params: Record<string, unknown>) => Promise<PaginatedResponse<T>>;
  create: (data: Record<string, unknown>) => Promise<T>;
  update: (id: string, data: Record<string, unknown>) => Promise<T>;
  remove: (id: string) => Promise<void>;
  exportCsv: () => Promise<Blob>;
  importCsv: (file: File) => Promise<{ imported: number; skipped: number; errors: string[] }>;
}

interface UseCrudListReturn<T, F extends Record<string, string>> {
  items: T[];
  total: number;
  loading: boolean;
  searchQuery: string;
  page: number;
  rowsPerPage: number;
  formOpen: boolean;
  editId: string | null;
  form: F;
  deleteTarget: T | null;
  deleteDialogOpen: boolean;
  notification: ReturnType<typeof useNotification>['notification'];
  closeNotification: () => void;
  fileInputRef: React.RefObject<HTMLInputElement>;
  load: () => void;
  handleSearchChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  handlePageChange: (_: unknown, newPage: number) => void;
  handleRowsPerPageChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  handleExport: (filename: string) => void;
  handleImport: (e: React.ChangeEvent<HTMLInputElement>) => void;
  handleOpenNew: () => void;
  handleOpenEdit: (id: string, formData: F) => void;
  handleSave: (payload: Record<string, unknown>) => Promise<void>;
  handleDeleteClick: (item: T) => void;
  handleDeleteConfirm: () => void;
  handleDeleteCancel: () => void;
  handleFieldChange: (field: string) => (e: React.ChangeEvent<HTMLInputElement>) => void;
  handleFieldSet: (field: string, value: string) => void;
  setFormOpen: (open: boolean) => void;
}

const ROWS_PER_PAGE_OPTIONS = [25, 50, 100];

export { ROWS_PER_PAGE_OPTIONS };

export function useCrudList<T extends { id: string }, F extends Record<string, string>>(
  api: CrudApiFunctions<T>,
  emptyForm: F,
): UseCrudListReturn<T, F> {
  const [items, setItems] = useState<T[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);
  const [formOpen, setFormOpen] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [form, setForm] = useState<F>(emptyForm);
  const [deleteTarget, setDeleteTarget] = useState<T | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { notification, notify, closeNotification } = useNotification();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const result = await api.fetch({
        q: searchQuery || undefined,
        limit: rowsPerPage,
        offset: page * rowsPerPage,
      });
      setItems(result.items);
      setTotal(result.total);
    } catch {
      notify('データの読み込みに失敗しました', 'error');
    } finally {
      setLoading(false);
    }
  }, [searchQuery, page, rowsPerPage, api, notify]);

  useEffect(() => { load(); }, [load]);

  const handleSearchChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(e.target.value);
    setPage(0);
  }, []);

  const handlePageChange = useCallback((_: unknown, newPage: number) => {
    setPage(newPage);
  }, []);

  const handleRowsPerPageChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(e.target.value, 10));
    setPage(0);
  }, []);

  const handleExport = useCallback(async (filename: string) => {
    try {
      const blob = await api.exportCsv();
      downloadBlob(blob, filename);
      notify('CSVをエクスポートしました');
    } catch {
      notify('エクスポートに失敗しました', 'error');
    }
  }, [api, notify]);

  const handleImport = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 10 * 1024 * 1024) {
      notify('ファイルサイズが大きすぎます（最大10MB）', 'error');
      if (fileInputRef.current) fileInputRef.current.value = '';
      return;
    }
    try {
      const result = await api.importCsv(file);
      const msg = `${result.imported}件インポート, ${result.skipped}件スキップ`;
      notify(msg, result.errors.length > 0 ? 'error' : 'success');
      load();
    } catch {
      notify('インポートに失敗しました', 'error');
    } finally {
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  }, [api, notify, load]);

  const handleOpenNew = useCallback(() => {
    setEditId(null);
    setForm(emptyForm);
    setFormOpen(true);
  }, [emptyForm]);

  const handleOpenEdit = useCallback((id: string, formData: F) => {
    setEditId(id);
    setForm(formData);
    setFormOpen(true);
  }, []);

  const handleSave = useCallback(async (payload: Record<string, unknown>) => {
    try {
      if (editId) {
        await api.update(editId, payload);
        notify('更新しました');
      } else {
        await api.create(payload);
        notify('登録しました');
      }
      setFormOpen(false);
      load();
    } catch {
      notify('保存に失敗しました', 'error');
    }
  }, [editId, api, notify, load]);

  const handleDeleteClick = useCallback((item: T) => {
    setDeleteTarget(item);
    setDeleteDialogOpen(true);
  }, []);

  const handleDeleteConfirm = useCallback(async () => {
    if (!deleteTarget) return;
    try {
      await api.remove(deleteTarget.id);
      setDeleteDialogOpen(false);
      setDeleteTarget(null);
      notify('削除しました');
      load();
    } catch {
      notify('削除に失敗しました', 'error');
    }
  }, [deleteTarget, api, notify, load]);

  const handleDeleteCancel = useCallback(() => {
    setDeleteDialogOpen(false);
    setDeleteTarget(null);
  }, []);

  const handleFieldChange = useCallback((field: string) => (e: React.ChangeEvent<HTMLInputElement>) => {
    setForm(prev => ({ ...prev, [field]: e.target.value }));
  }, []);

  const handleFieldSet = useCallback((field: string, value: string) => {
    setForm(prev => ({ ...prev, [field]: value }));
  }, []);

  return {
    items, total, loading, searchQuery, page, rowsPerPage,
    formOpen, editId, form, deleteTarget, deleteDialogOpen,
    notification, closeNotification, fileInputRef,
    load, handleSearchChange, handlePageChange, handleRowsPerPageChange,
    handleExport, handleImport, handleOpenNew, handleOpenEdit, handleSave,
    handleDeleteClick, handleDeleteConfirm, handleDeleteCancel,
    handleFieldChange, handleFieldSet, setFormOpen,
  };
}
