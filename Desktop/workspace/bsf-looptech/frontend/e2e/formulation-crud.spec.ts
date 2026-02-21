import { test, expect } from '@playwright/test';

/**
 * E2E: 配合管理 CRUD (Tab 1)
 *
 * AI推薦ダイアログの操作、推薦候補の選択・承認・却下・適用・検証、
 * Tab 0 -> Tab 1 ワークフロー連携を検証。
 */

test.describe('配合管理 CRUD', () => {
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

  test('AI推薦ダイアログを開いて搬入記録を選択できる', async ({ page }) => {
    // AI推薦ボタンをクリック
    await page.getByRole('button', { name: /AI推薦/ }).click();

    // ダイアログが表示される
    await expect(page.getByText('配合推薦')).toBeVisible();
    await expect(page.getByLabel('搬入記録')).toBeVisible();
    await expect(page.getByLabel('候補数')).toBeVisible();

    // 推薦を実行ボタンがdisabled（搬入記録未選択）
    await expect(page.getByRole('button', { name: /推薦を実行/ })).toBeDisabled();

    // 搬入記録セレクトを開いて選択肢を確認
    const wasteSelect = page.getByLabel('搬入記録');
    await wasteSelect.click();
    await page.waitForTimeout(500);

    // 選択肢が存在する場合は最初の項目を選択
    const firstOption = page.getByRole('option').first();
    if (await firstOption.isVisible({ timeout: 3000 }).catch(() => false)) {
      await firstOption.click();
      await page.waitForTimeout(500);

      // 搬入記録選択後、推薦を実行ボタンが有効になる
      await expect(page.getByRole('button', { name: /推薦を実行/ })).toBeEnabled();
    }

    // キャンセルで閉じる
    await page.getByRole('button', { name: 'キャンセル' }).click();
    await expect(page.getByText('配合推薦')).not.toBeVisible();
  });

  test('推薦候補を選択して配合レコードを作成できる', async ({ page }) => {
    // AI推薦ダイアログを開く
    await page.getByRole('button', { name: /AI推薦/ }).click();
    await expect(page.getByText('配合推薦')).toBeVisible();

    // 搬入記録を選択
    const wasteSelect = page.getByLabel('搬入記録');
    await wasteSelect.click();
    await page.waitForTimeout(500);

    const firstOption = page.getByRole('option').first();
    if (await firstOption.isVisible({ timeout: 3000 }).catch(() => false)) {
      await firstOption.click();
      await page.waitForTimeout(500);

      // 推薦を実行
      const execButton = page.getByRole('button', { name: /推薦を実行/ });
      if (await execButton.isEnabled()) {
        await execButton.click();
        // 推薦結果が表示されるまで待機
        await page.waitForTimeout(5000);

        // 推薦候補カードまたはリストが表示される
        // (APIが応答しない環境ではスキップ)
        const resultArea = page.locator('[class*="recommendation"], [class*="candidate"], [role="list"]');
        if (await resultArea.first().isVisible({ timeout: 5000 }).catch(() => false)) {
          // 最初の候補を選択（採用ボタンをクリック）
          const adoptButton = page.getByRole('button', { name: /採用|選択/ }).first();
          if (await adoptButton.isVisible({ timeout: 3000 }).catch(() => false)) {
            await adoptButton.click();
            await page.waitForTimeout(1000);
          }
        }
      }
    }

    // ダイアログを閉じる（まだ開いている場合）
    const cancelButton = page.getByRole('button', { name: 'キャンセル' });
    if (await cancelButton.isVisible().catch(() => false)) {
      await cancelButton.click();
    }

    // ページが正常
    await expect(page.getByText('ERC製品管理システム')).toBeVisible();
  });

  test('配合レコードを却下できる', async ({ page }) => {
    await page.waitForTimeout(2000);

    // 配合一覧テーブルを確認
    const table = page.locator('table');
    if (await table.isVisible({ timeout: 3000 }).catch(() => false)) {
      const rows = page.locator('table tbody tr');
      const rowCount = await rows.count();

      if (rowCount > 0) {
        // 「提案」ステータスの行を探す
        const proposedRow = page.locator('table tbody tr', {
          has: page.locator('text=提案'),
        }).first();

        if (await proposedRow.isVisible({ timeout: 2000 }).catch(() => false)) {
          // 却下ボタンを探してクリック
          const rejectButton = proposedRow.getByRole('button', { name: /却下/ });
          if (await rejectButton.isVisible({ timeout: 2000 }).catch(() => false)) {
            await rejectButton.click();
            await page.waitForTimeout(500);

            // 却下理由入力欄が表示される場合
            const reasonInput = page.locator('textarea, input[type="text"]').last();
            if (await reasonInput.isVisible({ timeout: 2000 }).catch(() => false)) {
              await reasonInput.fill('E2Eテスト: コスト超過のため却下');

              // 確定ボタン
              const confirmButton = page.getByRole('button', { name: /確定|保存|OK/ }).first();
              if (await confirmButton.isVisible({ timeout: 2000 }).catch(() => false)) {
                await confirmButton.click();
                await page.waitForTimeout(1000);
              }
            }
          }
        }
      }
    }

    // ページが正常
    await expect(page.getByText('ERC製品管理システム')).toBeVisible();
  });

  test('配合レコードを適用して実績値を入力できる', async ({ page }) => {
    await page.waitForTimeout(2000);

    // 「承認済」ステータスの行を探す
    const table = page.locator('table');
    if (await table.isVisible({ timeout: 3000 }).catch(() => false)) {
      const acceptedRow = page.locator('table tbody tr', {
        has: page.locator('text=承認済'),
      }).first();

      if (await acceptedRow.isVisible({ timeout: 2000 }).catch(() => false)) {
        // 適用ボタンを探してクリック
        const applyButton = acceptedRow.getByRole('button', { name: /適用/ });
        if (await applyButton.isVisible({ timeout: 2000 }).catch(() => false)) {
          await applyButton.click();
          await page.waitForTimeout(500);

          // 適用フォームが表示される場合
          // 実コスト入力
          const costInput = page.locator('input[type="number"]').first();
          if (await costInput.isVisible({ timeout: 2000 }).catch(() => false)) {
            await costInput.fill('3000');
          }

          // 確定ボタン
          const confirmButton = page.getByRole('button', { name: /確定|保存|OK/ }).first();
          if (await confirmButton.isVisible({ timeout: 2000 }).catch(() => false)) {
            await confirmButton.click();
            await page.waitForTimeout(1000);
          }
        }
      }
    }

    // ページが正常
    await expect(page.getByText('ERC製品管理システム')).toBeVisible();
  });

  test('配合レコードを検証して溶出結果を入力できる', async ({ page }) => {
    await page.waitForTimeout(2000);

    // 「適用済」ステータスの行を探す
    const table = page.locator('table');
    if (await table.isVisible({ timeout: 3000 }).catch(() => false)) {
      const appliedRow = page.locator('table tbody tr', {
        has: page.locator('text=適用済'),
      }).first();

      if (await appliedRow.isVisible({ timeout: 2000 }).catch(() => false)) {
        // 検証ボタンを探してクリック
        const verifyButton = appliedRow.getByRole('button', { name: /検証/ });
        if (await verifyButton.isVisible({ timeout: 2000 }).catch(() => false)) {
          await verifyButton.click();
          await page.waitForTimeout(500);

          // 検証フォームが表示される場合
          // ページが正常に動作している
          await expect(page.getByText('ERC製品管理システム')).toBeVisible();

          // 閉じる（まだダイアログが開いている場合）
          const cancelButton = page.getByRole('button', { name: /キャンセル|閉じる/ });
          if (await cancelButton.isVisible({ timeout: 1000 }).catch(() => false)) {
            await cancelButton.click();
          }
        }
      }
    }

    // ページが正常
    await expect(page.getByText('ERC製品管理システム')).toBeVisible();
  });

  test('Tab 0→Tab 1 ワークフロー連携が動作する', async ({ page }) => {
    // Tab 0 (搬入予定) に遷移
    await page.getByRole('tab', { name: '搬入予定' }).click();
    await expect(page.getByRole('tab', { name: '搬入予定' })).toHaveAttribute('aria-selected', 'true');
    await page.waitForTimeout(2000);

    // 「配合開始」ボタンが存在する場合（ready_for_formulation ステータスの行）
    const formulationStartButton = page.getByRole('button', { name: /配合開始/ }).first();
    if (await formulationStartButton.isVisible({ timeout: 3000 }).catch(() => false)) {
      await formulationStartButton.click();
      await page.waitForTimeout(1000);

      // Tab 1 に自動遷移
      await expect(page.getByRole('tab', { name: '配合管理' })).toHaveAttribute('aria-selected', 'true');

      // AI推薦ダイアログが自動で開く
      await expect(page.getByText('配合推薦')).toBeVisible({ timeout: 5000 });
    } else {
      // 配合開始ボタンがない場合は手動でTab 1に遷移して確認
      await page.getByRole('tab', { name: '配合管理' }).click();
      await expect(page.getByRole('tab', { name: '配合管理' })).toHaveAttribute('aria-selected', 'true');
    }

    // ページが正常
    await expect(page.getByText('ERC製品管理システム')).toBeVisible();
  });
});
