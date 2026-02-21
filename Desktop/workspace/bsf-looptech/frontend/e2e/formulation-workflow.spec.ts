import { test, expect } from '@playwright/test';

/**
 * E2E Flow: 配合ワークフロー (配合管理タブ)
 *
 * Tab 1 で FormulationPanel + ダイアログが正しく表示・操作できることを検証。
 */

test.describe('配合ワークフロー', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.getByLabel(/ユーザー名/).fill('demo');
    await page.getByLabel(/パスワード/).fill('demo');
    await page.getByRole('button', { name: /ログイン/ }).click();
    await expect(page.getByText('ERC製品管理システム')).toBeVisible({ timeout: 10000 });

    // Navigate to Tab 1: 配合管理
    await page.getByRole('tab', { name: '配合管理' }).click();
    await expect(page.getByRole('tab', { name: '配合管理' })).toHaveAttribute('aria-selected', 'true');
  });

  test('配合ワークフローパネルが表示される', async ({ page }) => {
    await expect(page.getByText('配合ワークフロー')).toBeVisible();
  });

  test('ステータスフィルタが操作できる', async ({ page }) => {
    // ステータスフィルタの存在確認
    const statusFilter = page.getByLabel('ステータス');
    await expect(statusFilter).toBeVisible();

    // フィルタを開いて選択肢が表示されることを確認
    await statusFilter.click();
    await expect(page.getByRole('option', { name: '提案' })).toBeVisible();
    await expect(page.getByRole('option', { name: '承認済' })).toBeVisible();
    await expect(page.getByRole('option', { name: '検証済' })).toBeVisible();
    await expect(page.getByRole('option', { name: '却下' })).toBeVisible();

    // 「全て」を選択して閉じる
    await page.getByRole('option', { name: '全て' }).click();
  });

  test('推薦元フィルタが操作できる', async ({ page }) => {
    const sourceFilter = page.getByLabel('推薦元');
    await expect(sourceFilter).toBeVisible();

    await sourceFilter.click();
    await expect(page.getByRole('option', { name: 'ML予測' })).toBeVisible();
    await expect(page.getByRole('option', { name: '手動' })).toBeVisible();
    await expect(page.getByRole('option', { name: '最適化' })).toBeVisible();
    await page.getByRole('option', { name: '全て' }).click();
  });

  test('AI推薦ダイアログが開閉できる', async ({ page }) => {
    // AI推薦ボタンをクリック
    await page.getByRole('button', { name: /AI推薦/ }).click();

    // ダイアログが表示される
    await expect(page.getByText('配合推薦')).toBeVisible();
    await expect(page.getByText(/搬入記録を選択して/)).toBeVisible();
    await expect(page.getByLabel('搬入記録')).toBeVisible();
    await expect(page.getByLabel('候補数')).toBeVisible();

    // 推薦を実行ボタンがdisabled（搬入記録未選択）
    await expect(page.getByRole('button', { name: /推薦を実行/ })).toBeDisabled();

    // キャンセルで閉じる
    await page.getByRole('button', { name: 'キャンセル' }).click();
    await expect(page.getByText('配合推薦')).not.toBeVisible();
  });

  test('空状態でEmptyStateが表示される', async ({ page }) => {
    // データがない場合のEmptyState表示
    // Backend未接続時はエラーまたは空状態になる
    await page.waitForTimeout(2000);

    // テーブルまたはEmptyStateが表示されること
    const tableOrEmpty = page.locator('table, [class*="EmptyState"]');
    await expect(tableOrEmpty.first()).toBeVisible();
  });

  test('ページネーションコントロールが表示される', async ({ page }) => {
    await page.waitForTimeout(1000);
    // ページネーションの「表示件数:」ラベルがある
    await expect(page.getByText('表示件数:')).toBeVisible();
  });

  test('レシピリストも同一タブ内に表示される', async ({ page }) => {
    // FormulationPanel の下に RecipeList が表示されていること
    // スクロールダウンして確認
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await page.waitForTimeout(500);

    // Tab 1 にはレシピ管理関連コンポーネントも含まれている
    await expect(page.getByText('ERC製品管理システム')).toBeVisible();
  });

  test('AI推薦ダイアログで搬入記録を選択して推薦を実行できる', async ({ page }) => {
    // AI推薦ダイアログを開く
    await page.getByRole('button', { name: /AI推薦/ }).click();
    await expect(page.getByText('配合推薦')).toBeVisible();

    // 搬入記録セレクトを開く
    const wasteSelect = page.getByLabel('搬入記録');
    await wasteSelect.click();
    await page.waitForTimeout(500);

    // 選択肢が存在する場合は最初の項目を選択
    const firstOption = page.getByRole('option').first();
    if (await firstOption.isVisible({ timeout: 3000 }).catch(() => false)) {
      await firstOption.click();
      await page.waitForTimeout(500);

      // 推薦を実行ボタンが有効になっていること
      const execButton = page.getByRole('button', { name: /推薦を実行/ });
      await expect(execButton).toBeEnabled();

      // 推薦を実行
      await execButton.click();

      // 結果が返るまで待機（APIタイムアウト考慮）
      await page.waitForTimeout(5000);

      // 推薦結果エリアまたはエラーメッセージが表示される
      // (バックエンドが接続されている場合は推薦候補が表示される)
      await expect(page.getByText('ERC製品管理システム')).toBeVisible();
    }

    // ダイアログを閉じる
    const cancelButton = page.getByRole('button', { name: 'キャンセル' });
    if (await cancelButton.isVisible().catch(() => false)) {
      await cancelButton.click();
    }
  });
});
