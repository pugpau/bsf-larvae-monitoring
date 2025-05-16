import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getSubstrateBatches } from '../../api/substrate';

const SubstrateList = () => {
  const [loading, setLoading] = useState(true);
  const [batches, setBatches] = useState([]);
  const [error, setError] = useState(null);
  const [activeOnly, setActiveOnly] = useState(false);
  
  // Default farm ID - in a real app, this would come from user selection or auth
  const farmId = 'farm-001';

  useEffect(() => {
    const fetchBatches = async () => {
      try {
        setLoading(true);
        const response = await getSubstrateBatches(farmId, activeOnly);
        setBatches(response);
        setLoading(false);
      } catch (err) {
        console.error('Error fetching substrate batches:', err);
        setError('基質バッチの取得中にエラーが発生しました。');
        setLoading(false);
      }
    };

    fetchBatches();
  }, [farmId, activeOnly]);

  if (loading) {
    return <div>基質バッチを読み込み中...</div>;
  }

  if (error) {
    return <div className="error-message">{error}</div>;
  }

  return (
    <div>
      <h1>基質バッチ一覧</h1>
      
      <div className="filter-controls">
        <label>
          <input
            type="checkbox"
            checked={activeOnly}
            onChange={() => setActiveOnly(!activeOnly)}
          />
          アクティブなバッチのみ表示
        </label>
      </div>
      
      {batches.length === 0 ? (
        <p>基質バッチが見つかりません</p>
      ) : (
        <div className="substrate-list">
          {batches.map(batch => (
            <div key={batch.id} className="substrate-card">
              <h2>{batch.name || batch.id}</h2>
              <p>ステータス: {batch.status}</p>
              {batch.location && <p>場所: {batch.location}</p>}
              {batch.total_weight && (
                <p>
                  総重量: {batch.total_weight} {batch.weight_unit || 'kg'}
                </p>
              )}
              
              <Link to={`/substrate/${batch.id}`} className="button">
                詳細を表示
              </Link>
            </div>
          ))}
        </div>
      )}
      
      <div className="action-buttons">
        <button className="primary-button">新規バッチ作成</button>
      </div>
    </div>
  );
};

export default SubstrateList;
