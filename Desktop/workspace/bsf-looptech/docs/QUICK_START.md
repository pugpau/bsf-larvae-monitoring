# BSF-LoopTech クイックスタートガイド

システム管理者向けの 10 分セットアップ手順です。

---

## 前提条件

以下がインストール済みであることを確認してください。

- **Docker Desktop** (v24 以上) が起動していること
- **Git** がインストール済みであること
- インターネット接続が利用可能であること（Docker イメージ取得用）

---

## ステップ 1: リポジトリ取得（2分）

```bash
git clone <リポジトリURL> bsf-looptech
cd bsf-looptech
```

---

## ステップ 2: 環境設定（3分）

```bash
# テンプレートから本番環境設定ファイルを作成
cp config/env.production.template .env.production
```

`.env.production` を開き、以下の2項目を **必ず変更** してください。

```bash
# SECRET_KEY — JWT認証の署名に使用する秘密鍵
# 以下のコマンドで安全な値を生成します
python3 -c "import secrets; print(secrets.token_hex(32))"
# 出力された値を SECRET_KEY= の後にペーストしてください

# POSTGRES_PASSWORD — データベースのパスワード
# DATABASE_URL 内のパスワードも同じ値に合わせてください
```

その他の設定項目はデフォルト値のまま動作します。

---

## ステップ 3: 初回起動（5分）

```bash
./scripts/deploy-blue-green.sh init
```

このコマンドにより以下が自動実行されます。

1. Docker イメージのビルド（初回は数分かかります）
2. PostgreSQL の起動とデータベース初期化
3. バックエンド（FastAPI）の起動とマイグレーション実行
4. フロントエンド（React）のビルドと nginx 配信設定
5. ヘルスチェックによる動作確認

---

## 動作確認

ブラウザで以下のURLにアクセスします。

| URL | 説明 |
|-----|------|
| http://localhost:3000 | メイン画面（HTTP） |
| https://localhost | メイン画面（HTTPS、自己署名証明書の警告あり） |

ログイン画面が表示されたら、初期ユーザーを登録してログインします。

ログイン後、5つのタブ（搬入予定・配合管理・分析ダッシュボード・品質管理・マスタ管理）が表示されれば成功です。

---

## デモデータ投入（オプション）

動作確認やトレーニング用にサンプルデータを投入できます。

```bash
# 基本マスタデータ（業者・固化材・溶出抑制剤・レシピ）
python scripts/seed_dev_data.py

# 搬入記録 300件
python scripts/seed_waste_300.py

# 配合ワークフローのデモデータ（8シナリオ）
python scripts/seed_formulation_demo.py
```

---

## システムの停止と再起動

```bash
# 停止
docker compose -f docker-compose.prod.yml down

# 再起動（データは保持されます）
docker compose -f docker-compose.prod.yml up -d
```

---

## 次のステップ

| ドキュメント | 内容 |
|-------------|------|
| `docs/OPERATOR_GUIDE.md` | オペレーター向け操作ガイド |
| `OPERATIONS_MANUAL.md` | システム管理者向け詳細運用手順 |
| `docs/TROUBLESHOOTING_FAQ.md` | よくある問題と対処法 |
| `docs/MAINTENANCE_SCHEDULE.md` | メンテナンススケジュール |
