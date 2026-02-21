# VPS選定比較ガイド

BSF-LoopTech バックエンド用VPSの詳細比較

## 必要スペック要件

| コンポーネント | 最小要件 | 推奨要件 |
|---------------|---------|---------|
| CPU | 2 vCPU | 3-4 vCPU |
| RAM | 2GB | 4GB |
| ストレージ | 40GB SSD | 80GB NVMe |
| 帯域幅 | 1TB/月 | 無制限 |
| リージョン | 東京 | 東京 |

**稼働サービス**: FastAPI, PostgreSQL, InfluxDB, MQTT Broker (Mosquitto)

---

## 国内VPSプロバイダー比較

### ConoHa VPS

| プラン | vCPU | RAM | SSD | 月額 | 初期費用 |
|--------|------|-----|-----|------|----------|
| 1GB | 2 | 1GB | 100GB | ¥968 | ¥0 |
| **2GB** | **3** | **2GB** | **100GB** | **¥1,848** | **¥0** |
| 4GB | 4 | 4GB | 100GB | ¥3,608 | ¥0 |
| 8GB | 6 | 8GB | 100GB | ¥7,348 | ¥0 |

**メリット**:
- 時間課金対応（テスト時に便利）
- 管理画面が日本語で使いやすい
- APIが充実
- 自動バックアップオプション

**デメリット**:
- 帯域幅制限あり（転送量課金）

**推奨プラン**: 2GB (¥1,848/月)

---

### Xserver VPS

| プラン | vCPU | RAM | NVMe | 月額 | 初期費用 |
|--------|------|-----|------|------|----------|
| 2GB | 3 | 2GB | 50GB | ¥830〜 | ¥0 |
| **4GB** | **4** | **4GB** | **100GB** | **¥1,700〜** | **¥0** |
| 8GB | 6 | 8GB | 100GB | ¥3,201〜 | ¥0 |
| 16GB | 8 | 16GB | 100GB | ¥7,200〜 | ¥0 |

**メリット**:
- 高速NVMe SSD
- 転送量無制限
- 24時間サポート
- 最安クラスの価格

**デメリット**:
- 最低契約期間あり（3ヶ月〜）

**推奨プラン**: 4GB (¥1,700/月) - 転送量無制限が魅力

---

### さくらのVPS

| プラン | vCPU | RAM | SSD | 月額 | 初期費用 |
|--------|------|-----|-----|------|----------|
| 1GB | 2 | 1GB | 50GB | ¥880 | ¥0 |
| **2GB** | **3** | **2GB** | **100GB** | **¥1,738** | **¥0** |
| 4GB | 4 | 4GB | 200GB | ¥3,520 | ¥0 |
| 8GB | 6 | 8GB | 400GB | ¥7,040 | ¥0 |

**メリット**:
- 老舗の安定性
- 豊富なストレージ
- 2週間お試し無料

**デメリット**:
- 管理画面がやや古い

**推奨プラン**: 2GB (¥1,738/月)

---

## 海外VPSプロバイダー比較（東京リージョン）

### DigitalOcean

| プラン | vCPU | RAM | SSD | 月額 | 帯域幅 |
|--------|------|-----|-----|------|--------|
| Basic | 1 | 1GB | 25GB | $6 | 1TB |
| **Basic** | **2** | **2GB** | **50GB** | **$12** | **2TB** |
| Basic | 2 | 4GB | 80GB | $24 | 4TB |
| Basic | 4 | 8GB | 160GB | $48 | 5TB |

**メリット**:
- 豊富なドキュメント
- Terraform/Ansible対応
- マネージドデータベース連携
- グローバルなコミュニティ

**デメリット**:
- 日本語サポートなし
- 円建て決済不可

**推奨プラン**: 2GB ($12/月 ≈ ¥1,800)

---

### Vultr

| プラン | vCPU | RAM | SSD | 月額 | 帯域幅 |
|--------|------|-----|-----|------|--------|
| Cloud | 1 | 1GB | 25GB | $5 | 1TB |
| **Cloud** | **1** | **2GB** | **50GB** | **$10** | **2TB** |
| Cloud | 2 | 4GB | 80GB | $20 | 3TB |
| Cloud | 4 | 8GB | 160GB | $40 | 4TB |

**メリット**:
- 最安クラス
- 東京リージョン高速
- 時間課金対応
- スナップショット無料

**デメリット**:
- 1vCPU の2GBプランのみ（CPU弱め）

**推奨プラン**: 4GB ($20/月 ≈ ¥3,000) - CPUが重要なため

---

### Linode (Akamai)

| プラン | vCPU | RAM | SSD | 月額 | 帯域幅 |
|--------|------|-----|-----|------|--------|
| Nanode | 1 | 1GB | 25GB | $5 | 1TB |
| **Linode 2GB** | **1** | **2GB** | **50GB** | **$10** | **2TB** |
| Linode 4GB | 2 | 4GB | 80GB | $20 | 4TB |
| Linode 8GB | 4 | 8GB | 160GB | $40 | 5TB |

**メリット**:
- Akamai CDN連携
- 豊富なマネージドサービス
- 長い運用実績

**デメリット**:
- 東京リージョンの遅延がやや大きい場合あり

**推奨プラン**: 4GB ($20/月 ≈ ¥3,000)

---

## 総合比較表

| プロバイダー | 推奨プラン | 月額 | vCPU | RAM | 帯域幅 | 日本語 | 推奨度 |
|-------------|-----------|------|------|-----|--------|--------|--------|
| **Xserver VPS** | 4GB | ¥1,700 | 4 | 4GB | 無制限 | ✅ | ⭐⭐⭐⭐⭐ |
| **ConoHa VPS** | 2GB | ¥1,848 | 3 | 2GB | 制限あり | ✅ | ⭐⭐⭐⭐ |
| さくらのVPS | 2GB | ¥1,738 | 3 | 2GB | 無制限 | ✅ | ⭐⭐⭐⭐ |
| DigitalOcean | 2GB | $12 | 2 | 2GB | 2TB | ❌ | ⭐⭐⭐ |
| Vultr | 4GB | $20 | 2 | 4GB | 3TB | ❌ | ⭐⭐⭐ |

---

## 最終推奨

### 第1候補: Xserver VPS 4GBプラン

**月額: ¥1,700**

**理由**:
1. **転送量無制限** - IoTデータ転送に最適
2. **高性能NVMe** - データベース操作が高速
3. **4vCPU/4GB** - FastAPI + DB + MQTT を余裕で稼働
4. **日本語サポート** - トラブル時に安心
5. **コストパフォーマンス最高** - 同スペックで最安

### 第2候補: ConoHa VPS 2GBプラン

**月額: ¥1,848**

**理由**:
1. **時間課金** - テスト環境として柔軟
2. **API充実** - 自動化しやすい
3. **初期費用0円** - すぐに始められる

---

## セットアップ手順 (Xserver VPS)

### 1. 契約
```
1. https://vps.xserver.ne.jp/ にアクセス
2. 4GBプラン（3ヶ月以上）を選択
3. OS: Ubuntu 22.04 LTS を選択
4. リージョン: 東京
5. SSH鍵を登録
```

### 2. 初期設定
```bash
# SSH接続
ssh root@your-vps-ip

# システム更新
apt update && apt upgrade -y

# Docker インストール
curl -fsSL https://get.docker.com | sh
usermod -aG docker $USER

# Docker Compose インストール
apt install docker-compose-plugin -y

# ファイアウォール設定
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw allow 8000/tcp  # FastAPI
ufw allow 8883/tcp  # MQTT TLS
ufw enable
```

### 3. Let's Encrypt SSL
```bash
# Certbot インストール
apt install certbot -y

# 証明書取得
certbot certonly --standalone -d api.yourdomain.com

# 自動更新設定
systemctl enable certbot.timer
```

### 4. BSF LoopTech デプロイ
```bash
# リポジトリクローン
git clone https://github.com/your-repo/bsf-looptech.git
cd bsf-looptech

# 環境変数設定
cp .env.production.example .env.production
nano .env.production  # 編集

# Docker Compose 起動
docker-compose -f docker-compose.prod.yml up -d
```

---

## 月額コスト最終見積もり

| サービス | 費用 |
|----------|------|
| Xserver VPS 4GB | ¥1,700 |
| ドメイン (.com/年) | ¥100相当 |
| SSL (Let's Encrypt) | ¥0 |
| **合計** | **¥1,800/月** |

予算 ¥10,000/月 に対し、**¥1,800/月** で運用可能です。
