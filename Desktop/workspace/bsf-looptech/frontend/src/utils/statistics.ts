/**
 * Pure statistical functions for correlation analysis
 */

/** Pearson correlation coefficient */
export const calculateCorrelation = (x: number[], y: number[]): number => {
  const n = x.length;
  if (n < 3 || n !== y.length) return 0;

  const sumX = x.reduce((a, b) => a + b, 0);
  const sumY = y.reduce((a, b) => a + b, 0);
  const sumXY = x.reduce((total, xi, i) => total + xi * y[i], 0);
  const sumX2 = x.reduce((total, xi) => total + xi * xi, 0);
  const sumY2 = y.reduce((total, yi) => total + yi * yi, 0);

  const numerator = n * sumXY - sumX * sumY;
  const denominator = Math.sqrt((n * sumX2 - sumX * sumX) * (n * sumY2 - sumY * sumY));

  return denominator === 0 ? 0 : numerator / denominator;
};

/** Coefficient of determination (R-squared) */
export const calculateR2 = (correlation: number): number => correlation * correlation;
