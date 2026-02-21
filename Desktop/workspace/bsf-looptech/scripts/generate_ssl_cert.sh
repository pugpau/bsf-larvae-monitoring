#!/bin/bash

# BSF-LoopTech 自己署名SSL証明書生成
# 閉域ネットワーク用（10年有効）
#
# Usage: ./scripts/generate_ssl_cert.sh [hostname]
# Example: ./scripts/generate_ssl_cert.sh bsf-looptech.local

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
CERT_DIR="${PROJECT_DIR}/config/ssl"
HOSTNAME="${1:-bsf-looptech.local}"

log_info() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] INFO: $1"
}

log_error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1" >&2
}

# ディレクトリ作成
mkdir -p "$CERT_DIR"

# 既存証明書の確認
if [ -f "$CERT_DIR/server.crt" ] && [ -f "$CERT_DIR/server.key" ]; then
    EXPIRY=$(openssl x509 -enddate -noout -in "$CERT_DIR/server.crt" 2>/dev/null | cut -d= -f2)
    log_info "既存の証明書があります（有効期限: $EXPIRY）"
    read -p "上書きしますか？ (y/N): " CONFIRM
    if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
        log_info "キャンセルしました"
        exit 0
    fi
fi

log_info "自己署名SSL証明書を生成します（ホスト名: $HOSTNAME）"

# 自己署名証明書生成（RSA 2048bit, 10年有効）
openssl req -x509 -nodes \
    -days 3650 \
    -newkey rsa:2048 \
    -keyout "$CERT_DIR/server.key" \
    -out "$CERT_DIR/server.crt" \
    -subj "/CN=$HOSTNAME/O=BSF-LoopTech/C=JP/ST=Ishikawa/L=Noto" \
    -addext "subjectAltName=DNS:$HOSTNAME,DNS:localhost,IP:127.0.0.1"

# 秘密鍵のパーミッション設定
chmod 600 "$CERT_DIR/server.key"
chmod 644 "$CERT_DIR/server.crt"

log_info "証明書を生成しました:"
log_info "  証明書: $CERT_DIR/server.crt"
log_info "  秘密鍵: $CERT_DIR/server.key"
log_info "  有効期限: 10年"
log_info "  ホスト名: $HOSTNAME"

# 証明書の内容を表示
openssl x509 -in "$CERT_DIR/server.crt" -noout -subject -dates
