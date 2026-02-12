export const WASTE_TYPES = [
  '汚泥（一般）', '焼却灰', '汚泥（有機）', '鉱さい', 'ばいじん', 'その他',
] as const;

export type WasteType = (typeof WASTE_TYPES)[number];

/** 土壌汚染対策法 溶出基準 (regulatory thresholds) */
export interface ElutionThreshold {
  limit: number;
  unit: string;
  name: string;
}

export const ELUTION_THRESHOLDS: Record<string, ElutionThreshold> = {
  Pb: { limit: 0.01, unit: 'mg/L', name: '鉛' },
  As: { limit: 0.01, unit: 'mg/L', name: 'ヒ素' },
  Cd: { limit: 0.003, unit: 'mg/L', name: 'カドミウム' },
  Cr6: { limit: 0.05, unit: 'mg/L', name: '六価クロム' },
  Hg: { limit: 0.0005, unit: 'mg/L', name: '水銀' },
  Se: { limit: 0.01, unit: 'mg/L', name: 'セレン' },
  F: { limit: 0.8, unit: 'mg/L', name: 'フッ素' },
  B: { limit: 1.0, unit: 'mg/L', name: 'ホウ素' },
};
