# BSF-LoopTech 本番デプロイ前チェックリスト

Mac mini への初回本番デプロイ前に、すべての項目を確認してください。

---

## 1. ハードウェア確認

- [ ] Mac mini スペック確認 (Apple Silicon M1 以上推奨)
- [ ] CPU: 4コア以上
- [ ] RAM: 16GB 以上 (LLM ローカル推論に必要)
- [ ] SSD: 256GB 以上 (Docker イメージ + DB データ + バックアップ)
- [ ] ネットワーク接続: 有線 LAN (固定 IP または DHCP 予約)
- [ ] UPS (無停電電源装置) 接続確認
- [ ] ディスク空き容量: 50GB 以上 (`df -h /`)

## 2. ソフトウェア前提条件

- [ ] macOS バージョン: Ventura 13 以上 (`sw_vers`)
- [ ] Docker Desktop for Mac インストール済み (`docker --version`)
- [ ] Docker Compose v2 利用可能 (`docker compose version`)
- [ ] Docker Desktop リソース設定: RAM 8GB 以上割当
- [ ] Git インストール済み (`git --version`)
- [ ] Node.js 18 以上 (`node --version`) — フロントエンドビルド用
- [ ] Python 3.11 以上 (`python3 --version`) — スクリプト実行用
- [ ] PostgreSQL クライアント (`psql --version`) — DB 管理用
- [ ] curl インストール済み (`curl --version`) — ヘルスチェック用
- [ ] openssl インストール済み (`openssl version`) — SSL 証明書生成用

## 3. ネットワーク設定

- [ ] ポート 80 (HTTP) が空いている: `lsof -i :80 | grep LISTEN`
- [ ] ポート 443 (HTTPS) が空いている: `lsof -i :443 | grep LISTEN`
- [ ] ポート 3000 (router HTTP) が空いている: `lsof -i :3000 | grep LISTEN`
- [ ] ポート 5432 (PostgreSQL) は 127.0.0.1 のみ公開 (外部遮断)
- [ ] macOS ファイアウォール設定: Docker Desktop を許可
- [ ] DNS または `/etc/hosts` に対象ホスト名を登録 (例: `bsf-looptech.local`)
- [ ] LM Studio 用ポート 1234 が利用可能 (LLM ローカル推論)

## 4. 環境変数準備

- [ ] `.env.production` ファイルを作成 (テンプレート: `config/env.production.template`)
- [ ] `SECRET_KEY` を生成して設定:
  ```bash
  python3 -c "import secrets; print(secrets.token_hex(32))"
  ```
- [ ] `POSTGRES_PASSWORD` を安全なパスワードに変更 (16文字以上推奨)
- [ ] `CORS_ORIGINS` をデプロイ先 URL に設定
- [ ] `LLM_BASE_URL` を設定:
  - LM Studio: `http://host.docker.internal:1234/v1`
  - ollama: `http://host.docker.internal:11434/v1`
- [ ] `SKIP_AUTH=false` であることを確認
- [ ] `LOG_LEVEL=WARNING` に設定 (本番推奨)
- [ ] プレースホルダー (`CHANGE_ME`, `GENERATE_WITH_...`) が残っていないことを確認

## 5. SSL 証明書

- [ ] 自己署名証明書を生成:
  ```bash
  ./scripts/generate_ssl_cert.sh bsf-looptech.local
  ```
- [ ] 証明書ファイルの存在確認: `config/ssl/server.crt`
- [ ] 秘密鍵ファイルの存在確認: `config/ssl/server.key`
- [ ] 秘密鍵のパーミッション: `600` (`ls -l config/ssl/server.key`)
- [ ] 証明書の有効期限確認:
  ```bash
  openssl x509 -in config/ssl/server.crt -noout -enddate
  ```
- [ ] (オプション) Let's Encrypt 証明書を使用する場合は certbot を設定

## 6. Git リポジトリ

- [ ] main ブランチに切り替え: `git checkout main`
- [ ] 最新版を取得: `git pull origin main`
- [ ] 未コミットの変更がないことを確認: `git status`
- [ ] リリースタグを付与:
  ```bash
  git tag -a v1.0.0 -m "初回本番リリース"
  git push origin v1.0.0
  ```

## 7. Alembic マイグレーション

- [ ] マイグレーション整合性チェック:
  ```bash
  ./scripts/verify_migration.sh
  ```
- [ ] マイグレーションが単一 HEAD であることを確認 (ブランチ競合なし)
- [ ] 全 11 マイグレーションが正しくチェーン接続されていることを確認

## 8. バックアップ計画

- [ ] バックアップ保存先ディレクトリを作成: `mkdir -p ~/BSF_Backups/postgres`
- [ ] ログディレクトリを作成: `mkdir -p logs`
- [ ] 初回デプロイ前に macOS Time Machine スナップショットを取得
- [ ] launchd バックアップ plist を確認:
  ```bash
  ls config/com.bsf-looptech.backup.plist
  ```
- [ ] バックアップスクリプトに実行権限を付与:
  ```bash
  chmod +x scripts/backup_databases.sh
  ```

## 9. デプロイ実行

- [ ] ドライラン実行:
  ```bash
  ./scripts/deploy_dryrun.sh
  ```
- [ ] ドライラン結果が全て PASS であることを確認
- [ ] 本番デプロイ実行:
  ```bash
  ./scripts/deploy-blue-green.sh init
  ```
- [ ] デプロイ後チェックリストへ進む: `docs/POST_DEPLOYMENT_CHECKLIST.md`

---

**注意事項**

- `.env.production` は `.gitignore` に含まれており、Git にコミットされません
- `config/ssl/` 内の証明書・秘密鍵も `.gitignore` で除外済みです
- すべてのスクリプトは `bsf-looptech/` ディレクトリから実行してください
