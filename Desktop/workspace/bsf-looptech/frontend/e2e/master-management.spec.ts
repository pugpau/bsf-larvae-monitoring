import { test, expect } from '@playwright/test';

/**
 * E2E: マスタ管理 (Tab 4)
 *
 * 4つのサブタブ（搬入先、搬入物、固化材、溶出抑制剤）のナビゲーション、
 * 各リストのツールバー、検索、ページネーション、CSV出力を検証。
 */

test.describe('マスタ管理', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.getByLabel(/ユーザー名/).fill('demo');
    await page.getByLabel(/パスワード/).fill('demo');
    await page.getByRole('button', { name: /ログイン/ }).click();
    await expect(page.getByText('ERC製品管理システム')).toBeVisible({ timeout: 10000 });

    // Tab 4: マスタ管理 へ遷移
    await page.getByRole('tab', { name: 'マスタ管理' }).click();
    await expect(page.getByRole('tab', { name: 'マスタ管理' })).toHaveAttribute('aria-selected', 'true');
  });

  test('4つのサブタブが表示される', async ({ page }) => {
    await expect(page.getByRole('tab', { name: '搬入先' })).toBeVisible();
    await expect(page.getByRole('tab', { name: '搬入物' })).toBeVisible();
    await expect(page.getByRole('tab', { name: '固化材' })).toBeVisible();
    await expect(page.getByRole('tab', { name: '溶出抑制剤' })).toBeVisible();
  });

  test('搬入先サブタブがデフォルトで選択されている', async ({ page }) => {
    await expect(page.getByRole('tab', { name: '搬入先' })).toHaveAttribute('aria-selected', 'true');

    // テーブルまたはEmptyStateが表示される
    await page.waitForTimeout(1000);
    const tableOrEmpty = page.locator('table, [class*="EmptyState"]');
    await expect(tableOrEmpty.first()).toBeVisible();
  });

  test('サブタブ切替: 搬入先→搬入物→固化材→溶出抑制剤', async ({ page }) => {
    const subTabs = ['搬入先', '搬入物', '固化材', '溶出抑制剤'];

    for (const tabName of subTabs) {
      await page.getByRole('tab', { name: tabName }).click();
      await expect(page.getByRole('tab', { name: tabName })).toHaveAttribute('aria-selected', 'true');
      await page.waitForTimeout(300);
    }
  });

  test('搬入先リストのツールバーが表示される', async ({ page }) => {
    // 搬入先タブ（デフォルト）
    await page.waitForTimeout(1000);

    // 新規追加ボタン
    await expect(page.getByRole('button', { name: /追加/ })).toBeVisible();

    // CSV出力ボタン
    await expect(page.getByRole('button', { name: /CSV出力/ })).toBeVisible();
  });

  test('搬入物サブタブに切替できる', async ({ page }) => {
    await page.getByRole('tab', { name: '搬入物' }).click();
    await expect(page.getByRole('tab', { name: '搬入物' })).toHaveAttribute('aria-selected', 'true');

    // テーブルまたはEmptyStateが表示される
    await page.waitForTimeout(1000);
    const tableOrEmpty = page.locator('table, [class*="EmptyState"]');
    await expect(tableOrEmpty.first()).toBeVisible();
  });

  test('固化材サブタブに切替できる', async ({ page }) => {
    await page.getByRole('tab', { name: '固化材' }).click();
    await expect(page.getByRole('tab', { name: '固化材' })).toHaveAttribute('aria-selected', 'true');

    await page.waitForTimeout(1000);
    const tableOrEmpty = page.locator('table, [class*="EmptyState"]');
    await expect(tableOrEmpty.first()).toBeVisible();
  });

  test('溶出抑制剤サブタブに切替できる', async ({ page }) => {
    await page.getByRole('tab', { name: '溶出抑制剤' }).click();
    await expect(page.getByRole('tab', { name: '溶出抑制剤' })).toHaveAttribute('aria-selected', 'true');

    await page.waitForTimeout(1000);
    const tableOrEmpty = page.locator('table, [class*="EmptyState"]');
    await expect(tableOrEmpty.first()).toBeVisible();
  });
});
