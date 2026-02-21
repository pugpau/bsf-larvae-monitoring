import { test, expect } from '@playwright/test';

/**
 * E2E: 分析ダッシュボード & 品質管理 タブレンダリング
 *
 * Tab 2 (分析ダッシュボード) と Tab 3 (品質管理) が
 * 正常にレンダリングされ、ErrorBoundaryがクラッシュしないことを検証。
 */

test.describe('分析・品質 タブレンダリング', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.getByLabel(/ユーザー名/).fill('demo');
    await page.getByLabel(/パスワード/).fill('demo');
    await page.getByRole('button', { name: /ログイン/ }).click();
    await expect(page.getByText('ERC製品管理システム')).toBeVisible({ timeout: 10000 });
  });

  test('分析ダッシュボードタブがレンダリングされる', async ({ page }) => {
    await page.getByRole('tab', { name: '分析ダッシュボード' }).click();
    await expect(page.getByRole('tab', { name: '分析ダッシュボード' })).toHaveAttribute('aria-selected', 'true');

    // ErrorBoundaryによるクラッシュ表示がないこと
    await page.waitForTimeout(2000);
    await expect(page.locator('text=エラーが発生しました')).not.toBeVisible();
    await expect(page.getByText('ERC製品管理システム')).toBeVisible();
  });

  test('品質管理タブがレンダリングされる', async ({ page }) => {
    await page.getByRole('tab', { name: '品質管理' }).click();
    await expect(page.getByRole('tab', { name: '品質管理' })).toHaveAttribute('aria-selected', 'true');

    // ErrorBoundaryクラッシュなし
    await page.waitForTimeout(2000);
    await expect(page.locator('text=エラーが発生しました')).not.toBeVisible();
    await expect(page.getByText('ERC製品管理システム')).toBeVisible();
  });

  test('全5タブを順番に遷移してもクラッシュしない', async ({ page }) => {
    const tabs = ['搬入予定', '配合管理', '分析ダッシュボード', '品質管理', 'マスタ管理'];

    for (const tabName of tabs) {
      await page.getByRole('tab', { name: tabName }).click();
      await expect(page.getByRole('tab', { name: tabName })).toHaveAttribute('aria-selected', 'true');
      await page.waitForTimeout(500);

      // ErrorBoundaryクラッシュなし
      await expect(page.locator('text=エラーが発生しました')).not.toBeVisible();
    }

    // 最終的にアプリが正常
    await expect(page.getByText('ERC製品管理システム')).toBeVisible();
  });

  test('分析ダッシュボードでスクロールしてもクラッシュしない', async ({ page }) => {
    await page.getByRole('tab', { name: '分析ダッシュボード' }).click();
    await page.waitForTimeout(1000);

    // スクロールダウン
    for (let i = 0; i < 3; i++) {
      await page.evaluate((offset) => window.scrollTo(0, offset), (i + 1) * 500);
      await page.waitForTimeout(300);
    }

    // スクロールトップに戻る
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.waitForTimeout(300);

    await expect(page.getByText('ERC製品管理システム')).toBeVisible();
  });
});
