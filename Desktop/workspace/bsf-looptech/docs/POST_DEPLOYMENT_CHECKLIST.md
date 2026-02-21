# BSF-LoopTech デプロイ後チェックリスト

本番デプロイ完了後、以下の項目を順に確認してください。

---

## 1. 即時確認 (デプロイ直後)

- [ ] 全コンテナが running 状態:
  ```bash
  docker compose -f docker-compose.prod.yml ps
  ```
- [ ] アクティブスロットの確認:
  ```bash
  ./scripts/deploy-blue-green.sh status
  ```
- [ ] `/health` エンドポイント 200 応答:
  ```bash
  curl -s http://localhost:3000/health | python3 -m json.tool
  ```
- [ ] `/ready` エンドポイント 200 応答:
  ```bash
  curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/ready
  ```
- [ ] nginx アクセスログにエラーなし:
  ```bash
  docker compose -f docker-compose.prod.yml logs --tail=20 router
  ```
- [ ] SSL 証明書の有効性 (HTTPS アクセス):
  ```bash
  curl -sk https://localhost/health | python3 -m json.tool
  ```
- [ ] バックエンドログにエラーなし:
  ```bash
  docker compose -f docker-compose.prod.yml logs --tail=50 backend-blue | grep -i error
  ```

## 2. 15分以内の機能確認

- [ ] ブラウザでログイン画面が表示: `http://localhost:3000`
- [ ] demo ユーザーでログイン成功 (初回デプロイ後は管理者ユーザーを作成):
  ```bash
  docker compose -f docker-compose.prod.yml exec backend-blue python scripts/create_admin_user.py
  ```
- [ ] 5タブ全て表示確認:
  - [ ] Tab 0: 搬入予定
  - [ ] Tab 1: 配合管理
  - [ ] Tab 2: 分析ダッシュボード
  - [ ] Tab 3: 品質管理
  - [ ] Tab 4: マスタ管理
- [ ] 搬入予定一覧の取得 (API 直接):
  ```bash
  curl -s http://localhost:3000/api/v1/delivery/schedules?limit=5 | python3 -m json.tool
  ```
- [ ] マスタデータ表示 (業者一覧):
  ```bash
  curl -s http://localhost:3000/api/v1/materials/suppliers?limit=5 | python3 -m json.tool
  ```
- [ ] 配合ワークフロー画面の表示確認

## 3. 30分以内の詳細確認

- [ ] AI チャット応答確認 (LLM 接続):
  ```bash
  # LM Studio が Mac mini ホスト上で起動していることを確認
  curl -s http://localhost:1234/v1/models | python3 -m json.tool
  ```
- [ ] チャットセッション作成テスト:
  ```bash
  curl -s -X POST http://localhost:3000/api/v1/chat/sessions \
    -H "Content-Type: application/json" \
    -d '{"title":"デプロイ後テスト"}' | python3 -m json.tool
  ```
- [ ] CSV エクスポート動作確認 (任意のマスタ):
  ```bash
  curl -s http://localhost:3000/api/v1/materials/suppliers/csv -o /tmp/suppliers.csv
  file /tmp/suppliers.csv
  ```
- [ ] ML 予測 API 応答:
  ```bash
  curl -s http://localhost:3000/api/v1/ml/models | python3 -m json.tool
  ```
- [ ] バッチジョブスケジューラ起動確認:
  ```bash
  curl -s http://localhost:3000/api/v1/batch/jobs | python3 -m json.tool
  ```
- [ ] KPI ダッシュボード API:
  ```bash
  curl -s http://localhost:3000/api/v1/kpi/realtime | python3 -m json.tool
  ```

## 4. launchd / 自動化確認

- [ ] バックアップジョブ登録:
  ```bash
  cp config/com.bsf-looptech.backup.plist ~/Library/LaunchAgents/
  launchctl load ~/Library/LaunchAgents/com.bsf-looptech.backup.plist
  launchctl list | grep bsf-looptech
  ```
- [ ] モニタリングジョブ登録:
  ```bash
  cp config/com.bsf-looptech.monitor.plist ~/Library/LaunchAgents/
  launchctl load ~/Library/LaunchAgents/com.bsf-looptech.monitor.plist
  ```
- [ ] 本番環境自動起動ジョブ登録:
  ```bash
  cp config/com.bsf-looptech.production.plist ~/Library/LaunchAgents/
  launchctl load ~/Library/LaunchAgents/com.bsf-looptech.production.plist
  ```
- [ ] 全ジョブ登録確認:
  ```bash
  launchctl list | grep bsf-looptech
  ```
- [ ] バックアップ手動テスト実行:
  ```bash
  ./scripts/backup_databases.sh
  ls -lt ~/BSF_Backups/postgres/ | head -3
  ```
- [ ] ログディレクトリの確認:
  ```bash
  ls -la logs/
  ```

## 5. ロールバック準備

- [ ] 現在のスロット確認:
  ```bash
  ./scripts/deploy-blue-green.sh status
  ```
- [ ] ロールバック手順の確認:
  ```bash
  # 問題発生時は以下を実行
  ./scripts/deploy-blue-green.sh rollback
  ```
- [ ] DB バックアップの存在確認:
  ```bash
  ls -lt ~/BSF_Backups/postgres/ | head -5
  ```
- [ ] 緊急連絡先・手順書の確認:
  - 運用マニュアル: `OPERATIONS_MANUAL.md`
  - トラブルシューティング: セクション 6
  - 緊急ロールバック: セクション 7

---

## 確認完了後

すべてのチェックが完了したら:

1. このチェックリストに日付と確認者名を記録
2. `kaiwa.md` にデプロイ実施記録を追記
3. 翌日の朝に再度ヘルスチェックを実施

**確認日**: ____年__月__日
**確認者**: ________________
**バージョン**: v____
