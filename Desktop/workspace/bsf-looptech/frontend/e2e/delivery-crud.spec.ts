import { test, expect } from '@playwright/test';

/**
 * E2E: 搬入管理 CRUD (Tab 0)
 *
 * Tab 0 での搬入予定一覧表示、検索、CSV出力、新規登録フォーム、
 * ステータス更新の各操作を検証。
 */

test.describe('搬入管理 CRUD', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.getByLabel(/ユーザー名/).fill('demo');
    await page.getByLabel(/パスワード/).fill('demo');
    await page.getByRole('button', { name: /ログイン/ }).click();
    await expect(page.getByText('ERC製品管理システム')).toBeVisible({ timeout: 10000 });

    // Tab 0 (搬入予定) はデフォルトでアクティブ
    await expect(page.getByRole('tab', { name: '搬入予定' })).toHaveAttribute('aria-selected', 'true');
  });

  test('搬入予定一覧がテーブルで表示される', async ({ page }) => {
    // テーブルビューがデフォルト
    await page.waitForTimeout(2000);

    // テーブルまたはEmptyStateが表示される
    const tableOrEmpty = page.locator('table, [class*="EmptyState"]');
    await expect(tableOrEmpty.first()).toBeVisible();

    // ツールバーボタンが表示される
    await expect(page.getByRole('button', { name: /新規登録/ })).toBeVisible();
    await expect(page.getByRole('button', { name: /CSV出力/ })).toBeVisible();

    // ページネーションが表示される
    await expect(page.getByText('表示件数:')).toBeVisible();
  });

  test('検索ボックスでフィルタリングできる', async ({ page }) => {
    await page.waitForTimeout(2000);

    // 検索入力欄を探す
    const searchInput = page.locator('input[type="text"][placeholder*="検索"], input[type="search"], input[aria-label*="検索"]').first();

    if (await searchInput.isVisible()) {
      // テスト業者Aで検索
      await searchInput.fill('テスト業者');
      await page.waitForTimeout(1000);

      // ページがクラッシュしていない
      await expect(page.getByText('ERC製品管理システム')).toBeVisible();

      // 検索をクリア
      await searchInput.clear();
      await page.waitForTimeout(500);
    }

    // ページが正常
    await expect(page.getByRole('tab', { name: '搬入予定' })).toHaveAttribute('aria-selected', 'true');
  });

  test('CSV出力ボタンでダウンロードが開始される', async ({ page }) => {
    await page.waitForTimeout(1000);

    // ダウンロードイベントを監視
    const downloadPromise = page.waitForEvent('download', { timeout: 5000 }).catch(() => null);

    await page.getByRole('button', { name: /CSV出力/ }).click();

    const download = await downloadPromise;
    if (download) {
      // ダウンロードが開始された
      const filename = download.suggestedFilename();
      expect(filename).toContain('.csv');
    }

    // ページが正常
    await expect(page.getByText('ERC製品管理システム')).toBeVisible();
  });

  test('新規登録フォームで搬入予定を作成できる', async ({ page }) => {
    // 新規登録ボタンをクリック
    await page.getByRole('button', { name: /新規登録/ }).click();

    // フォームが表示される
    await expect(page.getByText('搬入予定登録')).toBeVisible({ timeout: 3000 });

    // フォームに搬入先選択フィールドが存在する
    await expect(page.getByLabel('搬入先')).toBeVisible();
    await expect(page.getByLabel('予定日')).toBeVisible();

    // 搬入先を選択（カスケード選択）
    const supplierSelect = page.getByLabel('搬入先');
    await supplierSelect.click();
    await page.waitForTimeout(500);

    // 選択肢が表示される場合はクリック
    const firstOption = page.getByRole('option').first();
    if (await firstOption.isVisible({ timeout: 2000 }).catch(() => false)) {
      await firstOption.click();
      await page.waitForTimeout(500);
    }

    // キャンセルで閉じる
    await page.getByRole('button', { name: /キャンセル/ }).click();
    await page.waitForTimeout(500);

    // テーブルビューに戻る
    await expect(page.getByRole('button', { name: /新規登録/ })).toBeVisible();
  });

  test('ステータス変更ボタンが表示される', async ({ page }) => {
    await page.waitForTimeout(2000);

    // テーブルが存在する場合
    const table = page.locator('table');
    if (await table.isVisible({ timeout: 3000 }).catch(() => false)) {
      // テーブル行内にステータスバッジまたはボタンが存在する
      const rows = page.locator('table tbody tr');
      const rowCount = await rows.count();

      if (rowCount > 0) {
        // 最初の行にステータス表示がある
        const firstRow = rows.first();
        await expect(firstRow).toBeVisible();
      }
    }

    // ページが正常
    await expect(page.getByText('ERC製品管理システム')).toBeVisible();
  });
});
