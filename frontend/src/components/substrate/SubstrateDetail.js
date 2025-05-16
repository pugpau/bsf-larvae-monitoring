import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  getSubstrateBatch, 
  updateBatchStatus, 
  getBatchHistory,
  getAllSubstrateTypes
} from '../../api/substrate';

const SubstrateDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [batch, setBatch] = useState(null);
  const [history, setHistory] = useState([]);
  const [substrateTypes, setSubstrateTypes] = useState([]);
  const [error, setError] = useState(null);
  const [statusUpdate, setStatusUpdate] = useState({
    status: '',
    change_reason: '',
  });
  const [showStatusForm, setShowStatusForm] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        
        // Fetch batch details
        const batchResponse = await getSubstrateBatch(id);
        setBatch(batchResponse);
        
        // Fetch batch history
        const historyResponse = await getBatchHistory(id);
        setHistory(historyResponse);
        
        // Fetch substrate types for reference
        const typesResponse = await getAllSubstrateTypes();
        setSubstrateTypes(typesResponse);
        
        setLoading(false);
      } catch (err) {
        console.error('Error fetching substrate batch data:', err);
        setError('基質バッチデータの取得中にエラーが発生しました。');
        setLoading(false);
      }
    };

    fetchData();
  }, [id]);

  const handleStatusChange = (e) => {
    setStatusUpdate({
      ...statusUpdate,
      [e.target.name]: e.target.value,
    });
  };

  const submitStatusUpdate = async (e) => {
    e.preventDefault();
    
    if (!statusUpdate.status) {
      setError('ステータスを選択してください。');
      return;
    }
    
    try {
      await updateBatchStatus(id, statusUpdate);
      
      // Refresh batch data
      const batchResponse = await getSubstrateBatch(id);
      setBatch(batchResponse);
      
      // Refresh history
      const historyResponse = await getBatchHistory(id);
      setHistory(historyResponse);
      
      // Reset form
      setStatusUpdate({
        status: '',
        change_reason: '',
      });
      setShowStatusForm(false);
    } catch (err) {
      console.error('Error updating batch status:', err);
      setError('ステータス更新中にエラーが発生しました。');
    }
  };

  if (loading) {
    return <div>基質バッチデータを読み込み中...</div>;
  }

  if (error) {
    return <div className="error-message">{error}</div>;
  }

  if (!batch) {
    return <div>基質バッチが見つかりません。</div>;
  }

  // Find substrate type names for components
  const getSubstrateTypeName = (typeId) => {
    const type = substrateTypes.find(t => t.id === typeId);
    return type ? type.name : typeId;
  };

  return (
    <div className="substrate-detail">
      <h1>{batch.name || `基質バッチ ${batch.id}`}</h1>
      
      <div className="substrate-info">
        <div className="info-section">
          <h2>基本情報</h2>
          <p><strong>ID:</strong> {batch.id}</p>
          <p><strong>ステータス:</strong> {batch.status}</p>
          {batch.description && (
            <p><strong>説明:</strong> {batch.description}</p>
          )}
          {batch.location && (
            <p><strong>場所:</strong> {batch.location}</p>
          )}
          {batch.total_weight && (
            <p>
              <strong>総重量:</strong> {batch.total_weight} {batch.weight_unit || 'kg'}
            </p>
          )}
          {batch.batch_number && (
            <p><strong>バッチ番号:</strong> {batch.batch_number}</p>
          )}
          <p><strong>作成日:</strong> {new Date(batch.created_at).toLocaleString()}</p>
        </div>
        
        <div className="info-section">
          <h2>構成成分</h2>
          {batch.components && batch.components.length > 0 ? (
            <ul>
              {batch.components.map((component, index) => (
                <li key={index}>
                  {getSubstrateTypeName(component.substrate_type_id)} - {component.ratio * 100}%
                </li>
              ))}
            </ul>
          ) : (
            <p>構成成分情報がありません</p>
          )}
        </div>
        
        {batch.attributes && batch.attributes.length > 0 && (
          <div className="info-section">
            <h2>属性</h2>
            <ul>
              {batch.attributes.map((attr, index) => (
                <li key={index}>
                  {attr.name}: {attr.value} {attr.unit || ''}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
      
      <div className="action-section">
        <h2>アクション</h2>
        <button 
          className="primary-button"
          onClick={() => setShowStatusForm(!showStatusForm)}
        >
          ステータス更新
        </button>
        <button 
          className="secondary-button"
          onClick={() => navigate('/substrate')}
        >
          一覧に戻る
        </button>
      </div>
      
      {showStatusForm && (
        <div className="status-update-form">
          <h3>ステータス更新</h3>
          <form onSubmit={submitStatusUpdate}>
            <div className="form-group">
              <label htmlFor="status">新しいステータス:</label>
              <select
                id="status"
                name="status"
                value={statusUpdate.status}
                onChange={handleStatusChange}
                required
              >
                <option value="">選択してください</option>
                <option value="準備中">準備中</option>
                <option value="使用中">使用中</option>
                <option value="完了">完了</option>
                <option value="廃棄">廃棄</option>
              </select>
            </div>
            
            <div className="form-group">
              <label htmlFor="change_reason">変更理由:</label>
              <textarea
                id="change_reason"
                name="change_reason"
                value={statusUpdate.change_reason}
                onChange={handleStatusChange}
                rows="3"
              />
            </div>
            
            <div className="form-actions">
              <button type="submit" className="primary-button">更新</button>
              <button 
                type="button" 
                className="secondary-button"
                onClick={() => setShowStatusForm(false)}
              >
                キャンセル
              </button>
            </div>
          </form>
        </div>
      )}
      
      <div className="history-section">
        <h2>変更履歴</h2>
        {history.length === 0 ? (
          <p>変更履歴がありません</p>
        ) : (
          <table className="history-table">
            <thead>
              <tr>
                <th>日時</th>
                <th>変更内容</th>
                <th>変更理由</th>
                <th>変更者</th>
              </tr>
            </thead>
            <tbody>
              {history.map((entry, index) => (
                <tr key={index}>
                  <td>{new Date(entry.timestamp).toLocaleString()}</td>
                  <td>{entry.change_description}</td>
                  <td>{entry.change_reason || '-'}</td>
                  <td>{entry.changed_by || '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};

export default SubstrateDetail;
