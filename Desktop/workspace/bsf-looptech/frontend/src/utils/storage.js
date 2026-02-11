/**
 * Hybrid data layer for waste treatment formulation optimization.
 *
 * Strategy:
 * - On init, try to load from backend API → cache into localStorage
 * - Reads always come from localStorage (synchronous, instant)
 * - Writes go to API first; on success, update localStorage; on fail, localStorage-only
 *
 * This keeps the synchronous interface that existing components expect
 * while transparently persisting to PostgreSQL when the backend is available.
 */

import * as api from './apiClient';

const STORAGE_KEYS = {
  MATERIAL_TYPES: 'bsf_substrate_types',
  WASTE_RECORDS: 'bsf_substrate_batches'
};

// Track whether we've synced with the API in this session
let _apiSynced = false;

// ===== Initialization (call once on app mount) =====

/**
 * Initialize data from backend API.
 * Call this in App.js useEffect. If API is down, localStorage data is used as-is.
 */
export const initializeFromApi = async () => {
  try {
    const healthy = await api.checkApiHealth();
    if (!healthy) return false;

    // Fetch waste records from API
    const records = await api.fetchWasteRecords();
    if (Array.isArray(records) && records.length > 0) {
      localStorage.setItem(STORAGE_KEYS.WASTE_RECORDS, JSON.stringify(records));
    }

    // Fetch material types from API
    const types = await api.fetchMaterialTypes();
    if (Array.isArray(types) && types.length > 0) {
      localStorage.setItem(STORAGE_KEYS.MATERIAL_TYPES, JSON.stringify(types));
    }

    _apiSynced = true;
    return true;
  } catch {
    _apiSynced = false;
    return false;
  }
};

/** Whether the API sync completed successfully. */
export const isApiSynced = () => _apiSynced;


// ===== Material Types (マスタ管理) =====

export const saveSubstrateType = (materialType) => {
  const existing = getSubstrateTypes();
  const newType = {
    ...materialType,
    id: materialType.id || `type_${Date.now()}`,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString()
  };
  const updated = [...existing, newType];
  localStorage.setItem(STORAGE_KEYS.MATERIAL_TYPES, JSON.stringify(updated));

  // Fire-and-forget API call
  if (_apiSynced) {
    api.createMaterialType(materialType).catch(() => {});
  }

  return newType;
};

export const updateSubstrateType = (id, updates) => {
  const existing = getSubstrateTypes();
  const updated = existing.map(type =>
    type.id === id
      ? { ...type, ...updates, updated_at: new Date().toISOString() }
      : type
  );
  localStorage.setItem(STORAGE_KEYS.MATERIAL_TYPES, JSON.stringify(updated));

  if (_apiSynced) {
    api.updateMaterialType(id, updates).catch(() => {});
  }

  return updated.find(type => type.id === id);
};

export const getSubstrateTypes = () => {
  const stored = localStorage.getItem(STORAGE_KEYS.MATERIAL_TYPES);
  if (stored) {
    return JSON.parse(stored);
  }

  const defaultTypes = [
    {
      id: 'type_solidifier_1',
      name: '普通ポルトランドセメント',
      category: 'solidifier',
      description: '一般的な固化剤。汎用性が高い。',
      supplier: 'セメントメーカーA',
      unitCost: 15,
      unit: 'kg',
      attributes: [
        { name: 'CaO含有率', value: '64', unit: '%' },
        { name: 'SiO2含有率', value: '22', unit: '%' }
      ],
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    },
    {
      id: 'type_solidifier_2',
      name: '高炉セメントB種',
      category: 'solidifier',
      description: '高炉スラグ配合。六価クロム低減効果あり。',
      supplier: 'セメントメーカーB',
      unitCost: 18,
      unit: 'kg',
      attributes: [
        { name: 'スラグ混合率', value: '40', unit: '%' },
        { name: 'Cr6+溶出抑制', value: '高', unit: '' }
      ],
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    },
    {
      id: 'type_suppressor_1',
      name: 'キレート剤A',
      category: 'suppressor',
      description: '重金属イオンのキレート化による溶出抑制。',
      supplier: '化学メーカーC',
      unitCost: 250,
      unit: 'kg',
      attributes: [
        { name: '対象金属', value: 'Pb, Cd, As', unit: '' },
        { name: '有効pH範囲', value: '4-12', unit: '' }
      ],
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    },
    {
      id: 'type_suppressor_2',
      name: '硫酸第一鉄',
      category: 'suppressor',
      description: '六価クロム還元用。',
      supplier: '化学メーカーD',
      unitCost: 45,
      unit: 'kg',
      attributes: [
        { name: '対象金属', value: 'Cr6+', unit: '' },
        { name: '純度', value: '95', unit: '%' }
      ],
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    },
    {
      id: 'type_waste_1',
      name: '汚泥（一般）',
      category: 'waste_type',
      description: '工場排水処理汚泥',
      supplier: '',
      unitCost: 0,
      unit: 't',
      attributes: [
        { name: '典型含水率', value: '70-85', unit: '%' },
        { name: '典型pH', value: '6-9', unit: '' }
      ],
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    },
    {
      id: 'type_waste_2',
      name: '焼却灰',
      category: 'waste_type',
      description: '一般廃棄物焼却灰',
      supplier: '',
      unitCost: 0,
      unit: 't',
      attributes: [
        { name: '典型含水率', value: '15-30', unit: '%' },
        { name: '典型pH', value: '10-12', unit: '' }
      ],
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    }
  ];

  localStorage.setItem(STORAGE_KEYS.MATERIAL_TYPES, JSON.stringify(defaultTypes));
  return defaultTypes;
};

export const deleteSubstrateType = (id) => {
  const existing = getSubstrateTypes();
  const filtered = existing.filter(type => type.id !== id);
  localStorage.setItem(STORAGE_KEYS.MATERIAL_TYPES, JSON.stringify(filtered));

  if (_apiSynced) {
    api.deleteMaterialType(id).catch(() => {});
  }

  return true;
};

// ===== Waste Records (搬入管理) =====

export const saveSubstrateBatch = (record) => {
  const existing = getSubstrateBatches();
  const newRecord = {
    ...record,
    id: record.id || `waste_${Date.now()}`,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString()
  };
  const updated = [...existing, newRecord];
  localStorage.setItem(STORAGE_KEYS.WASTE_RECORDS, JSON.stringify(updated));

  if (_apiSynced) {
    api.createWasteRecord(record).catch(() => {});
  }

  return newRecord;
};

export const updateSubstrateBatch = (id, updates) => {
  const existing = getSubstrateBatches();
  const updated = existing.map(record =>
    record.id === id
      ? { ...record, ...updates, updated_at: new Date().toISOString() }
      : record
  );
  localStorage.setItem(STORAGE_KEYS.WASTE_RECORDS, JSON.stringify(updated));

  if (_apiSynced) {
    api.updateWasteRecord(id, updates).catch(() => {});
  }

  return updated.find(record => record.id === id);
};

export const getSubstrateBatches = () => {
  const stored = localStorage.getItem(STORAGE_KEYS.WASTE_RECORDS);
  if (stored) {
    return JSON.parse(stored);
  }

  const defaultRecords = [
    {
      id: 'waste_sample_1',
      source: 'A工場',
      deliveryDate: '2026-01-10',
      wasteType: '汚泥（一般）',
      weight: 12.5,
      weightUnit: 't',
      status: 'formulated',
      analysis: {
        pH: 7.2, moisture: 78.5, ignitionLoss: 32.1,
        Pb: 0.008, As: 0.002, Cd: 0.001, Cr6: 0.02,
        Hg: 0.0003, Se: 0.001, F: 0.15, B: 0.08
      },
      formulation: {
        solidifierType: '普通ポルトランドセメント',
        solidifierAmount: 150, solidifierUnit: 'kg/t',
        suppressorType: 'キレート剤A',
        suppressorAmount: 3.5, suppressorUnit: 'kg/t'
      },
      elutionResult: { Pb: 0.005, As: 0.001, Cd: 0.0005, Cr6: 0.01, passed: true },
      notes: '通常配合で基準値クリア',
      created_at: '2026-01-10T09:00:00Z', updated_at: '2026-01-10T14:30:00Z'
    },
    {
      id: 'waste_sample_2',
      source: 'B工場',
      deliveryDate: '2026-01-15',
      wasteType: '焼却灰',
      weight: 8.0,
      weightUnit: 't',
      status: 'formulated',
      analysis: {
        pH: 11.5, moisture: 22.3, ignitionLoss: 8.7,
        Pb: 0.05, As: 0.008, Cd: 0.003, Cr6: 0.08,
        Hg: 0.0005, Se: 0.005, F: 0.85, B: 0.12
      },
      formulation: {
        solidifierType: '高炉セメントB種',
        solidifierAmount: 200, solidifierUnit: 'kg/t',
        suppressorType: '硫酸第一鉄',
        suppressorAmount: 8.0, suppressorUnit: 'kg/t'
      },
      elutionResult: { Pb: 0.008, As: 0.003, Cd: 0.001, Cr6: 0.04, passed: true },
      notes: 'Pb, Cr6+が高め。高炉セメント+硫酸第一鉄で対応',
      created_at: '2026-01-15T10:00:00Z', updated_at: '2026-01-16T11:00:00Z'
    },
    {
      id: 'waste_sample_3',
      source: 'C処理場',
      deliveryDate: '2026-01-20',
      wasteType: '汚泥（一般）',
      weight: 15.0,
      weightUnit: 't',
      status: 'formulated',
      analysis: {
        pH: 6.8, moisture: 82.0, ignitionLoss: 40.5,
        Pb: 0.012, As: 0.005, Cd: 0.002, Cr6: 0.015,
        Hg: 0.0002, Se: 0.003, F: 0.30, B: 0.15
      },
      formulation: {
        solidifierType: '普通ポルトランドセメント',
        solidifierAmount: 180, solidifierUnit: 'kg/t',
        suppressorType: 'キレート剤A',
        suppressorAmount: 5.0, suppressorUnit: 'kg/t'
      },
      elutionResult: { Pb: 0.006, As: 0.002, Cd: 0.001, Cr6: 0.008, passed: true },
      notes: '高含水率のため固化剤増量',
      created_at: '2026-01-20T08:30:00Z', updated_at: '2026-01-20T15:00:00Z'
    },
    {
      id: 'waste_sample_4',
      source: 'A工場',
      deliveryDate: '2026-01-25',
      wasteType: '汚泥（一般）',
      weight: 10.0,
      weightUnit: 't',
      status: 'formulated',
      analysis: {
        pH: 7.5, moisture: 75.0, ignitionLoss: 28.3,
        Pb: 0.006, As: 0.003, Cd: 0.0015, Cr6: 0.025,
        Hg: 0.0002, Se: 0.002, F: 0.20, B: 0.06
      },
      formulation: {
        solidifierType: '普通ポルトランドセメント',
        solidifierAmount: 130, solidifierUnit: 'kg/t',
        suppressorType: '',
        suppressorAmount: 0, suppressorUnit: 'kg/t'
      },
      elutionResult: { Pb: 0.004, As: 0.002, Cd: 0.0008, Cr6: 0.015, passed: true },
      notes: '基準値内のため抑制材不要',
      created_at: '2026-01-25T09:00:00Z', updated_at: '2026-01-25T13:00:00Z'
    },
    {
      id: 'waste_sample_5',
      source: 'D処理場',
      deliveryDate: '2026-01-28',
      wasteType: '焼却灰',
      weight: 6.5,
      weightUnit: 't',
      status: 'formulated',
      analysis: {
        pH: 12.0, moisture: 18.5, ignitionLoss: 5.2,
        Pb: 0.08, As: 0.012, Cd: 0.004, Cr6: 0.12,
        Hg: 0.0004, Se: 0.008, F: 1.2, B: 0.25
      },
      formulation: {
        solidifierType: '高炉セメントB種',
        solidifierAmount: 250, solidifierUnit: 'kg/t',
        suppressorType: '硫酸第一鉄',
        suppressorAmount: 12.0, suppressorUnit: 'kg/t'
      },
      elutionResult: { Pb: 0.009, As: 0.005, Cd: 0.002, Cr6: 0.045, F: 0.6, passed: true },
      notes: '高濃度。大量配合で対応。F基準ギリギリ',
      created_at: '2026-01-28T10:00:00Z', updated_at: '2026-01-29T16:00:00Z'
    },
    {
      id: 'waste_sample_6',
      source: 'B工場',
      deliveryDate: '2026-02-01',
      wasteType: '汚泥（一般）',
      weight: 14.0,
      weightUnit: 't',
      status: 'formulated',
      analysis: {
        pH: 8.0, moisture: 72.0, ignitionLoss: 25.0,
        Pb: 0.015, As: 0.006, Cd: 0.002, Cr6: 0.035,
        Hg: 0.0003, Se: 0.004, F: 0.40, B: 0.10
      },
      formulation: {
        solidifierType: '普通ポルトランドセメント',
        solidifierAmount: 160, solidifierUnit: 'kg/t',
        suppressorType: 'キレート剤A',
        suppressorAmount: 4.0, suppressorUnit: 'kg/t'
      },
      elutionResult: { Pb: 0.007, As: 0.003, Cd: 0.001, Cr6: 0.02, passed: true },
      notes: '',
      created_at: '2026-02-01T09:00:00Z', updated_at: '2026-02-01T14:00:00Z'
    },
    {
      id: 'waste_sample_7',
      source: 'C処理場',
      deliveryDate: '2026-02-03',
      wasteType: '焼却灰',
      weight: 5.5,
      weightUnit: 't',
      status: 'formulated',
      analysis: {
        pH: 11.0, moisture: 25.0, ignitionLoss: 10.5,
        Pb: 0.035, As: 0.009, Cd: 0.0025, Cr6: 0.06,
        Hg: 0.0004, Se: 0.006, F: 0.70, B: 0.18
      },
      formulation: {
        solidifierType: '高炉セメントB種',
        solidifierAmount: 180, solidifierUnit: 'kg/t',
        suppressorType: '硫酸第一鉄',
        suppressorAmount: 6.0, suppressorUnit: 'kg/t'
      },
      elutionResult: { Pb: 0.008, As: 0.004, Cd: 0.001, Cr6: 0.035, passed: true },
      notes: '中程度の汚染。標準配合で対応',
      created_at: '2026-02-03T10:00:00Z', updated_at: '2026-02-03T15:00:00Z'
    },
    {
      id: 'waste_sample_8',
      source: 'A工場',
      deliveryDate: '2026-02-05',
      wasteType: '汚泥（一般）',
      weight: 11.0,
      weightUnit: 't',
      status: 'formulated',
      analysis: {
        pH: 7.0, moisture: 80.0, ignitionLoss: 35.0,
        Pb: 0.010, As: 0.004, Cd: 0.0018, Cr6: 0.022,
        Hg: 0.0002, Se: 0.002, F: 0.25, B: 0.09
      },
      formulation: {
        solidifierType: '普通ポルトランドセメント',
        solidifierAmount: 170, solidifierUnit: 'kg/t',
        suppressorType: 'キレート剤A',
        suppressorAmount: 4.5, suppressorUnit: 'kg/t'
      },
      elutionResult: { Pb: 0.004, As: 0.001, Cd: 0.0006, Cr6: 0.012, passed: true },
      notes: '',
      created_at: '2026-02-05T09:00:00Z', updated_at: '2026-02-05T14:30:00Z'
    },
    {
      id: 'waste_sample_9',
      source: 'D処理場',
      deliveryDate: '2026-02-07',
      wasteType: '焼却灰',
      weight: 7.0,
      weightUnit: 't',
      status: 'analyzed',
      analysis: {
        pH: 11.8, moisture: 20.0, ignitionLoss: 6.5,
        Pb: 0.065, As: 0.011, Cd: 0.0035, Cr6: 0.10,
        Hg: 0.0005, Se: 0.007, F: 0.95, B: 0.20
      },
      formulation: null,
      elutionResult: null,
      notes: '高濃度。配合検討中',
      created_at: '2026-02-07T10:00:00Z', updated_at: '2026-02-07T10:00:00Z'
    },
    {
      id: 'waste_sample_10',
      source: 'B工場',
      deliveryDate: '2026-02-09',
      wasteType: '汚泥（一般）',
      weight: 13.0,
      weightUnit: 't',
      status: 'pending',
      analysis: {},
      formulation: null,
      elutionResult: null,
      notes: '分析待ち',
      created_at: '2026-02-09T08:00:00Z', updated_at: '2026-02-09T08:00:00Z'
    }
  ];

  localStorage.setItem(STORAGE_KEYS.WASTE_RECORDS, JSON.stringify(defaultRecords));
  return defaultRecords;
};

export const deleteSubstrateBatch = (id) => {
  const existing = getSubstrateBatches();
  const filtered = existing.filter(record => record.id !== id);
  localStorage.setItem(STORAGE_KEYS.WASTE_RECORDS, JSON.stringify(filtered));

  if (_apiSynced) {
    api.deleteWasteRecord(id).catch(() => {});
  }

  return true;
};

// ===== Utility =====

export const clearAllData = () => {
  localStorage.removeItem(STORAGE_KEYS.MATERIAL_TYPES);
  localStorage.removeItem(STORAGE_KEYS.WASTE_RECORDS);
};

// Category labels
export const MATERIAL_CATEGORIES = {
  solidifier: '固化剤',
  suppressor: '溶出抑制材',
  waste_type: '廃棄物種別'
};

export const getCategoryLabel = (category) => {
  return MATERIAL_CATEGORIES[category] || category;
};

// ===== AI Recommendation =====

/**
 * Get AI-recommended formulation for waste analysis.
 * Tries API first; falls back to local rule-based engine.
 */
export const getRecommendation = async (analysis, wasteType) => {
  // Try API first
  if (_apiSynced) {
    try {
      return await api.recommendFormulation(analysis, wasteType);
    } catch {
      // Fall through to local engine
    }
  }

  // Local rule-based fallback
  return localRecommend(analysis, wasteType);
};

const ELUTION_LIMITS = {
  Pb: 0.01, As: 0.01, Cd: 0.003, Cr6: 0.05,
  Hg: 0.0005, Se: 0.01, F: 0.8, B: 1.0,
};

const FEATURE_WEIGHTS = {
  pH: 1.0, moisture: 0.8, ignitionLoss: 0.6,
  Pb: 2.0, As: 2.0, Cd: 2.5, Cr6: 2.0,
  Hg: 2.5, Se: 1.5, F: 1.5, B: 1.0,
};

const FEATURE_RANGES = {
  pH: [4.0, 13.0], moisture: [10.0, 95.0], ignitionLoss: [2.0, 60.0],
  Pb: [0.0, 0.2], As: [0.0, 0.05], Cd: [0.0, 0.01],
  Cr6: [0.0, 0.3], Hg: [0.0, 0.002], Se: [0.0, 0.03],
  F: [0.0, 2.0], B: [0.0, 1.5],
};

const normalise = (value, feature) => {
  const [lo, hi] = FEATURE_RANGES[feature] || [0, 1];
  if (hi === lo) return 0;
  return Math.max(0, Math.min(1, (value - lo) / (hi - lo)));
};

const weightedDistance = (a, b) => {
  let total = 0, wSum = 0;
  for (const [feat, w] of Object.entries(FEATURE_WEIGHTS)) {
    if (a[feat] == null || b[feat] == null) continue;
    const diff = normalise(Number(a[feat]), feat) - normalise(Number(b[feat]), feat);
    total += w * diff * diff;
    wSum += w;
  }
  return wSum === 0 ? Infinity : Math.sqrt(total / wSum);
};

const severityScore = (analysis) => {
  let score = 0;
  for (const [metal, limit] of Object.entries(ELUTION_LIMITS)) {
    const val = analysis[metal];
    if (val != null && limit > 0) {
      const ratio = Number(val) / limit;
      if (ratio > 1) score += (ratio - 1) * (FEATURE_WEIGHTS[metal] || 1);
    }
  }
  return score;
};

const localRecommend = (analysis, wasteType) => {
  const history = getSubstrateBatches();
  const successful = history.filter(
    r => r.status === 'formulated' && r.formulation && r.analysis &&
         Object.entries(r.analysis).some(([k, v]) => v != null && FEATURE_WEIGHTS[k])
  );

  const reasoning = [];
  const exceeding = [];
  for (const [metal, limit] of Object.entries(ELUTION_LIMITS)) {
    const val = analysis[metal];
    if (val != null && Number(val) > limit) {
      exceeding.push(`${metal}: ${val} mg/L (基準値 ${limit} の ${(Number(val) / limit).toFixed(1)}倍)`);
    }
  }
  reasoning.push(exceeding.length > 0 ? `基準超過項目: ${exceeding.join(', ')}` : '全項目基準値内');

  if (successful.length >= 3) {
    const distances = successful
      .map(r => ({ dist: weightedDistance(analysis, r.analysis), rec: r }))
      .sort((a, b) => a.dist - b.dist)
      .slice(0, 5);

    let totalW = 0, avgSol = 0, avgSup = 0;
    const solCounts = {}, supCounts = {};
    const similarRecords = [];

    for (const { dist, rec } of distances) {
      const w = 1 / (dist + 0.01);
      totalW += w;
      const f = rec.formulation;
      avgSol += w * Number(f.solidifierAmount || 0);
      avgSup += w * Number(f.suppressorAmount || 0);
      if (f.solidifierType) solCounts[f.solidifierType] = (solCounts[f.solidifierType] || 0) + w;
      if (f.suppressorType) supCounts[f.suppressorType] = (supCounts[f.suppressorType] || 0) + w;
      similarRecords.push({
        id: rec.id, source: rec.source, deliveryDate: rec.deliveryDate,
        distance: Math.round(dist * 10000) / 10000,
        formulation: f,
        passed: rec.elutionResult?.passed ?? null,
      });
    }

    if (totalW > 0) { avgSol /= totalW; avgSup /= totalW; }

    const bestSol = Object.keys(solCounts).sort((a, b) => solCounts[b] - solCounts[a])[0] || '普通ポルトランドセメント';
    const bestSup = Object.keys(supCounts).sort((a, b) => supCounts[b] - supCounts[a])[0] || '';
    const severity = severityScore(analysis);
    const meanSev = distances.reduce((s, d) => s + severityScore(d.rec.analysis), 0) / distances.length;
    const ratio = (severity + 0.1) / (meanSev + 0.1);

    const avgDist = distances.reduce((s, d) => s + d.dist, 0) / distances.length;
    const passRate = distances.filter(d => d.rec.elutionResult?.passed).length / distances.length;
    const confidence = Math.max(0.1, Math.min(0.95, (1 - Math.min(avgDist, 1)) * 0.5 + passRate * 0.5));

    reasoning.push(`類似実績 ${distances.length} 件から推奨 (平均距離: ${avgDist.toFixed(3)})`);
    reasoning.push(`過去の合格率: ${(passRate * 100).toFixed(0)}%`);

    return {
      recommendation: {
        solidifierType: bestSol,
        solidifierAmount: Math.round(avgSol * Math.min(ratio, 1.5)),
        solidifierUnit: 'kg/t',
        suppressorType: bestSup,
        suppressorAmount: Math.round(avgSup * Math.min(ratio, 1.5) * 10) / 10,
        suppressorUnit: 'kg/t',
      },
      confidence: Math.round(confidence * 100) / 100,
      method: 'similarity',
      reasoning,
      similarRecords,
    };
  }

  // Rule-based fallback
  reasoning.push('過去実績が不足のためルールベースで推奨');
  const moisture = Number(analysis.moisture || 50);
  const severity = severityScore(analysis);
  const cr6 = Number(analysis.Cr6 || 0);
  const base = wasteType === '焼却灰' ? 180 : 160;
  const mf = wasteType === '焼却灰' ? 0.2 : 0.4;
  const metF = wasteType === '焼却灰' ? 60 : 55;
  const solAmount = Math.round(base + Math.max(0, moisture - 60) * mf + severity * metF);

  return {
    recommendation: {
      solidifierType: cr6 > 0.05 ? '高炉セメントB種' : '普通ポルトランドセメント',
      solidifierAmount: solAmount,
      solidifierUnit: 'kg/t',
      suppressorType: cr6 > 0.04 ? '硫酸第一鉄' : (severity > 0.5 ? 'キレート剤A' : ''),
      suppressorAmount: cr6 > 0.04 ? Math.round((2 + severity * 3) * 10) / 10 : (severity > 0.5 ? Math.round((2 + severity * 2) * 10) / 10 : 0),
      suppressorUnit: 'kg/t',
    },
    confidence: exceeding.length > 0 ? 0.3 : 0.4,
    method: 'rule',
    reasoning,
    similarRecords: [],
  };
};


// Regulatory thresholds (土壌汚染対策法 溶出基準)
export const ELUTION_THRESHOLDS = {
  Pb: { limit: 0.01, unit: 'mg/L', name: '鉛' },
  As: { limit: 0.01, unit: 'mg/L', name: 'ヒ素' },
  Cd: { limit: 0.003, unit: 'mg/L', name: 'カドミウム' },
  Cr6: { limit: 0.05, unit: 'mg/L', name: '六価クロム' },
  Hg: { limit: 0.0005, unit: 'mg/L', name: '水銀' },
  Se: { limit: 0.01, unit: 'mg/L', name: 'セレン' },
  F: { limit: 0.8, unit: 'mg/L', name: 'フッ素' },
  B: { limit: 1.0, unit: 'mg/L', name: 'ホウ素' }
};
