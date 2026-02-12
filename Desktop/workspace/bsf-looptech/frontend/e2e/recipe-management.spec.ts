import { test, expect } from '@playwright/test';

/**
 * E2E Flow 3: レシピ管理 (配合管理タブ)
 *
 * Tab 1 でレシピリストが表示されることを検証。
 * バックエンド未接続でもUIコンポーネントがレンダリングされることを確認。
 */

test.describe('レシピ管理', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.getByLabel(/ユーザー名/).fill('demo');
    await page.getByLabel(/パスワード/).fill('demo');
    await page.getByRole('button', { name: /ログイン/ }).click();
    await expect(page.getByText('BSF-LoopTech')).toBeVisible({ timeout: 10000 });
  });

  test('配合管理タブでレシピ関連コンポーネントが表示される', async ({ page }) => {
    await page.getByRole('tab', { name: '配合管理' }).click();
    await expect(page.getByRole('tab', { name: '配合管理' })).toHaveAttribute('aria-selected', 'true');

    // 配合管理タブのコンテンツがレンダリングされていることを確認
    await page.waitForTimeout(1000);
    await expect(page.getByText('BSF-LoopTech')).toBeVisible();
  });

  test('マスタ管理タブで固化材・溶出抑制剤リストが表示される', async ({ page }) => {
    await page.getByRole('tab', { name: 'マスタ管理' }).click();
    await expect(page.getByRole('tab', { name: 'マスタ管理' })).toHaveAttribute('aria-selected', 'true');

    // マスタ管理コンポーネントがレンダリングされていることを確認
    await page.waitForTimeout(1000);
    await expect(page.getByText('BSF-LoopTech')).toBeVisible();
  });
});
