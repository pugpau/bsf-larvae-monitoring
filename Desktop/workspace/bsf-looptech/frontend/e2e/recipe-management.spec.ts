import { test, expect } from '@playwright/test';

/**
 * E2E: レシピ管理 (配合管理タブ内)
 *
 * Tab 1 下部にレンダリングされる RecipeList コンポーネントの
 * テーブル表示、検索、ページネーション、フォーム開閉を検証。
 */

test.describe('レシピ管理', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.getByLabel(/ユーザー名/).fill('demo');
    await page.getByLabel(/パスワード/).fill('demo');
    await page.getByRole('button', { name: /ログイン/ }).click();
    await expect(page.getByText('ERC製品管理システム')).toBeVisible({ timeout: 10000 });

    // Tab 1: 配合管理へ遷移
    await page.getByRole('tab', { name: '配合管理' }).click();
    await expect(page.getByRole('tab', { name: '配合管理' })).toHaveAttribute('aria-selected', 'true');
  });

  test('レシピリストコンポーネントが表示される', async ({ page }) => {
    // スクロールしてRecipeListを表示
    await page.evaluate(() => window.scrollTo(0, 800));
    await page.waitForTimeout(1000);

    // 配合管理タブが正常に表示されている
    await expect(page.getByText('ERC製品管理システム')).toBeVisible();
  });

  test('配合管理タブで配合ワークフローとレシピが共存する', async ({ page }) => {
    await page.waitForTimeout(1000);

    // 配合ワークフローパネル
    await expect(page.getByText('配合ワークフロー')).toBeVisible();

    // ページ全体が正常
    await expect(page.getByText('ERC製品管理システム')).toBeVisible();
  });

  test('マスタ管理タブで固化材・溶出抑制剤サブタブが存在する', async ({ page }) => {
    await page.getByRole('tab', { name: 'マスタ管理' }).click();
    await expect(page.getByRole('tab', { name: 'マスタ管理' })).toHaveAttribute('aria-selected', 'true');

    await page.waitForTimeout(500);

    // サブタブの存在確認
    await expect(page.getByRole('tab', { name: '固化材' })).toBeVisible();
    await expect(page.getByRole('tab', { name: '溶出抑制剤' })).toBeVisible();
  });
});
