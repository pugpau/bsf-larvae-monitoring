import { test, expect } from '@playwright/test';

/**
 * E2E Flow 4: AIチャット (FAB → Drawer)
 *
 * ChatFab ボタンをクリックして ChatDrawer が開くことを検証。
 */

test.describe('AIチャット / RAG', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.getByLabel(/ユーザー名/).fill('demo');
    await page.getByLabel(/パスワード/).fill('demo');
    await page.getByRole('button', { name: /ログイン/ }).click();
    await expect(page.getByText('ERC製品管理システム')).toBeVisible({ timeout: 10000 });
  });

  test('チャットFABボタンが表示される', async ({ page }) => {
    // FABボタンが画面に存在する
    const fab = page.locator('button[aria-label*="チャット"], button[aria-label*="chat"], .MuiFab-root').first();
    await expect(fab).toBeVisible({ timeout: 5000 });
  });

  test('FABクリックでチャットDrawerが開く', async ({ page }) => {
    const fab = page.locator('button[aria-label*="チャット"], button[aria-label*="chat"], .MuiFab-root').first();
    await fab.click();

    // Drawerが開く (MUI Drawerはrole="presentation"のオーバーレイ)
    await page.waitForTimeout(500);
    // Drawerのコンテンツが存在する
    const drawer = page.locator('.MuiDrawer-root');
    await expect(drawer).toBeVisible({ timeout: 3000 });
  });
});
