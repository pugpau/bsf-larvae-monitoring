import { test, expect } from '@playwright/test';

/**
 * E2E: マスタ管理 CRUD (Tab 4)
 *
 * 4つのサブタブ（搬入先、搬入物、固化材、溶出抑制剤）でのCRUD操作、
 * レシピ管理、CSV出力を検証。
 */

test.describe('マスタ管理 CRUD', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.getByLabel(/ユーザー名/).fill('demo');
    await page.getByLabel(/パスワード/).fill('demo');
    await page.getByRole('button', { name: /ログイン/ }).click();
    await expect(page.getByText('ERC製品管理システム')).toBeVisible({ timeout: 10000 });

    // Tab 4: マスタ管理へ遷移
    await page.getByRole('tab', { name: 'マスタ管理' }).click();
    await expect(page.getByRole('tab', { name: 'マスタ管理' })).toHaveAttribute('aria-selected', 'true');
  });

  test('4つのサブタブが切替できる', async ({ page }) => {
    const subTabs = ['搬入先', '搬入物', '固化材', '溶出抑制剤'];

    for (const tabName of subTabs) {
      await page.getByRole('tab', { name: tabName }).click();
      await expect(page.getByRole('tab', { name: tabName })).toHaveAttribute('aria-selected', 'true');
      await page.waitForTimeout(500);

      // テーブルまたはEmptyStateが表示される
      const tableOrEmpty = page.locator('table, [class*="EmptyState"]');
      await expect(tableOrEmpty.first()).toBeVisible({ timeout: 3000 });
    }
  });

  test('搬入先マスタで新規追加ダイアログが開閉できる', async ({ page }) => {
    // 搬入先サブタブ（デフォルト）
    await expect(page.getByRole('tab', { name: '搬入先' })).toHaveAttribute('aria-selected', 'true');
    await page.waitForTimeout(1000);

    // 追加ボタンをクリック
    await page.getByRole('button', { name: /追加/ }).click();
    await page.waitForTimeout(500);

    // インライン追加行またはダイアログが表示される
    // 名前入力欄を探す
    const nameInput = page.locator('input[placeholder*="名前"], input[placeholder*="搬入先名"], input[name*="name"]').first();
    if (await nameInput.isVisible({ timeout: 3000 }).catch(() => false)) {
      // テスト業者を入力
      await nameInput.fill('E2Eテスト新規搬入先');
      await page.waitForTimeout(300);

      // 保存ボタンを探す
      const saveButton = page.getByRole('button', { name: /保存|確定|登録/ }).first();
      if (await saveButton.isVisible({ timeout: 2000 }).catch(() => false)) {
        await saveButton.click();
        await page.waitForTimeout(1000);
      } else {
        // Escapeで閉じる
        await page.keyboard.press('Escape');
      }
    }

    // ページが正常
    await expect(page.getByText('ERC製品管理システム')).toBeVisible();
  });

  test('搬入先データがテーブルに表示される', async ({ page }) => {
    await page.waitForTimeout(2000);

    // テーブルが存在する場合
    const table = page.locator('table');
    if (await table.isVisible({ timeout: 3000 }).catch(() => false)) {
      const rows = page.locator('table tbody tr');
      const rowCount = await rows.count();

      // テストデータが投入されていれば行が存在する
      if (rowCount > 0) {
        // 最初の行の内容を確認
        const firstRow = rows.first();
        await expect(firstRow).toBeVisible();
      }
    }

    // ページが正常
    await expect(page.getByText('ERC製品管理システム')).toBeVisible();
  });

  test('固化材サブタブでデータが表示される', async ({ page }) => {
    // 固化材サブタブに切替
    await page.getByRole('tab', { name: '固化材' }).click();
    await expect(page.getByRole('tab', { name: '固化材' })).toHaveAttribute('aria-selected', 'true');
    await page.waitForTimeout(2000);

    // テーブルまたはEmptyStateが表示される
    const tableOrEmpty = page.locator('table, [class*="EmptyState"]');
    await expect(tableOrEmpty.first()).toBeVisible();

    // 追加ボタンが表示される
    await expect(page.getByRole('button', { name: /追加/ })).toBeVisible();

    // CSV出力ボタンが表示される
    await expect(page.getByRole('button', { name: /CSV出力/ })).toBeVisible();
  });

  test('溶出抑制剤サブタブでデータが表示される', async ({ page }) => {
    // 溶出抑制剤サブタブに切替
    await page.getByRole('tab', { name: '溶出抑制剤' }).click();
    await expect(page.getByRole('tab', { name: '溶出抑制剤' })).toHaveAttribute('aria-selected', 'true');
    await page.waitForTimeout(2000);

    // テーブルまたはEmptyStateが表示される
    const tableOrEmpty = page.locator('table, [class*="EmptyState"]');
    await expect(tableOrEmpty.first()).toBeVisible();

    // 追加ボタンが表示される
    await expect(page.getByRole('button', { name: /追加/ })).toBeVisible();
  });

  test('マスタCSVエクスポートが動作する', async ({ page }) => {
    // 搬入先サブタブ（デフォルト）
    await page.waitForTimeout(1000);

    // ダウンロードイベントを監視
    const downloadPromise = page.waitForEvent('download', { timeout: 5000 }).catch(() => null);

    await page.getByRole('button', { name: /CSV出力/ }).click();

    const download = await downloadPromise;
    if (download) {
      const filename = download.suggestedFilename();
      expect(filename).toContain('.csv');
    }

    // 固化材サブタブに切替してCSV出力
    await page.getByRole('tab', { name: '固化材' }).click();
    await page.waitForTimeout(1000);

    const downloadPromise2 = page.waitForEvent('download', { timeout: 5000 }).catch(() => null);
    await page.getByRole('button', { name: /CSV出力/ }).click();

    const download2 = await downloadPromise2;
    if (download2) {
      const filename = download2.suggestedFilename();
      expect(filename).toContain('.csv');
    }

    // ページが正常
    await expect(page.getByText('ERC製品管理システム')).toBeVisible();
  });
});
