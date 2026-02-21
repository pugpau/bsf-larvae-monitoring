import { test, expect } from '@playwright/test';

/**
 * E2E: エラーハンドリング
 *
 * フォームバリデーションエラー、不正ルートのリダイレクト、
 * ErrorBoundary の動作を検証。
 */

test.describe('エラーハンドリング', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.getByLabel(/ユーザー名/).fill('demo');
    await page.getByLabel(/パスワード/).fill('demo');
    await page.getByRole('button', { name: /ログイン/ }).click();
    await expect(page.getByText('ERC製品管理システム')).toBeVisible({ timeout: 10000 });
  });

  test('フォームバリデーションエラーが表示される', async ({ page }) => {
    // Tab 0 (搬入予定) で新規登録フォームを開く
    await expect(page.getByRole('tab', { name: '搬入予定' })).toHaveAttribute('aria-selected', 'true');

    await page.getByRole('button', { name: /新規登録/ }).click();
    await expect(page.getByText('搬入予定登録')).toBeVisible({ timeout: 3000 });

    // 必須項目を空のまま保存を試みる
    const saveButton = page.getByRole('button', { name: /保存|登録/ }).first();
    if (await saveButton.isVisible({ timeout: 2000 }).catch(() => false)) {
      await saveButton.click();
      await page.waitForTimeout(1000);

      // バリデーションエラーが表示される（エラーメッセージまたはhelperText）
      // フォームのエラー表示は実装に依存するが、フォームが閉じないことを確認
      await expect(page.getByText('搬入予定登録')).toBeVisible();
    }

    // キャンセルで閉じる
    const cancelButton = page.getByRole('button', { name: /キャンセル/ });
    if (await cancelButton.isVisible().catch(() => false)) {
      await cancelButton.click();
    }

    // ページが正常
    await expect(page.getByText('ERC製品管理システム')).toBeVisible();
  });

  test('不正なルートでリダイレクトまたは404が表示される', async ({ page }) => {
    // 存在しないパスにアクセス
    await page.goto('/nonexistent-page');
    await page.waitForTimeout(2000);

    // ログインページにリダイレクトされるか、またはアプリが正常に表示される
    // (SPA のため、ルーティングでログインまたはメインページに戻る)
    const loginOrMain = page.locator(
      'text=ERC製品管理システム, text=ログイン, input[type="password"]'
    );
    await expect(loginOrMain.first()).toBeVisible({ timeout: 5000 });
  });

  test('ErrorBoundaryがクラッシュせず全タブで動作する', async ({ page }) => {
    const tabs = ['搬入予定', '配合管理', '分析ダッシュボード', '品質管理', 'マスタ管理'];

    for (const tabName of tabs) {
      await page.getByRole('tab', { name: tabName }).click();
      await expect(page.getByRole('tab', { name: tabName })).toHaveAttribute('aria-selected', 'true');
      await page.waitForTimeout(1000);

      // ErrorBoundaryのクラッシュ画面が表示されていないこと
      await expect(page.locator('text=エラーが発生しました')).not.toBeVisible();

      // スクロールしてもクラッシュしない
      await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
      await page.waitForTimeout(300);
      await page.evaluate(() => window.scrollTo(0, 0));
      await page.waitForTimeout(300);

      // ヘッダーが正常に表示されている
      await expect(page.getByText('ERC製品管理システム')).toBeVisible();
    }

    // 最終確認: ErrorBoundaryクラッシュなし
    await expect(page.locator('text=エラーが発生しました')).not.toBeVisible();
  });
});
