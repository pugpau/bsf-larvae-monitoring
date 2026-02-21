/**
 * Recharts アニメーション制御ユーティリティ
 * prefers-reduced-motion に応じてチャートアニメーションを切り替え
 */

interface AnimationProps {
  isAnimationActive: boolean;
  animationDuration?: number;
}

/**
 * Recharts コンポーネント (Line, Bar, Scatter 等) にスプレッドするアニメーション props
 * @param prefersReduced useReducedMotion() の返値
 * @returns `{...animProps}` でスプレッド
 */
export function getAnimationProps(prefersReduced: boolean): AnimationProps {
  if (prefersReduced) {
    return { isAnimationActive: false };
  }
  return { isAnimationActive: true, animationDuration: 300 };
}
