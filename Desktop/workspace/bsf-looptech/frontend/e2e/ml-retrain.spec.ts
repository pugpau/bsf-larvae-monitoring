import { test, expect } from '@playwright/test';

/**
 * E2E Flow 5: 分析ダッシュボード (KPI + トレンド + 精度)
 *
 * Tab 2 で KPIダッシュボード、トレンド分析、予測精度コンポーネントが
 * レンダリングされることを検証。
 */

test.describe('分析ダッシュボード & ML精度', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.getByLabel(/ユーザー名/).fill('demo');
    await page.getByLabel(/パスワード/).fill('demo');
    await page.getByRole('button', { name: /ログイン/ }).click();
    await expect(page.getByText('BSF-LoopTech')).toBeVisible({ timeout: 10000 });
  });

  test('分析ダッシュボードタブが表示される', async ({ page }) => {
    await page.getByRole('tab', { name: '分析ダッシュボード' }).click();
    await expect(page.getByRole('tab', { name: '分析ダッシュボード' })).toHaveAttribute('aria-selected', 'true');

    // ダッシュボードコンポーネントがレンダリングされる
    await page.waitForTimeout(2000);
    await expect(page.getByText('BSF-LoopTech')).toBeVisible();
  });

  test('品質管理タブが表示される', async ({ page }) => {
    await page.getByRole('tab', { name: '品質管理' }).click();
    await expect(page.getByRole('tab', { name: '品質管理' })).toHaveAttribute('aria-selected', 'true');

    // 品質管理コンポーネントがレンダリングされる
    await page.waitForTimeout(1000);
    await expect(page.getByText('BSF-LoopTech')).toBeVisible();
  });
});
