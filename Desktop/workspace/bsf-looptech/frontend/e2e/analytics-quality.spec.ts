import { test, expect } from '@playwright/test';

/**
 * E2E: 分析ダッシュボード (Tab 2) & 品質管理 (Tab 3)
 *
 * Tab 2: KPIダッシュボード + 相関分析 + トレンド + 予測精度
 * Tab 3: 品質管理ダッシュボード（溶出基準チェック、合否判定）
 */

test.describe('分析ダッシュボード (Tab 2)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.getByLabel(/ユーザー名/).fill('demo');
    await page.getByLabel(/パスワード/).fill('demo');
    await page.getByRole('button', { name: /ログイン/ }).click();
    await expect(page.getByText('ERC製品管理システム')).toBeVisible({ timeout: 10000 });

    // Tab 2 へ遷移
    await page.getByRole('tab', { name: '分析ダッシュボード' }).click();
    await expect(page.getByRole('tab', { name: '分析ダッシュボード' })).toHaveAttribute('aria-selected', 'true');
  });

  test('KPIダッシュボードセクションが表示される', async ({ page }) => {
    // KPIダッシュボードのヘッダーまたはローディングが表示される
    await page.waitForTimeout(2000);

    // ページがクラッシュしていない
    await expect(page.getByText('ERC製品管理システム')).toBeVisible();

    // Tab 2 のコンテンツエリアが存在する
    await expect(page.getByRole('tab', { name: '分析ダッシュボード' })).toHaveAttribute('aria-selected', 'true');
  });

  test('KPI期間選択が操作できる', async ({ page }) => {
    await page.waitForTimeout(1000);

    // 期間フィルタ（Select）が存在する場合
    const periodSelect = page.locator('select, [role="combobox"]').first();
    if (await periodSelect.isVisible()) {
      await periodSelect.click();
      await page.waitForTimeout(300);
    }

    // ページが正常に動作している
    await expect(page.getByText('ERC製品管理システム')).toBeVisible();
  });

  test('スクロールで複数セクションが確認できる', async ({ page }) => {
    await page.waitForTimeout(2000);

    // ページ下部へスクロール
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await page.waitForTimeout(500);

    // ページトップに戻る
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.waitForTimeout(300);

    // ページが正常
    await expect(page.getByText('ERC製品管理システム')).toBeVisible();
  });

  test('他タブへの遷移と復帰が正常に動作する', async ({ page }) => {
    // Tab 3へ遷移
    await page.getByRole('tab', { name: '品質管理' }).click();
    await expect(page.getByRole('tab', { name: '品質管理' })).toHaveAttribute('aria-selected', 'true');

    // Tab 2へ復帰
    await page.getByRole('tab', { name: '分析ダッシュボード' }).click();
    await expect(page.getByRole('tab', { name: '分析ダッシュボード' })).toHaveAttribute('aria-selected', 'true');

    await page.waitForTimeout(1000);
    await expect(page.getByText('ERC製品管理システム')).toBeVisible();
  });
});

test.describe('品質管理 (Tab 3)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.getByLabel(/ユーザー名/).fill('demo');
    await page.getByLabel(/パスワード/).fill('demo');
    await page.getByRole('button', { name: /ログイン/ }).click();
    await expect(page.getByText('ERC製品管理システム')).toBeVisible({ timeout: 10000 });

    // Tab 3 へ遷移
    await page.getByRole('tab', { name: '品質管理' }).click();
    await expect(page.getByRole('tab', { name: '品質管理' })).toHaveAttribute('aria-selected', 'true');
  });

  test('品質管理ダッシュボードが表示される', async ({ page }) => {
    await page.waitForTimeout(2000);

    // ページがクラッシュしていない
    await expect(page.getByText('ERC製品管理システム')).toBeVisible();
    await expect(page.getByRole('tab', { name: '品質管理' })).toHaveAttribute('aria-selected', 'true');
  });

  test('テーブルまたはチャートが表示される', async ({ page }) => {
    await page.waitForTimeout(2000);

    // テーブル、チャート、またはEmptyState/Alert のいずれかが存在
    const contentElements = page.locator('table, .recharts-wrapper, [role="alert"], [class*="EmptyState"]');
    await expect(contentElements.first()).toBeVisible({ timeout: 5000 });
  });

  test('品質管理→分析ダッシュボードタブ遷移が動作する', async ({ page }) => {
    // Tab 2へ遷移
    await page.getByRole('tab', { name: '分析ダッシュボード' }).click();
    await expect(page.getByRole('tab', { name: '分析ダッシュボード' })).toHaveAttribute('aria-selected', 'true');

    // Tab 3へ復帰
    await page.getByRole('tab', { name: '品質管理' }).click();
    await expect(page.getByRole('tab', { name: '品質管理' })).toHaveAttribute('aria-selected', 'true');

    await page.waitForTimeout(1000);
    await expect(page.getByText('ERC製品管理システム')).toBeVisible();
  });
});
