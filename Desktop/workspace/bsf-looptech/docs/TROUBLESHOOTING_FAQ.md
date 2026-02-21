# BSF-LoopTech トラブルシューティング FAQ

よくあるトラブルと対処法をまとめたガイドです。
オペレーター向けの画面操作と、管理者向けのターミナル操作を分けて記載しています。

---

## Q1: システムにアクセスできません

### 症状
ブラウザで URL にアクセスしても、ページが表示されない。
「このサイトにアクセスできません」「接続がタイムアウトしました」などのエラーが表示される。

### 原因
1. Docker コンテナが停止している
2. ネットワーク（LAN）の接続障害
3. ブラウザのキャッシュの問題

### 対処法

**オペレーター向け:**
1. ブラウザのアドレスバーに正しい URL が入力されているか確認してください
2. 別のブラウザ（Chrome / Edge / Firefox）で試してください
3. LAN ケーブルや Wi-Fi の接続状態を確認してください
4. 改善しない場合は管理者に連絡してください

**管理者向け:**
```bash
# コンテナの稼働状態を確認
docker compose -f docker-compose.prod.yml ps

# 全コンテナが停止している場合は再起動
docker compose -f docker-compose.prod.yml up -d

# ヘルスチェック
curl -s http://localhost:3000/health | python3 -m json.tool
```

### それでも解決しない場合
サーバー（Mac mini）のネットワーク設定やファイアウォール設定を確認してください。
Docker Desktop が起動しているかも確認してください。

---

## Q2: ログインできません

### 症状
ログイン画面でユーザー名とパスワードを入力しても、ログインに失敗する。
「認証に失敗しました」などのエラーメッセージが表示される。

### 原因
1. ユーザー名またはパスワードの入力ミス
2. Caps Lock がオンになっている
3. アカウントがロックされている（連続ログイン失敗）

### 対処法

**オペレーター向け:**
1. Caps Lock がオフになっているか確認してください
2. ユーザー名とパスワードを正確に入力し直してください
3. パスワードの全角/半角に注意してください
4. 複数回失敗するとアカウントがロックされることがあります。しばらく時間をおいてから再試行してください

**管理者向け:**
```bash
# ユーザー一覧の確認（API経由）
curl -s http://localhost:3000/api/v1/auth/users \
  -H "Authorization: Bearer <管理者トークン>" | python3 -m json.tool

# バックエンドログでログイン失敗の原因を確認
docker compose -f docker-compose.prod.yml logs backend-blue | grep -i "auth\|login" | tail -20
```

### それでも解決しない場合
管理者に連絡して、アカウントの状態確認とパスワードリセットを依頼してください。

---

## Q3: AIチャットが応答しません

### 症状
AIチャットボタンをクリックしてメッセージを送信しても、応答がない。
「エラーが発生しました」や回転中のまま止まらない。

### 原因
1. LLM サーバー（LM Studio）が起動していない
2. LLM サーバーとの接続設定が正しくない
3. LLM サーバーのメモリ不足

### 対処法

**オペレーター向け:**
1. しばらく（30秒ほど）待ってから再度メッセージを送信してください
2. チャットドロワーを一度閉じて、再度開いてみてください
3. 改善しない場合は管理者に連絡してください。AIチャット以外の機能は通常通り使用できます

**管理者向け:**
```bash
# LM Studio の稼働確認
curl -s http://localhost:1234/v1/models | python3 -m json.tool

# Docker コンテナ内からの接続確認
docker exec bsf-backend-blue curl -s http://host.docker.internal:1234/v1/models

# 環境変数の LLM 設定を確認
grep LLM .env.production

# LM Studio を再起動してください（Mac mini のアプリケーション）
```

### それでも解決しない場合
LM Studio アプリケーションを再起動し、モデルが正しくロードされているか確認してください。
Mac mini のメモリ使用量が高い場合は、不要なアプリケーションを終了してください。

---

## Q4: 画面が真っ白になりました

### 症状
ログイン後、画面が真っ白になり何も表示されない。
または、特定のタブをクリックした後に白い画面になる。

### 原因
1. フロントエンドの JavaScript エラー
2. ブラウザのキャッシュの破損
3. フロントエンドのビルド不良

### 対処法

**オペレーター向け:**
1. ブラウザの再読み込みを行ってください（F5 キーまたは Ctrl+R）
2. ブラウザのキャッシュをクリアしてください
   - Chrome の場合: Ctrl+Shift+Delete → 「キャッシュされた画像とファイル」にチェック → 「データを削除」
3. 別のブラウザで試してください
4. ブラウザの開発者ツール（F12キー）のコンソールタブに赤いエラーメッセージが表示されている場合は、その内容をメモして管理者に連絡してください

**管理者向け:**
```bash
# フロントエンドの再ビルド
docker compose -f docker-compose.prod.yml build frontend-builder
docker compose -f docker-compose.prod.yml up -d frontend-builder router

# nginx の設定検証
docker exec bsf-router nginx -t

# 静的ファイルの存在確認
docker exec bsf-router ls /usr/share/nginx/html/index.html
```

### それでも解決しない場合
ブラウザのシークレットウィンドウ（プライベートブラウジング）で試してください。
それでも表示されない場合は、フロントエンドの完全再ビルドが必要です。

---

## Q5: CSV出力ができません

### 症状
CSV出力ボタンをクリックしても、ファイルがダウンロードされない。
またはダウンロードされたファイルが文字化けしている。

### 原因
1. ブラウザのダウンロード設定でブロックされている
2. 対象データが0件の場合
3. Excelでの文字コード認識の問題

### 対処法

**オペレーター向け:**
1. ブラウザのダウンロード設定を確認してください
   - ポップアップブロックが有効になっている場合は、本システムのURLを許可してください
2. ダウンロードフォルダを確認してください。ファイルが保存されている可能性があります
3. 対象データが存在するか確認してください（一覧にデータが表示されていますか）
4. **文字化けする場合**:
   - Excel でファイルを開く際に「データ」→「テキスト/CSV から」で取り込みます
   - 文字コードのプルダウンで **「UTF-8」** を選択します
   - macOS の場合は Numbers で開くと自動認識されます

### それでも解決しない場合
別のブラウザ（Chrome 推奨）でダウンロードを試してください。

---

## Q6: 配合推薦でエラーが出ます

### 症状
AI推薦ダイアログで「推薦を取得できませんでした」などのエラーが表示される。
推薦結果が0件で表示される。

### 原因
1. 対象の搬入記録に必要な情報が不足している
2. ML モデルが未学習の状態
3. マスタデータ（固化材・溶出抑制剤）が未登録

### 対処法

**オペレーター向け:**
1. 搬入記録のデータが正しく入力されているか確認してください
2. マスタ管理タブで、固化材と溶出抑制剤が登録されているか確認してください
3. 推薦結果が0件の場合でも、手動で配合を入力することは可能です
4. 改善しない場合は管理者に連絡してください

**管理者向け:**
```bash
# ML モデルの状態確認
curl -s http://localhost:3000/api/v1/ml/models | python3 -m json.tool

# モデルが未学習の場合は手動で学習を実行
curl -X POST http://localhost:3000/api/v1/ml/train

# バックエンドのエラーログを確認
docker compose -f docker-compose.prod.yml logs backend-blue | grep -i "error\|exception" | tail -20
```

### それでも解決しない場合
十分な学習データ（搬入記録と配合結果）が蓄積されるまでは、ML予測の精度が低い場合があります。
類似度ベースやルールベースの推薦を活用してください。

---

## Q7: データが表示されません（ローディングが終わらない）

### 症状
一覧画面やダッシュボードでデータ読み込み中の表示（スケルトンやスピナー）のまま、いつまでも表示されない。

### 原因
1. バックエンド API がタイムアウトしている
2. データベースの負荷が高い
3. ネットワーク接続の不安定

### 対処法

**オペレーター向け:**
1. ブラウザの再読み込み（F5キー）を試してください
2. 別のタブに切り替えてから、元のタブに戻してみてください
3. 数分待ってから再度アクセスしてみてください
4. 改善しない場合は管理者に連絡してください

**管理者向け:**
```bash
# バックエンドの稼働確認
curl -s http://localhost:3000/health | python3 -m json.tool

# データベース接続の確認
docker exec bsf-postgres pg_isready -U bsf_user -d bsf_system

# アクティブな DB 接続数の確認
docker exec bsf-postgres psql -U bsf_user -d bsf_system \
  -c "SELECT count(*) FROM pg_stat_activity WHERE datname='bsf_system';"

# バックエンドの再起動
docker compose -f docker-compose.prod.yml restart backend-blue
```

### それでも解決しない場合
PostgreSQL とバックエンドの両方を再起動してください。

```bash
docker compose -f docker-compose.prod.yml restart postgres
# 30秒待ってから
docker compose -f docker-compose.prod.yml restart backend-blue
```

---

## Q8: バッチ処理が動いていないようです

### 症状
ML モデルの再学習が行われていない。
KPI データが古いままになっている。

### 原因
1. バッチ処理が無効化されている（`BATCH_ENABLED=false`）
2. バックエンドコンテナが再起動された際にスケジューラが停止した
3. バッチジョブの実行中にエラーが発生している

### 対処法

**オペレーター向け:**
管理者に連絡して、バッチ処理の状態を確認してもらってください。

**管理者向け:**
```bash
# バッチジョブの状態確認
curl -s http://localhost:3000/api/v1/batch/status | python3 -m json.tool

# 各ジョブの実行状況
curl -s http://localhost:3000/api/v1/batch/jobs | python3 -m json.tool

# ジョブの手動実行（例: ML再学習）
curl -X POST http://localhost:3000/api/v1/batch/jobs/weekly_ml_retrain/trigger

# 環境変数の確認
grep BATCH .env.production
# BATCH_ENABLED=true になっているか確認

# バックエンドの再起動（スケジューラも再起動されます）
docker compose -f docker-compose.prod.yml restart backend-blue
```

### それでも解決しない場合
バックエンドのログで詳細なエラーメッセージを確認してください。

```bash
docker compose -f docker-compose.prod.yml logs backend-blue | grep -i "batch\|scheduler\|apscheduler" | tail -30
```

---

## Q9: ディスク容量が不足しています

### 症状
システムの動作が遅くなった。
バックアップや Docker の操作でエラーが発生する。

### 原因
1. Docker イメージやコンテナの蓄積
2. バックアップファイルの蓄積
3. ログファイルの肥大化

### 対処法

**オペレーター向け:**
管理者に連絡して、ディスク容量の確認と不要データの整理を依頼してください。

**管理者向け:**
```bash
# ディスク使用量の確認
df -h /

# Docker が使用しているディスク容量
docker system df

# 不要な Docker リソースの削除（停止中のコンテナ、未使用イメージ）
docker system prune -a

# バックアップファイルの確認（30日分保持が標準）
ls -lt ~/BSF_Backups/postgres/ | head -10
du -sh ~/BSF_Backups/postgres/

# 14日より古いバックアップを手動削除
find ~/BSF_Backups/postgres -name "*.sql.gz" -mtime +14 -delete

# ログファイルの確認
du -sh logs/
```

### それでも解決しない場合
外部ストレージへのバックアップ退避や、不要なデータの削除を検討してください。
データベースのサイズが大きい場合は VACUUM ANALYZE を実行してください。

```bash
docker exec bsf-postgres psql -U bsf_user -d bsf_system -c "VACUUM ANALYZE;"
```

---

## Q10: システムを再起動したい

### 症状
システム全体の動作が不安定なため、再起動したい。

### 原因
- 長時間の稼働によるリソース蓄積
- 設定変更後の反映
- 原因不明の不具合

### 対処法

**オペレーター向け:**
管理者に連絡して、システム再起動を依頼してください。
再起動中（約2〜3分）はシステムが利用できません。事前に他のオペレーターに告知してください。

**管理者向け:**

通常の再起動（データは保持されます）:
```bash
# 全サービスを停止
docker compose -f docker-compose.prod.yml down

# 全サービスを起動
docker compose -f docker-compose.prod.yml up -d

# 起動確認
docker compose -f docker-compose.prod.yml ps

# ヘルスチェック
curl -s http://localhost:3000/health | python3 -m json.tool
```

Blue-Green デプロイによる再起動（ダウンタイムなし）:
```bash
./scripts/deploy-blue-green.sh deploy
```

### それでも解決しない場合
完全に再構築が必要な場合は、以下を実行します（**データベースのバックアップを必ず確認してから**）。

```bash
# バックアップ実行
./scripts/backup_databases.sh

# 完全再構築
docker compose -f docker-compose.prod.yml down
./scripts/deploy-blue-green.sh init
```

---

## エスカレーションガイド

上記の対処法で解決しない場合は、以下の情報を添えて管理者またはシステム開発者に連絡してください。

1. **いつ** 発生したか（日時）
2. **どの画面** で発生したか（タブ名、操作内容）
3. **何をしたら** 発生したか（操作手順）
4. **エラーメッセージ** の内容（スクリーンショットがあれば添付）
5. **ブラウザ** の種類とバージョン（Chrome / Edge / Firefox など）

連絡先:
- システム管理者: （組織の連絡先を記入してください）
- 開発元: （開発元の連絡先を記入してください）
