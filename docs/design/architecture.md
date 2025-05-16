# System Architecture

The BSF Larvae Monitoring System is designed with a modular architecture to allow for scalability and flexibility.

## Overall Architecture

```mermaid
flowchart TD
    subgraph "データ収集層 (IoT Devices)"
        A[センサーデバイス群 (Wi-Fi)] -->|MQTT/TLS| B[EMQX Broker (オンプレミス)]
    end
    
    subgraph "処理層 (オンプレミス)"
        B -->|データ収集| C[Telegraf]
        C -->|処理| D[Python処理エンジン (FastAPI)]
        D -->|異常検知 & 制御指示| E[アラート & 制御マネージャ]
        E -->|制御信号| F[自動制御システム (温湿度調整)]
    end
    
    subgraph "ストレージ層 (オンプレミス)"
        D -->|保存| G[InfluxDB]
        G -->|分析| H[分析エンジン (Python)]
    end
    
    subgraph "連携層 (オンプレミス)"
        H <-->|データ連携 API| I[ERP連携モジュール]
        I <-->|在庫・生産データ| J[企業ERP]
        H -->|エクスポート| K[CSVエクスポート機能]
    end
    
    subgraph "可視化層 (オンプレミス)"
        G -->|データ可視化| L[Grafanaダッシュボード]
        L -->|閾値設定| D
    end
```

## Data Collection Layer

The data collection layer consists of Wi-Fi connected sensor devices that communicate with an EMQX MQTT broker. The sensors collect data such as temperature, humidity, pressure, and gas levels at 5-minute intervals.

## Processing Layer

The processing layer consists of a Telegraf instance for data collection, a Python processing engine built with FastAPI, and components for anomaly detection and control management.

## Storage Layer

The storage layer uses InfluxDB for time-series data storage and includes a Python analysis engine for processing the data.

## Integration Layer

The integration layer provides API endpoints for ERP integration and CSV export functionality.

## Visualization Layer

The visualization layer uses Grafana dashboards for real-time monitoring and setting threshold values.
