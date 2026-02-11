# BSF-LoopTech 運用マニュアル

## 📋 目次

1. [システム概要](#システム概要)
2. [日常運用](#日常運用)  
3. [監視とアラート](#監視とアラート)
4. [バックアップ運用](#バックアップ運用)
5. [メンテナンス](#メンテナンス)
6. [トラブルシューティング](#トラブルシューティング)
7. [緊急時対応](#緊急時対応)
8. [定期作業](#定期作業)

---

## 🚀 システム概要

### アーキテクチャ

BSF-LoopTechは以下のコンポーネントで構成されています：

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   M5StickC      │───▶│   MQTT Broker   │───▶│   Backend API   │
│   センサー      │    │  (Mosquitto)    │    │   (FastAPI)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │                        │
                              ▼                        ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Web Frontend   │    │   PostgreSQL    │    │    InfluxDB     │
│   (React)       │    │ (メタデータ)    │    │ (時系列データ)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 主要エンドポイント

| サービス | URL | 用途 |
|----------|-----|------|
| Web UI | http://localhost:3000 | フロントエンド |
| Backend API | http://localhost:8000 | REST API |
| API文档 | http://localhost:8000/docs | Swagger UI |
| InfluxDB | http://localhost:8086 | 時系列データ管理 |
| MQTT (標準) | localhost:1883 | デバイス通信 |
| MQTT (TLS) | localhost:8883 | セキュア通信 |

---

## 📅 日常運用

### 毎朝のチェックリスト

```bash
# 1. システム状態確認
./scripts/status_production.sh

# 2. 夜間ログ確認
tail -50 logs/application.log | grep ERROR
tail -50 logs/system_alerts.log

# 3. データ流入確認
./scripts/system_monitor.sh network
```

### システム起動・停止

```bash
# システム全体の起動
./scripts/start_production.sh

# システム全体の停止  
./scripts/stop_production.sh

# システム再起動
./scripts/restart_production.sh

# 個別サービス制御
./scripts/service_control.sh start|stop|restart|status
```

### データ流入確認

```bash
# MQTT メッセージ監視
mosquitto_sub -h localhost -p 1883 -t "bsf/+/+/+/data" -C 10

# InfluxDBデータ確認
influx query 'from(bucket:"bsf_data") |> range(start:-1h) |> limit(n:10)'

# PostgreSQL接続確認  
psql -h localhost -U bsf_user -d bsf_system -c "SELECT COUNT(*) FROM sensor_devices;"
```

---

## 🔍 監視とアラート

### リアルタイム監視

```bash
# システム全体監視
./scripts/system_monitor.sh

# リソース監視
./scripts/system_monitor.sh resources

# プロセス監視  
./scripts/system_monitor.sh processes

# ネットワーク監視
./scripts/system_monitor.sh network
```

### アラート確認

```bash
# 今日のアラート
grep "$(date '+%Y-%m-%d')" logs/system_alerts.log

# エラーレベルのアラート
grep "ERROR\|CRITICAL" logs/system_alerts.log | tail -20

# アラート統計
./scripts/system_monitor.sh | grep "アラート数"
```

### パフォーマンス監視

```bash
# CPU・メモリ使用量
top -l 1 | grep -E "(CPU usage|PhysMem)"

# ディスク使用量
df -h | grep -E "(/$|/Users)"

# BSF関連プロセス
ps aux | grep -E "(uvicorn|mosquitto|influxdb|postgres)" | grep -v grep
```

### ログ監視

```bash
# リアルタイムログ監視
tail -f logs/application.log

# エラーログフィルタ
tail -f logs/application.log | grep -E "ERROR|WARN|CRITICAL"

# MQTT接続ログ
tail -f logs/application.log | grep -i mqtt

# データベース関連ログ
tail -f logs/application.log | grep -E "influx|postgres"
```

---

## 💾 バックアップ運用

### 自動バックアップ確認

```bash
# バックアップ統計確認
./scripts/backup_system.sh stats

# 最新バックアップ確認
ls -la backup/ | head -10

# バックアップ完全性チェック
./scripts/backup_system.sh verify
```

### 手動バックアップ

```bash
# 完全バックアップ（推奨：週1回）
./scripts/backup_system.sh full

# データベースのみ（推奨：日1回）
./scripts/backup_system.sh database

# 増分バックアップ（推奨：日複数回）
./scripts/backup_system.sh incremental
```

### バックアップからの復元

```bash
# 利用可能なバックアップ一覧
ls -la backup/*.tar.gz

# 特定バックアップからの復元
./scripts/backup_system.sh restore backup/20250905_143000_full_backup.tar.gz

# 復元後の確認
./scripts/status_production.sh
```

---

## 🔧 メンテナンス

### 定期メンテナンス

```bash
# 全項目メンテナンス（推奨：週1回）
./scripts/maintenance.sh

# データベース最適化
./scripts/maintenance.sh database

# ログローテーション
./scripts/maintenance.sh logs

# システムヘルスチェック
./scripts/maintenance.sh health
```

### ログ管理

```bash
# ログローテーション実行
./scripts/rotate_logs.sh

# 古いログ削除
./scripts/maintenance.sh cleanup

# ログ圧縮
gzip logs/*.log.1

# ログサイズ確認
du -sh logs/
```

### データベース管理

```bash
# PostgreSQL メンテナンス
psql -h localhost -U bsf_user -d bsf_system -c "VACUUM ANALYZE;"

# InfluxDB データ保持ポリシー確認
influx bucket list --org bsf_org

# データベース統計
./scripts/maintenance.sh stats
```

---

## ⚠️ トラブルシューティング

### よくある問題と解決策

#### 1. APIサーバーが応答しない

```bash
# プロセス確認
ps aux | grep uvicorn

# ポート確認
lsof -i :8000

# ログ確認
tail -50 logs/application.log

# 解決策
./scripts/restart_production.sh
```

#### 2. MQTT接続エラー

```bash
# Mosquitto状態確認
brew services list | grep mosquitto

# MQTT接続テスト
mosquitto_pub -h localhost -p 1883 -t test -m "hello"

# TLS接続テスト
mosquitto_pub -h localhost -p 8883 --cafile certs/ca.crt -t test -m "hello"

# 解決策
brew services restart mosquitto
```

#### 3. データベース接続エラー

```bash
# PostgreSQL確認
brew services list | grep postgresql
psql -h localhost -U bsf_user -d bsf_system -c "SELECT 1;"

# InfluxDB確認
influx ping --host http://localhost:8086

# 解決策
brew services restart postgresql
brew services restart influxdb
```

#### 4. フロントエンド接続エラー

```bash
# React開発サーバー確認
lsof -i :3000

# ビルド状態確認
cd frontend && npm run build

# 解決策
cd frontend && npm start
```

#### 5. ディスク容量不足

```bash
# ディスク使用量確認
df -h

# 大きなファイル検索
find . -type f -size +100M

# 解決策
./scripts/backup_system.sh cleanup
./scripts/rotate_logs.sh
```

### ログ解析コマンド

```bash
# エラー統計
grep -c ERROR logs/application.log

# 時間別エラー分析
grep ERROR logs/application.log | cut -d' ' -f1-2 | sort | uniq -c

# MQTT接続統計
grep "MQTT" logs/application.log | grep -c "Connected\|Disconnected"

# データベース接続統計  
grep -E "(InfluxDB|PostgreSQL)" logs/application.log | grep -c "connected\|disconnected"
```

### システム修復

```bash
# 設定ファイル修復
git checkout certs/mosquitto.conf
git checkout .env.production

# 権限修復
chmod +x scripts/*.sh

# データベース修復
./scripts/maintenance.sh repair

# 完全リセット（最後の手段）
./scripts/stop_production.sh
rm -rf temp/*.pid
./scripts/start_production.sh
```

---

## 🚨 緊急時対応

### システム全停止

```bash
# 緊急停止
./scripts/stop_production.sh

# 強制プロセス終了
pkill -f "uvicorn.*main:app"
pkill -f "python.*ml_pipeline"
pkill mosquitto
```

### データ復旧手順

1. **システム停止**
```bash
./scripts/stop_production.sh
```

2. **最新バックアップ確認**
```bash
ls -lt backup/*.tar.gz | head -5
```

3. **データ復旧実行**
```bash
latest_backup=$(ls -t backup/*.tar.gz | head -1)
./scripts/backup_system.sh restore "$latest_backup"
```

4. **システム再起動**
```bash
./scripts/start_production.sh
```

5. **データ整合性確認**
```bash
./scripts/status_production.sh
./scripts/system_monitor.sh
```

### ネットワーク障害対応

```bash
# DNS確認
nslookup google.com

# ネットワーク設定確認
ifconfig en0

# MQTT外部接続確認
telnet localhost 1883

# 解決後の確認
./scripts/system_monitor.sh network
```

### セキュリティインシデント対応

1. **システム隔離**
```bash
./scripts/stop_production.sh
# ネットワーク接続を一時停止
```

2. **ログ保全**
```bash
cp -r logs/ logs_incident_$(date +%Y%m%d_%H%M%S)
```

3. **証明書更新**
```bash
python scripts/generate_mqtt_certs.py
./scripts/restart_production.sh
```

---

## 📅 定期作業

### 日次作業

- [ ] システム状態確認
- [ ] エラーログチェック
- [ ] データ流入確認
- [ ] バックアップ実行確認
- [ ] ディスク容量確認

### 週次作業

- [ ] 完全バックアップ実行
- [ ] ログローテーション
- [ ] システムメンテナンス
- [ ] パフォーマンス監視レポート
- [ ] セキュリティアップデート確認

### 月次作業

- [ ] データベース最適化
- [ ] 古いバックアップ削除
- [ ] システム統計レポート
- [ ] 証明書有効期限確認
- [ ] ハードウェア状態確認

### 年次作業

- [ ] TLS証明書更新
- [ ] パスワード変更
- [ ] 災害復旧テスト
- [ ] システム性能評価
- [ ] セキュリティ監査

---

## 📊 運用指標

### パフォーマンス指標

| 指標 | 目標値 | 警告値 | 危険値 |
|------|--------|--------|--------|
| CPU使用率 | <10% | >70% | >90% |
| メモリ使用率 | <60% | >80% | >95% |
| ディスク使用率 | <75% | >85% | >95% |
| API応答時間 | <200ms | >1s | >5s |
| MQTT接続数 | - | <預期の50% | <預期の10% |

### 可用性指標

| 項目 | 目標 | 測定方法 |
|------|------|----------|
| システム稼働率 | 99.5% | uptime監視 |
| データ損失率 | 0% | バックアップ検証 |
| 復旧時間 | <30分 | インシデント記録 |

### データ品質指標

```bash
# データ完全性チェック
./scripts/data_quality_check.sh

# センサーデータ統計
influx query 'from(bucket:"bsf_data") |> range(start:-24h) |> count()'

# 異常値検出
grep "anomaly" logs/application.log | tail -20
```

---

## 📞 連絡先・エスカレーション

### システム管理者
- **メール**: admin@bsf-looptech.com
- **緊急時**: [緊急連絡先]

### ベンダー連絡先
- **M5Stack**: [サポート連絡先]
- **InfluxDB**: [サポート連絡先]
- **PostgreSQL**: [コミュニティフォーラム]

---

## 📚 参考文献

- [BSF-LoopTech アーキテクチャ文書](ARCHITECTURE.md)
- [M5StickC セットアップガイド](M5STICK_SETUP_GUIDE.md)
- [本番環境セットアップガイド](PRODUCTION_SETUP.md)
- [API文書](http://localhost:8000/docs)

---

**⚠️ 重要事項**

1. **データバックアップ**: 日次バックアップは必須
2. **セキュリティ**: デフォルトパスワードは使用禁止
3. **監視**: システムアラートは24時間監視
4. **更新**: セキュリティパッチは迅速適用
5. **記録**: 全ての作業はログに記録

**📝 このマニュアルは定期的に更新し、最新の運用状況を反映してください。**