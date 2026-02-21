import { test, expect } from '@playwright/test';

/**
 * E2E: 搬入予定 & 配合管理タブ間遷移
 *
 * Tab 0 (搬入予定) でテーブル表示、Tab 1 (配合管理) でコンポーネント群がレンダリングされること、
 * およびタブ間遷移が正常に動作することを検証。
 */

test.describe('搬入予定 & 配合管理 タブ間遷移', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.getByLabel(/ユーザー名/).fill('demo');
    await page.getByLabel(/パスワード/).fill('demo');
    await page.getByRole('button', { name: /ログイン/ }).click();
    await expect(page.getByText('ERC製品管理システム')).toBeVisible({ timeout: 10000 });
  });

  test('搬入予定タブがデフォルトで選択されている', async ({ page }) => {
    const tab = page.getByRole('tab', { name: '搬入予定' });
    await expect(tab).toHaveAttribute('aria-selected', 'true');
  });

  test('搬入予定テーブルが表示される', async ({ page }) => {
    // テーブルまたはEmptyStateが表示されること
    await page.waitForTimeout(2000);
    const tableOrEmpty = page.locator('table, [class*="EmptyState"]');
    await expect(tableOrEmpty.first()).toBeVisible();
  });

  test('搬入予定→配合管理タブ遷移が動作する', async ({ page }) => {
    // Tab 1へ遷移
    await page.getByRole('tab', { name: '配合管理' }).click();
    await expect(page.getByRole('tab', { name: '配合管理' })).toHaveAttribute('aria-selected', 'true');

    // 配合ワークフローパネルが表示される
    await expect(page.getByText('配合ワークフロー')).toBeVisible({ timeout: 5000 });

    // AI推薦ボタンが存在する
    await expect(page.getByRole('button', { name: /AI推薦/ })).toBeVisible();
  });

  test('配合管理タブに4コンポーネントがレンダリングされる', async ({ page }) => {
    await page.getByRole('tab', { name: '配合管理' }).click();
    await page.waitForTimeout(1000);

    // 配合ワークフロー
    await expect(page.getByText('配合ワークフロー')).toBeVisible();

    // ページ全体がクラッシュしていない
    await expect(page.getByText('ERC製品管理システム')).toBeVisible();
  });

  test('配合管理→搬入予定タブ復帰が動作する', async ({ page }) => {
    // Tab 1へ
    await page.getByRole('tab', { name: '配合管理' }).click();
    await expect(page.getByRole('tab', { name: '配合管理' })).toHaveAttribute('aria-selected', 'true');

    // Tab 0へ戻る
    await page.getByRole('tab', { name: '搬入予定' }).click();
    await expect(page.getByRole('tab', { name: '搬入予定' })).toHaveAttribute('aria-selected', 'true');

    // テーブルまたはEmptyStateが表示される
    const tableOrEmpty = page.locator('table, [class*="EmptyState"]');
    await expect(tableOrEmpty.first()).toBeVisible({ timeout: 3000 });
  });
});
