import React, { useState, useEffect } from 'react';
import { 
  Box, 
  Button, 
  TextField, 
  Typography, 
  Select, 
  MenuItem, 
  FormControl, 
  InputLabel, 
  Grid,
  IconButton,
  Snackbar,
  Alert,
  FormHelperText
} from '@mui/material';
import { Add as AddIcon, Delete as DeleteIcon } from '@mui/icons-material';
import axios from 'axios';

// SubstrateTypeEnum に対応する型
const SubstrateTypeOptions = [
  { value: 'sewage_sludge', label: '下水汚泥' },
  { value: 'pig_manure', label: '豚の糞尿' },
  { value: 'chicken_manure', label: '鶏糞' },
  { value: 'sawdust', label: 'おが屑' },
  { value: 'other', label: 'その他' }
];

const SubstrateTypeForm = ({ initialData, onSubmitSuccess }) => {
  const [id, setId] = useState('');
  const [name, setName] = useState('');
  const [type, setType] = useState('');
  const [description, setDescription] = useState('');
  const [attributes, setAttributes] = useState([]);
  const [openSnackbar, setOpenSnackbar] = useState(false);
  const [snackbarMessage, setSnackbarMessage] = useState('');
  const [snackbarSeverity, setSnackbarSeverity] = useState('success'); // 'success' or 'error'
  const [isEditing, setIsEditing] = useState(false);
  
  // バリデーション状態
  const [errors, setErrors] = useState({
    name: '',
    type: '',
    attributes: []
  });

  // 初期データがある場合はフォームに設定
  useEffect(() => {
    if (initialData) {
      setId(initialData.id || '');
      setName(initialData.name || '');
      setType(initialData.type || '');
      setDescription(initialData.description || '');
      setAttributes(initialData.attributes || []);
      setIsEditing(true);
    } else {
      resetForm();
      setIsEditing(false);
    }
  }, [initialData]);

  const resetForm = () => {
    setId('');
    setName('');
    setType('');
    setDescription('');
    setAttributes([]);
  };

  const addAttribute = () => {
    setAttributes([...attributes, { name: '', value: '', unit: '' }]);
  };

  const updateAttribute = (index, field, value) => {
    const newAttributes = [...attributes];
    // 値が数値の場合は文字列に変換
    if (field === 'value' && typeof value === 'number') {
      newAttributes[index][field] = String(value);
    } else {
      newAttributes[index][field] = value;
    }
    setAttributes(newAttributes);
  };

  const removeAttribute = (index) => {
    const newAttributes = attributes.filter((_, i) => i !== index);
    setAttributes(newAttributes);
  };

  // フォームバリデーション
  const validateForm = () => {
    const newErrors = {
      name: '',
      type: '',
      attributes: Array(attributes.length).fill('')
    };
    
    let isValid = true;
    
    // 名前のバリデーション
    if (!name.trim()) {
      newErrors.name = '基質タイプ名は必須です';
      isValid = false;
    } else if (name.length > 50) {
      newErrors.name = '基質タイプ名は50文字以内で入力してください';
      isValid = false;
    }
    
    // タイプのバリデーション
    if (!type) {
      newErrors.type = '基質カテゴリは必須です';
      isValid = false;
    }
    
    // 属性のバリデーション
    attributes.forEach((attr, index) => {
      if (attr.name.trim() && (attr.value === '' || attr.value === null || attr.value === undefined)) {
        newErrors.attributes[index] = '属性に値を入力してください';
        isValid = false;
      } else if (attr.value && !attr.name.trim()) {
        newErrors.attributes[index] = '属性名を入力してください';
        isValid = false;
      }
    });
    
    setErrors(newErrors);
    return isValid;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // フォームバリデーション
    if (!validateForm()) {
      setSnackbarMessage('入力内容に誤りがあります。修正してください。');
      setSnackbarSeverity('error');
      setOpenSnackbar(true);
      return;
    }
    
    // 属性値を文字列に変換
    const processedAttributes = attributes.map(attr => ({
      ...attr,
      value: attr.value !== null && attr.value !== undefined ? String(attr.value) : ''
    }));
    
    const data = {
      name,
      type,
      description,
      attributes: processedAttributes
    };

    console.log('送信データ:', data);

    try {
      // モックデータ処理
      if (isEditing) {
        // 更新処理（実際にはAPIに送信せず、成功したと見なす）
        console.log('基質タイプ更新:', id, data);
        setSnackbarMessage('基質タイプを更新しました。');
      } else {
        // 新規作成（実際にはAPIに送信せず、成功したと見なす）
        console.log('基質タイプ登録:', data);
        setSnackbarMessage('基質タイプを登録しました。');
      }
      
      setSnackbarSeverity('success');
      setOpenSnackbar(true);
      resetForm();
      
      if (onSubmitSuccess) {
        onSubmitSuccess();
      }
    } catch (error) {
      console.error('基質タイプ操作エラー:', error);
      
      // エラーメッセージ
      let errorMessage = isEditing ? '基質タイプの更新に失敗しました。' : '基質タイプの登録に失敗しました。';
      
      setSnackbarMessage(errorMessage);
      setSnackbarSeverity('error');
      setOpenSnackbar(true);
    }
  };

  const handleCancel = () => {
    resetForm();
    if (onSubmitSuccess) {
      onSubmitSuccess();
    }
  };

  const handleSnackbarClose = (event, reason) => {
    if (reason === 'clickaway') {
      return;
    }
    setOpenSnackbar(false);
  };

  return (
    <Box component="form" onSubmit={handleSubmit} sx={{ maxWidth: 600, margin: 'auto', p: 2 }}>
      <Typography variant="h6" gutterBottom>
        {isEditing ? '基質タイプ編集' : '基質タイプ登録'}
      </Typography>
      
      <Grid container spacing={2}>
        <Grid item xs={12}>
          <TextField
            fullWidth
            label="基質タイプ名"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            error={!!errors.name}
            helperText={errors.name}
            onBlur={() => {
              if (!name.trim()) {
                setErrors({...errors, name: '基質タイプ名は必須です'});
              } else if (name.length > 50) {
                setErrors({...errors, name: '基質タイプ名は50文字以内で入力してください'});
              } else {
                setErrors({...errors, name: ''});
              }
            }}
          />
        </Grid>
        
        <Grid item xs={12}>
          <FormControl fullWidth error={!!errors.type}>
            <InputLabel>基質カテゴリ</InputLabel>
            <Select
              value={type}
              label="基質カテゴリ"
              onChange={(e) => {
                setType(e.target.value);
                if (e.target.value) {
                  setErrors({...errors, type: ''});
                }
              }}
              required
            >
              {SubstrateTypeOptions.map((option) => (
                <MenuItem key={option.value} value={option.value}>
                  {option.label}
                </MenuItem>
              ))}
            </Select>
            {errors.type && <FormHelperText>{errors.type}</FormHelperText>}
          </FormControl>
        </Grid>
        
        <Grid item xs={12}>
          <TextField
            fullWidth
            label="説明"
            multiline
            rows={3}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </Grid>
        
        <Grid item xs={12}>
          <Typography variant="subtitle1">属性</Typography>
          {attributes.map((attr, index) => (
            <Grid container spacing={1} key={index} sx={{ mb: 1 }}>
              <Grid item xs={4}>
                <TextField
                  fullWidth
                  label="属性名"
                  value={attr.name}
                  onChange={(e) => {
                    updateAttribute(index, 'name', e.target.value);
                    // 属性名が入力されたら、そのインデックスのエラーをクリア
                    if (e.target.value.trim() && errors.attributes[index]) {
                      const newAttributeErrors = [...errors.attributes];
                      newAttributeErrors[index] = '';
                      setErrors({...errors, attributes: newAttributeErrors});
                    }
                  }}
                  error={!!errors.attributes[index]}
                />
              </Grid>
              <Grid item xs={4}>
                <TextField
                  fullWidth
                  label="値"
                  type="number"
                  value={attr.value}
                  onChange={(e) => {
                    updateAttribute(index, 'value', e.target.value);
                    // 値が入力されたら、そのインデックスのエラーをクリア
                    if (e.target.value && errors.attributes[index]) {
                      const newAttributeErrors = [...errors.attributes];
                      newAttributeErrors[index] = '';
                      setErrors({...errors, attributes: newAttributeErrors});
                    }
                  }}
                  error={!!errors.attributes[index]}
                  helperText={errors.attributes[index]}
                />
              </Grid>
              <Grid item xs={3}>
                <TextField
                  fullWidth
                  label="単位"
                  value={attr.unit}
                  onChange={(e) => updateAttribute(index, 'unit', e.target.value)}
                />
              </Grid>
              <Grid item xs={1}>
                <IconButton onClick={() => removeAttribute(index)}>
                  <DeleteIcon />
                </IconButton>
              </Grid>
            </Grid>
          ))}
          
          <Button 
            startIcon={<AddIcon />} 
            onClick={addAttribute}
            variant="outlined"
          >
            属性を追加
          </Button>
        </Grid>
        
        <Grid item xs={6}>
          <Button 
            type="submit" 
            variant="contained" 
            color="primary"
            fullWidth
          >
            {isEditing ? '更新' : '登録'}
          </Button>
        </Grid>
        
        <Grid item xs={6}>
          <Button 
            variant="outlined" 
            color="secondary"
            fullWidth
            onClick={handleCancel}
          >
            キャンセル
          </Button>
        </Grid>
      </Grid>
      <Snackbar open={openSnackbar} autoHideDuration={6000} onClose={handleSnackbarClose}>
        <Alert onClose={handleSnackbarClose} severity={snackbarSeverity} sx={{ width: '100%' }}>
          {snackbarMessage}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default SubstrateTypeForm;
