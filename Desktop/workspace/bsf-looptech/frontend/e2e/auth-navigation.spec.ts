import { test, expect } from '@playwright/test';

/**
 * E2E Flow 1: ログイン → 5タブ遷移 → ログアウト
 *
 * demoモード (development) で username=demo, password=demo を使用。
 * タブは MUI Tab コンポーネント（role="tab"）で切替、URL変化なし。
 */

test.describe('認証 & タブナビゲーション', () => {
  test('ログインページが表示される', async ({ page }) => {
    await page.goto('/login');
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
    await expect(page.getByLabel(/ユーザー名/)).toBeVisible();
    await expect(page.getByLabel(/パスワード/)).toBeVisible();
  });

  test('demoログイン → ダッシュボード表示', async ({ page }) => {
    await page.goto('/login');
    await page.getByLabel(/ユーザー名/).fill('demo');
    await page.getByLabel(/パスワード/).fill('demo');
    await page.getByRole('button', { name: /ログイン/ }).click();

    // ダッシュボードに遷移
    await expect(page.getByText('ERC製品管理システム')).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('廃棄物処理配合最適化システム')).toBeVisible();
  });

  test('5タブ遷移が動作する', async ({ page }) => {
    // ログイン
    await page.goto('/login');
    await page.getByLabel(/ユーザー名/).fill('demo');
    await page.getByLabel(/パスワード/).fill('demo');
    await page.getByRole('button', { name: /ログイン/ }).click();
    await expect(page.getByText('ERC製品管理システム')).toBeVisible({ timeout: 10000 });

    const tabs = ['搬入予定', '配合管理', '分析ダッシュボード', '品質管理', 'マスタ管理'];

    for (const tabName of tabs) {
      await page.getByRole('tab', { name: tabName }).click();
      // タブが選択状態になる
      await expect(page.getByRole('tab', { name: tabName })).toHaveAttribute('aria-selected', 'true');
    }
  });

  test('ログアウトが動作する', async ({ page }) => {
    // ログイン
    await page.goto('/login');
    await page.getByLabel(/ユーザー名/).fill('demo');
    await page.getByLabel(/パスワード/).fill('demo');
    await page.getByRole('button', { name: /ログイン/ }).click();
    await expect(page.getByText('ERC製品管理システム')).toBeVisible({ timeout: 10000 });

    // ユーザーメニュー → ログアウト
    await page.getByRole('button', { name: /ユーザーメニュー/ }).click();
    await page.getByRole('menuitem', { name: /ログアウト/ }).click();

    // ログインページに戻る
    await expect(page.getByLabel(/ユーザー名/)).toBeVisible({ timeout: 5000 });
  });
});
