import { test, expect } from '@playwright/test';

/**
 * E2E: 搬入予定 (Tab 0)
 *
 * テーブル/カレンダービュー切替、新規登録フォーム、CSV出力を検証。
 */

test.describe('搬入予定', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.getByLabel(/ユーザー名/).fill('demo');
    await page.getByLabel(/パスワード/).fill('demo');
    await page.getByRole('button', { name: /ログイン/ }).click();
    await expect(page.getByText('ERC製品管理システム')).toBeVisible({ timeout: 10000 });
    // Tab 0 is active by default
    await expect(page.getByRole('tab', { name: '搬入予定' })).toHaveAttribute('aria-selected', 'true');
  });

  test('搬入予定ヘッダーとツールバーが表示される', async ({ page }) => {
    await expect(page.getByText('搬入予定')).toBeVisible();
    await expect(page.getByRole('button', { name: /新規登録/ })).toBeVisible();
    await expect(page.getByRole('button', { name: /CSV出力/ })).toBeVisible();
  });

  test('ビュー切替ボタンが操作できる', async ({ page }) => {
    // テーブルビューがデフォルト
    const tableBtn = page.getByRole('button', { name: /テーブル/ });
    await expect(tableBtn).toBeVisible();

    // 週間ビューに切替
    const weekBtn = page.getByRole('button', { name: /週間/ }).first();
    await weekBtn.click();
    await page.waitForTimeout(500);

    // 月間ビューに切替
    const monthBtn = page.getByRole('button', { name: /月間/ });
    await monthBtn.click();
    await page.waitForTimeout(500);

    // テーブルビューに戻る
    await tableBtn.click();
    await page.waitForTimeout(500);
  });

  test('新規登録フォームが開閉できる', async ({ page }) => {
    await page.getByRole('button', { name: /新規登録/ }).click();

    // フォームが表示される
    await expect(page.getByText('搬入予定登録')).toBeVisible({ timeout: 3000 });
    await expect(page.getByLabel('搬入先')).toBeVisible();
    await expect(page.getByLabel('予定日')).toBeVisible();

    // キャンセルで閉じる
    await page.getByRole('button', { name: /キャンセル/ }).click();
    await page.waitForTimeout(500);

    // テーブルに戻る
    await expect(page.getByRole('button', { name: /新規登録/ })).toBeVisible();
  });

  test('カレンダーモードでナビゲーションが動作する', async ({ page }) => {
    // 週間ビューに切替
    await page.getByRole('button', { name: /週間/ }).first().click();
    await page.waitForTimeout(500);

    // 期間ナビゲーションが表示される
    await expect(page.getByRole('button', { name: /前の期間/ })).toBeVisible();
    await expect(page.getByRole('button', { name: /次の期間/ })).toBeVisible();
    await expect(page.getByRole('button', { name: /今日/ })).toBeVisible();

    // ステータスフィルタチップが表示される
    await expect(page.getByText(/全て/)).toBeVisible();
    await expect(page.getByText(/予定/)).toBeVisible();
    await expect(page.getByText(/搬入済/)).toBeVisible();

    // 次の期間に遷移
    await page.getByRole('button', { name: /次の期間/ }).click();
    await page.waitForTimeout(500);

    // 今日に戻る
    await page.getByRole('button', { name: /今日/ }).click();
    await page.waitForTimeout(500);
  });

  test('テーブルビューにページネーションがある', async ({ page }) => {
    await page.waitForTimeout(1000);
    await expect(page.getByText('表示件数:')).toBeVisible();
  });

  test('新規登録フォームで搬入先を選択して入力できる', async ({ page }) => {
    // 新規登録フォームを開く
    await page.getByRole('button', { name: /新規登録/ }).click();
    await expect(page.getByText('搬入予定登録')).toBeVisible({ timeout: 3000 });

    // 搬入先セレクトボックスを開く
    const supplierSelect = page.getByLabel('搬入先');
    await supplierSelect.click();
    await page.waitForTimeout(500);

    // 選択肢が表示される場合は最初の項目を選択
    const firstOption = page.getByRole('option').first();
    if (await firstOption.isVisible({ timeout: 3000 }).catch(() => false)) {
      await firstOption.click();
      await page.waitForTimeout(500);

      // カスケード選択: カテゴリ・搬入物が表示される場合
      const categorySelect = page.getByLabel(/カテゴリ/);
      if (await categorySelect.isVisible({ timeout: 2000 }).catch(() => false)) {
        await categorySelect.click();
        await page.waitForTimeout(500);
        const catOption = page.getByRole('option').first();
        if (await catOption.isVisible({ timeout: 2000 }).catch(() => false)) {
          await catOption.click();
          await page.waitForTimeout(500);
        }
      }

      // 搬入物名選択
      const materialSelect = page.getByLabel(/搬入物/);
      if (await materialSelect.isVisible({ timeout: 2000 }).catch(() => false)) {
        await materialSelect.click();
        await page.waitForTimeout(500);
        const matOption = page.getByRole('option').first();
        if (await matOption.isVisible({ timeout: 2000 }).catch(() => false)) {
          await matOption.click();
          await page.waitForTimeout(500);
        }
      }

      // 予定日は既にフォームに含まれている
      await expect(page.getByLabel('予定日')).toBeVisible();

      // 推定重量を入力
      const weightInput = page.getByLabel(/推定重量|重量/);
      if (await weightInput.isVisible({ timeout: 2000 }).catch(() => false)) {
        await weightInput.fill('15.0');
      }
    }

    // フォームがまだ表示されている
    await expect(page.getByText('搬入予定登録')).toBeVisible();

    // キャンセルで閉じる
    await page.getByRole('button', { name: /キャンセル/ }).click();
    await page.waitForTimeout(500);
    await expect(page.getByRole('button', { name: /新規登録/ })).toBeVisible();
  });
});
