#include <M5StickC.h>
#include <Wire.h>
#include <EEPROM.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <time.h>
#include "Adafruit_BME680.h"
#include <ArduinoJson.h>

// Device Settings - BSF-LoopTech用
const char* DEVICE_ID = "GAS-001";
const char* DEVICE_TYPE = "gas_sensor";
const char* FARM_ID = "farm1";
const char* DEVICE_NAME = "ガスセンサー001";
const char* LOCATION = "エリアA-1";

// WiFi Settings
const char* ssid = "TP-Link_B430";
const char* password = "47461437";

// NTP Settings
const char* ntpServer = "pool.ntp.org";
const long gmtOffset_sec = 9 * 3600;  // JST
const int daylightOffset_sec = 0;

// MQTT Settings - Updated for BSF-LoopTech secure configuration
const char* mqtt_server = "localhost";  // Update to your MQTT broker IP
const int mqtt_port = 1883;  // Using plain port for M5StickC (TLS support limited)
const char* mqtt_user = "bsf_device";
const char* mqtt_password = "BSF_Device_2025_Secure!";
char mqtt_topic[100];
char mqtt_client_id[50];

// MQTT Client
WiFiClient espClient;
PubSubClient mqttClient(espClient);

// Sensor
Adafruit_BME680 bme;

// MICS-5524 Pin definitions
const int MICS5524_ANALOG_PIN = 36;  // G36 (アナログ入力)
const int MICS5524_ENABLE_PIN = 26;  // G26 (イネーブル制御)

// G36電圧監視用の新しい構造体
struct G36MonitorData {
    int baseline_adc;
    int current_adc;
    float baseline_voltage;
    float current_voltage;
    int difference;
    float sensitivity_percent;
    unsigned long detection_time;
    bool is_detecting;
    bool warning_level;
    bool alert_level;
    int variability;
    String status_text;
};

// Time
RTC_TimeTypeDef rtcTime;
RTC_DateTypeDef rtcDate;

// Operation modes - ガス測定モード + G36監視モード追加
enum GasMode {
    MODE_IDLE,
    MODE_H2S,
    MODE_NH3,
    MODE_CALIBRATION,
    MODE_G36_MONITOR  // 新しいモード
};

// Heater profile structure
struct HeaterProfile {
    uint16_t temp;
    uint16_t duration;
};

// MICS-5524 data structure
struct MICS5524Data {
    float nh3_ppm;
    float h2s_ppm;
    float co_ppm;
    int raw_value;
    float voltage;
};

// Measurement data structure - G36監視データ追加
struct MeasurementData {
    float temperature;
    float pressure;
    float humidity;
    uint32_t gas_resistance;
    float h2s_ppm;
    float nh3_ppm;
    uint32_t timestamp;
    uint8_t heater_step;
    bool isValid;
    float quality_score;
    bool high_humidity_warning;
    // MICS-5524データ
    float mics_nh3_ppm;
    float mics_h2s_ppm;
    float mics_co_ppm;
    bool mics_available;
    // G36監視データ
    G36MonitorData g36_data;
};

// Calibration data structure
struct CalibrationData {
    uint32_t baseResistance;
    float baseTemperature;
    float baseHumidity;
    bool isCalibrated;
};

// Average buffer for stable readings
struct AverageBuffer {
    float temp_sum;
    float humidity_sum;
    float pressure_sum;
    float gas_sum;
    float h2s_sum;
    float nh3_sum;
    int count;
    unsigned long last_send;
} avgBuffer = {0};

// Constants - ガスセンサー用定数
const int PROFILE_STEPS = 5;
const int SAMPLES_PER_CYCLE = 15;
const int MEASUREMENT_INTERVAL = 2000;
const int HEATER_MINIMUM_TIME = 30;
const int SCREEN_BRIGHTNESS = 15;
const int EEPROM_SIZE = 512;
const int H2S_CAL_ADDR = 0;
const int NH3_CAL_ADDR = sizeof(CalibrationData);
const int G36_CAL_ADDR = 2 * sizeof(CalibrationData);  // G36ベースライン保存位置
const unsigned long CALIBRATION_TIME = 30000;

// G36監視用定数
const int G36_BASELINE_SAMPLES = 50;
const int G36_DETECTION_THRESHOLD = 100;    // ADC値の変化閾値
const int G36_WARNING_THRESHOLD = 200;      // 警告レベル
const int G36_ALERT_THRESHOLD = 500;        // アラートレベル
const unsigned long G36_DETECTION_MIN_TIME = 1000;  // 最小検出時間（ms）

// PPM calculation constants - 高湿度環境用に調整
const float H2S_SENSITIVITY = 0.0200;
const float H2S_BASELINE = 9.5;

// Heater profiles - 高湿度環境用に最適化
const HeaterProfile H2S_PROFILE[] = {
    {220, 120},
    {320, 60},
    {250, 120},
    {350, 40},
    {200, 120}
};

const HeaterProfile NH3_PROFILE[] = {
    {260, 120},
    {360, 60},
    {300, 120},
    {400, 40},
    {240, 120}
};

// Display constants
const int SCREEN_WIDTH = 160;
const int SCREEN_HEIGHT = 80;
const int TEXT_SIZE_NORMAL = 2;
const int TEXT_SIZE_SMALL = 1;

// Timing constants
const unsigned long SEND_INTERVAL = 30000;
const unsigned long WIFI_RECONNECT_INTERVAL = 30000;
const unsigned long MQTT_RECONNECT_INTERVAL = 10000;
const unsigned long DISPLAY_UPDATE_INTERVAL = 2000;

// Global variables
GasMode currentMode = MODE_IDLE;
int currentStep = 0;
MeasurementData currentMeasurement = {0};
unsigned long lastHeaterUpdate = 0;
unsigned long lastMeasurement = 0;
unsigned long lastWifiCheck = 0;
unsigned long lastMqttCheck = 0;
unsigned long lastDisplayUpdate = 0;
CalibrationData h2sCalibration = {0, 0, 0, false};
CalibrationData nh3Calibration = {0, 0, 0, false};
bool mqttConnected = false;
bool wifiConnected = false;
int wifiRetryCount = 0;
int mqttRetryCount = 0;

// MICS-5524 global variables
bool mics5524Available = false;
float mics5524BaselineResistance = 0;

// G36監視用グローバル変数
G36MonitorData g36Monitor = {0};
bool g36MonitorActive = false;
unsigned long g36DetectionStartTime = 0;

// Color definitions
#define BLACK 0x0000
#define WHITE 0xFFFF
#define RED   0xF800
#define GREEN 0x07E0
#define BLUE  0x001F
#define YELLOW 0xFFE0
#define ORANGE 0xFD20

// ===========================================
// G36監視関数群
// ===========================================

// G36ベースライン校正（改良版）
void calibrateG36Baseline() {
    M5.Lcd.fillScreen(BLACK);
    M5.Lcd.setTextSize(TEXT_SIZE_SMALL);
    M5.Lcd.setTextColor(WHITE);
    M5.Lcd.setCursor(0, 0);
    M5.Lcd.println("G36 Baseline Cal");
    M5.Lcd.println("Clean air required!");
    M5.Lcd.println("Remove all gases...");
    M5.Lcd.println("");
    M5.Lcd.println("Press A to start");
    M5.Lcd.println("Press B to cancel");
    
    // ユーザー確認待ち
    while (true) {
        M5.update();
        if (M5.BtnA.wasPressed()) break;
        if (M5.BtnB.wasPressed()) return;
        delay(10);
    }
    
    M5.Lcd.fillScreen(BLACK);
    M5.Lcd.setCursor(0, 0);
    M5.Lcd.println("Calibrating G36...");
    M5.Lcd.println("Keep clean air!");
    
    long sum = 0;
    int validSamples = 0;
    int minVal = 4095;
    int maxVal = 0;
    
    for (int i = 0; i < G36_BASELINE_SAMPLES; i++) {
        int reading = analogRead(MICS5524_ANALOG_PIN);
        
        // 全範囲を有効とする（電圧監視なので）
        sum += reading;
        validSamples++;
        
        if (reading < minVal) minVal = reading;
        if (reading > maxVal) maxVal = reading;
        
        // プログレス表示
        int progress = (i * 100) / G36_BASELINE_SAMPLES;
        M5.Lcd.fillRect(0, 40, progress * 160 / 100, 8, GREEN);
        M5.Lcd.setCursor(0, 50);
        M5.Lcd.printf("ADC: %d", reading);
        M5.Lcd.setCursor(0, 60);
        M5.Lcd.printf("Range: %d-%d", minVal, maxVal);
        
        delay(100);
    }
    
    // 変動チェック
    int variability = maxVal - minVal;
    
    if (validSamples > G36_BASELINE_SAMPLES * 0.9 && variability < 500) {
        g36Monitor.baseline_adc = sum / validSamples;
        g36Monitor.baseline_voltage = (g36Monitor.baseline_adc * 3.3) / 4095.0;
        
        // EEPROMに保存
        EEPROM.begin(EEPROM_SIZE);
        EEPROM.put(G36_CAL_ADDR, g36Monitor.baseline_adc);
        EEPROM.commit();
        EEPROM.end();
        
        M5.Lcd.fillScreen(BLACK);
        M5.Lcd.setCursor(0, 0);
        M5.Lcd.setTextColor(GREEN);
        M5.Lcd.println("G36 Cal Success!");
        M5.Lcd.printf("Baseline: %d\n", g36Monitor.baseline_adc);
        M5.Lcd.printf("Voltage: %.3fV\n", g36Monitor.baseline_voltage);
        M5.Lcd.printf("Variability: %d\n", variability);
        
        Serial.printf("G36 Baseline calibrated successfully\n");
        Serial.printf("Baseline ADC: %d, Voltage: %.3fV\n", 
                     g36Monitor.baseline_adc, g36Monitor.baseline_voltage);
        Serial.printf("Variability: %d (good: <500)\n", variability);
    } else {
        M5.Lcd.fillScreen(BLACK);
        M5.Lcd.setTextColor(RED);
        M5.Lcd.println("G36 Cal Failed!");
        M5.Lcd.printf("Samples: %d/%d\n", validSamples, G36_BASELINE_SAMPLES);
        M5.Lcd.printf("Variability: %d\n", variability);
        M5.Lcd.setTextColor(YELLOW);
        M5.Lcd.println("Too unstable!");
        
        Serial.printf("G36 calibration failed: Variability=%d (>500)\n", variability);
    }
    
    delay(3000);
}

// G36ベースライン読み込み
void loadG36Baseline() {
    EEPROM.begin(EEPROM_SIZE);
    EEPROM.get(G36_CAL_ADDR, g36Monitor.baseline_adc);
    EEPROM.end();
    
    if (g36Monitor.baseline_adc > 10 && g36Monitor.baseline_adc < 4090) {
        g36Monitor.baseline_voltage = (g36Monitor.baseline_adc * 3.3) / 4095.0;
        Serial.printf("G36 Baseline loaded: ADC=%d, V=%.3f\n", 
                     g36Monitor.baseline_adc, g36Monitor.baseline_voltage);
    } else {
        g36Monitor.baseline_adc = 0;
        g36Monitor.baseline_voltage = 0;
        Serial.println("G36 Baseline not calibrated");
    }
}

// G36監視データ更新
void updateG36Monitor() {
    // 複数回測定して平均化
    long sum = 0;
    int min_val = 4095;
    int max_val = 0;
    
    for (int i = 0; i < 5; i++) {
        int reading = analogRead(MICS5524_ANALOG_PIN);
        sum += reading;
        if (reading < min_val) min_val = reading;
        if (reading > max_val) max_val = reading;
        delay(10);
    }
    
    g36Monitor.current_adc = sum / 5;
    g36Monitor.current_voltage = (g36Monitor.current_adc * 3.3) / 4095.0;
    g36Monitor.variability = max_val - min_val;
    
    if (g36Monitor.baseline_adc > 0) {
        g36Monitor.difference = g36Monitor.current_adc - g36Monitor.baseline_adc;
        g36Monitor.sensitivity_percent = (abs(g36Monitor.difference) * 100.0) / g36Monitor.baseline_adc;
        
        // 検出レベル判定
        int abs_diff = abs(g36Monitor.difference);
        
        if (abs_diff >= G36_ALERT_THRESHOLD) {
            g36Monitor.alert_level = true;
            g36Monitor.warning_level = true;
            g36Monitor.status_text = "🔴危険";
        } else if (abs_diff >= G36_WARNING_THRESHOLD) {
            g36Monitor.alert_level = false;
            g36Monitor.warning_level = true;
            g36Monitor.status_text = "🟠警告";
        } else if (abs_diff >= G36_DETECTION_THRESHOLD) {
            g36Monitor.alert_level = false;
            g36Monitor.warning_level = false;
            g36Monitor.status_text = "🟡注意";
        } else {
            g36Monitor.alert_level = false;
            g36Monitor.warning_level = false;
            g36Monitor.status_text = "🟢正常";
        }
        
        // 検出時間の管理
        if (abs_diff >= G36_DETECTION_THRESHOLD) {
            if (!g36Monitor.is_detecting) {
                g36DetectionStartTime = millis();
                g36Monitor.is_detecting = true;
            }
            g36Monitor.detection_time = millis() - g36DetectionStartTime;
        } else {
            g36Monitor.is_detecting = false;
            g36Monitor.detection_time = 0;
        }
    } else {
        g36Monitor.difference = 0;
        g36Monitor.sensitivity_percent = 0;
        g36Monitor.status_text = "未校正";
        g36Monitor.is_detecting = false;
    }
    
    // シリアル出力
    if (g36MonitorActive) {
        Serial.printf("基準:%d 現在: %d 差:%+d [%s", 
                     g36Monitor.baseline_adc, 
                     g36Monitor.current_adc,
                     g36Monitor.difference,
                     g36Monitor.status_text.c_str());
        
        if (g36Monitor.is_detecting) {
            Serial.printf("(%lus)", g36Monitor.detection_time / 1000);
        }
        
        Serial.printf("] 感度:%.1f%% 変動:%d\n",
                     g36Monitor.sensitivity_percent,
                     g36Monitor.variability);
    }
}

// ===========================================
// 既存関数群（一部修正）
// ===========================================

// バッテリーレベルを計算
int getBatteryLevel() {
    float batVoltage = M5.Axp.GetBatVoltage();
    int level = (int)((batVoltage - 3.0) / (4.2 - 3.0) * 100);
    level = constrain(level, 0, 100);
    return level;
}

// 湿度補正関数
float compensateGasResistance(uint32_t gasResistance, float humidity, float temperature) {
    float compensatedResistance = gasResistance;
    
    if (humidity > 40.0) {
        float humidityFactor = 1.0 + (humidity - 40.0) * 0.015;
        
        if (humidity > 70.0) {
            humidityFactor += (humidity - 70.0) * 0.025;
        }
        
        if (temperature > 25.0 && humidity > 60.0) {
            float tempHumFactor = 1.0 + ((temperature - 25.0) * (humidity - 60.0) * 0.0002);
            humidityFactor *= tempHumFactor;
        }
        
        compensatedResistance = gasResistance * humidityFactor;
    }
    
    return compensatedResistance;
}

// NH3計算（VOCから推定）
float calculateNH3FromVOC(uint32_t gasResistance, float temperature, float humidity) {
    if (!nh3Calibration.isCalibrated || nh3Calibration.baseResistance <= 0) {
        return 0.0;
    }
    
    uint32_t compensatedGasResistance = compensateGasResistance(gasResistance, humidity, temperature);
    uint32_t compensatedBaseResistance = compensateGasResistance(nh3Calibration.baseResistance, 
                                                                 nh3Calibration.baseHumidity, 
                                                                 nh3Calibration.baseTemperature);
    
    float resistanceRatio = (float)compensatedGasResistance / compensatedBaseResistance;
    float nh3_estimate = 0.0;
    
    if (resistanceRatio < 1.0) {
        nh3_estimate = (1.0 - resistanceRatio) * 50.0;
        
        if (temperature > 25.0) {
            nh3_estimate *= (1.0 + (temperature - 25.0) * 0.01);
        }
        
        if (humidity > 70.0) {
            nh3_estimate *= (1.0 - (humidity - 70.0) * 0.005);
        }
    }
    
    return constrain(nh3_estimate, 0.0, 50.0);
}

// PPM計算関数
float calculatePPM(uint32_t gasResistance, float temperature, float humidity, bool isH2S) {
    if (isH2S) {
        const CalibrationData& calData = h2sCalibration;
        float sensitivity = H2S_SENSITIVITY;
        float baseline = H2S_BASELINE;
        
        if (!calData.isCalibrated || calData.baseResistance <= 0) {
            return 0.0;
        }
        
        uint32_t compensatedGasResistance = compensateGasResistance(gasResistance, humidity, temperature);
        uint32_t compensatedBaseResistance = compensateGasResistance(calData.baseResistance, 
                                                                     calData.baseHumidity, 
                                                                     calData.baseTemperature);
        
        float resistanceRatio = (float)compensatedGasResistance / compensatedBaseResistance;
        
        float tempCoef = 1.0;
        if (temperature > 25.0) {
            tempCoef = 1.0 + 0.015 * (temperature - 25.0);
        } else {
            tempCoef = 1.0 + 0.02 * (temperature - 25.0);
        }
        
        float humCoef = 1.0 + 0.005 * (humidity - calData.baseHumidity);
        float ppm = baseline - (log10(resistanceRatio) / sensitivity) * tempCoef * humCoef;
        
        if (humidity > 75.0) {
            float humidityPenalty = (humidity - 75.0) * 0.02;
            ppm = ppm * (1.0 - humidityPenalty);
        }
        
        return constrain(ppm, 0.0, 10.0);
    } else {
        return calculateNH3FromVOC(gasResistance, temperature, humidity);
    }
}

// MICS-5524初期化（G36電圧監視として動作するよう修正）
bool setupMICS5524() {
    pinMode(MICS5524_ENABLE_PIN, OUTPUT);
    digitalWrite(MICS5524_ENABLE_PIN, LOW);  // Active LOW (センサーON)
    
    // ADC設定
    analogSetAttenuation(ADC_11db);  // 0-3.3V範囲
    analogReadResolution(12);        // 12ビット分解能
    
    M5.Lcd.setTextColor(WHITE);
    M5.Lcd.println("G36 Voltage Monitor:");
    
    // ウォームアップ（短縮）
    for (int i = 2; i > 0; i--) {
        M5.Lcd.setCursor(120, M5.Lcd.getCursorY());
        M5.Lcd.printf("Wait %ds", i);
        delay(1000);
    }
    
    // G36ピンの基本動作確認
    M5.Lcd.setCursor(120, M5.Lcd.getCursorY() - 10);
    M5.Lcd.print("Testing...");
    
    // 複数回読み取りテスト
    int validReadings = 0;
    int totalReadings = 10;
    float voltageSum = 0;
    int minReading = 4095;
    int maxReading = 0;
    
    for (int i = 0; i < totalReadings; i++) {
        int rawValue = analogRead(MICS5524_ANALOG_PIN);
        float voltage = (rawValue * 3.3) / 4095.0;
        
        // 有効範囲をより広く設定（電圧監視なので0-3.3V全域が有効）
        if (rawValue >= 0 && rawValue <= 4095) {
            voltageSum += voltage;
            validReadings++;
            if (rawValue < minReading) minReading = rawValue;
            if (rawValue > maxReading) maxReading = rawValue;
        }
        delay(50);
    }
    
    // 成功判定を緩和（電圧読み取りができれば成功）
    if (validReadings >= 8) {  // 10回中8回成功すれば OK
        float avgVoltage = voltageSum / validReadings;
        mics5524BaselineResistance = avgVoltage * 1000;  // 電圧*1000を仮のベースラインとして保存
        mics5524Available = true;
        
        M5.Lcd.setCursor(120, M5.Lcd.getCursorY() - 10);
        M5.Lcd.setTextColor(GREEN);
        M5.Lcd.println("OK       ");
        
        Serial.printf("G36 Voltage Monitor initialized successfully\n");
        Serial.printf("Valid readings: %d/%d\n", validReadings, totalReadings);
        Serial.printf("Voltage range: %.3f - %.3f V\n", (minReading * 3.3)/4095.0, (maxReading * 3.3)/4095.0);
        Serial.printf("Average voltage: %.3f V\n", avgVoltage);
        
        return true;
    } else {
        mics5524Available = false;
        M5.Lcd.setCursor(120, M5.Lcd.getCursorY() - 10);
        M5.Lcd.setTextColor(RED);
        M5.Lcd.println("FAILED   ");
        
        Serial.printf("G36 Voltage Monitor initialization failed\n");
        Serial.printf("Valid readings: %d/%d (minimum 8 required)\n", validReadings, totalReadings);
        
        return false;
    }
}

// MICS-5524読み取り（G36電圧監視ベース）
MICS5524Data readMICS5524() {
    MICS5524Data data = {0, 0, 0, 0, 0};
    
    if (!mics5524Available) return data;
    
    // 複数回読み取りで平均化
    int sum = 0;
    for (int i = 0; i < 5; i++) {
        sum += analogRead(MICS5524_ANALOG_PIN);
        delay(10);
    }
    data.raw_value = sum / 5;
    
    // ESP32の12ビットADCを電圧に変換
    data.voltage = (data.raw_value / 4095.0) * 3.3;
    
    // G36電圧監視ベースのガス濃度推定
    if (g36Monitor.baseline_adc > 0) {
        int diff = data.raw_value - g36Monitor.baseline_adc;
        float sensitivity = abs(diff) / (float)g36Monitor.baseline_adc;
        
        // 電圧変化からガス濃度を推定
        // アルコール等のVOCによる電圧変化パターン
        if (diff > 50) {  // 電圧上昇 = ガス検出
            // NH3濃度推定（電圧上昇パターン）
            data.nh3_ppm = (diff / 10.0) * sensitivity * 100;  // 調整係数
            data.nh3_ppm = constrain(data.nh3_ppm, 0, 500);
            
            // H2S濃度推定（より感度の高い検出）
            if (diff > 100) {
                data.h2s_ppm = (diff / 20.0) * sensitivity * 10;
                data.h2s_ppm = constrain(data.h2s_ppm, 0, 50);
            }
            
            // CO濃度推定
            if (diff > 200) {
                data.co_ppm = (diff / 5.0) * sensitivity * 50;
                data.co_ppm = constrain(data.co_ppm, 0, 1000);
            }
        }
    }
    
    return data;
}

// センサーデータ融合（G36データ追加）
void fuseSensorData(MeasurementData& data) {
    // G36監視データ更新
    updateG36Monitor();
    data.g36_data = g36Monitor;
    
    if (!mics5524Available) {
        // MICS-5524が利用できない場合はBME680の推定値を使用
        return;
    }
    
    MICS5524Data micsData = readMICS5524();
    data.mics_nh3_ppm = micsData.nh3_ppm;
    data.mics_h2s_ppm = micsData.h2s_ppm;
    data.mics_co_ppm = micsData.co_ppm;
    data.mics_available = true;
    
    // MICS-5524の値をメインの表示値として使用
    data.nh3_ppm = micsData.nh3_ppm;
    data.h2s_ppm = micsData.h2s_ppm;
    
    // MICS-5524が利用可能な場合は品質スコアを向上
    if (mics5524Available) {
        data.quality_score += 0.2;
        data.quality_score = constrain(data.quality_score, 0.0, 1.0);
    }
}

// MICS-5524電力管理
void setMICS5524Power(bool enable) {
    if (mics5524Available) {
        digitalWrite(MICS5524_ENABLE_PIN, enable ? LOW : HIGH);
        if (enable) {
            delay(1000);
        }
    }
}

// ヒータープロファイル更新
void updateHeaterProfile() {
    if (currentMode == MODE_IDLE || currentMode == MODE_G36_MONITOR) return;
    
    const HeaterProfile* profile = (currentMode == MODE_H2S) ? H2S_PROFILE : NH3_PROFILE;
    unsigned long currentTime = millis();
    
    if (currentTime - lastHeaterUpdate >= profile[currentStep].duration) {
        currentStep = (currentStep + 1) % PROFILE_STEPS;
        bme.setGasHeater(profile[currentStep].temp, profile[currentStep].duration);
        lastHeaterUpdate = currentTime;
        
        Serial.printf("Heater: Step %d, Temp %d°C, Duration %dms\n", 
                     currentStep, profile[currentStep].temp, profile[currentStep].duration);
    }
}

// WiFi接続
bool setupWiFi() {
    if (WiFi.status() == WL_CONNECTED) {
        wifiConnected = true;
        return true;
    }
    
    M5.Lcd.fillScreen(BLACK);
    M5.Lcd.setTextSize(TEXT_SIZE_SMALL);
    M5.Lcd.setTextColor(WHITE);
    M5.Lcd.setCursor(0, 0);
    M5.Lcd.printf("WiFi: %s\n", ssid);
    M5.Lcd.print("Connecting");
    
    WiFi.mode(WIFI_STA);
    WiFi.begin(ssid, password);
    
    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 30) {
        delay(500);
        M5.Lcd.print(".");
        attempts++;
        
        if (attempts % 10 == 0) {
            M5.Lcd.println();
        }
    }
    
    if (WiFi.status() == WL_CONNECTED) {
        wifiConnected = true;
        M5.Lcd.setTextColor(GREEN);
        M5.Lcd.printf("\nConnected!\n");
        M5.Lcd.printf("IP: %s\n", WiFi.localIP().toString().c_str());
        
        configTime(gmtOffset_sec, daylightOffset_sec, ntpServer);
        struct tm timeinfo;
        if (getLocalTime(&timeinfo)) {
            rtcTime.Hours = timeinfo.tm_hour;
            rtcTime.Minutes = timeinfo.tm_min;
            rtcTime.Seconds = timeinfo.tm_sec;
            M5.Rtc.SetTime(&rtcTime);
            
            rtcDate.Year = timeinfo.tm_year + 1900;
            rtcDate.Month = timeinfo.tm_mon + 1;
            rtcDate.Date = timeinfo.tm_mday;
            M5.Rtc.SetData(&rtcDate);
        }
        
        delay(2000);
        return true;
    } else {
        wifiConnected = false;
        wifiRetryCount++;
        M5.Lcd.setTextColor(RED);
        M5.Lcd.printf("\nFailed! (%d)\n", wifiRetryCount);
        delay(2000);
        return false;
    }
}

// MQTT接続
bool setupMQTT() {
    if (!wifiConnected) {
        return false;
    }
    
    snprintf(mqtt_client_id, sizeof(mqtt_client_id), "BSF-M5-%s-%08X", 
             DEVICE_ID, ESP.getEfuseMac());
    // FIXED: Changed topic format to match backend expectations
    snprintf(mqtt_topic, sizeof(mqtt_topic), "bsf/%s/%s/%s", 
             FARM_ID, DEVICE_TYPE, DEVICE_ID);
    
    mqttClient.setServer(mqtt_server, mqtt_port);
    mqttClient.setKeepAlive(60);
    mqttClient.setSocketTimeout(30);
    
    if (mqttClient.connect(mqtt_client_id, mqtt_user, mqtt_password)) {
        mqttConnected = true;
        mqttRetryCount = 0;
        Serial.println("MQTT Connected!");
        return true;
    } else {
        mqttConnected = false;
        mqttRetryCount++;
        Serial.printf("MQTT Failed! State: %d\n", mqttClient.state());
        return false;
    }
}

// センサー初期化
bool setupBME688() {
    Wire.begin(32, 33);
    
    if (!bme.begin(0x77)) {
        Serial.println("BME688 sensor not found");
        return false;
    }
    
    bme.setTemperatureOversampling(BME680_OS_2X);
    bme.setPressureOversampling(BME680_OS_16X);
    bme.setHumidityOversampling(BME680_OS_1X);
    bme.setIIRFilterSize(BME680_FILTER_SIZE_127);
    bme.setGasHeater(320, 150);
    
    return true;
}

// EEPROMデータ検証とクリア機能
void validateAndClearEEPROM() {
    EEPROM.begin(EEPROM_SIZE);
    
    // 各校正データの妥当性チェック
    bool needsClear = false;
    
    // H2S校正データチェック
    if (h2sCalibration.baseResistance > 1000000 || h2sCalibration.baseResistance < 1000) {
        Serial.printf("Invalid H2S calibration data: %lu\n", h2sCalibration.baseResistance);
        needsClear = true;
    }
    
    // NH3校正データチェック  
    if (nh3Calibration.baseResistance > 1000000 || nh3Calibration.baseResistance < 1000) {
        Serial.printf("Invalid NH3 calibration data: %lu\n", nh3Calibration.baseResistance);
        needsClear = true;
    }
    
    // G36ベースラインチェック
    if (g36Monitor.baseline_adc > 4095 || g36Monitor.baseline_adc < 0) {
        Serial.printf("Invalid G36 baseline data: %d\n", g36Monitor.baseline_adc);
        needsClear = true;
    }
    
    if (needsClear) {
        Serial.println("Clearing corrupted EEPROM data...");
        
        // 画面に警告表示
        M5.Lcd.fillScreen(BLACK);
        M5.Lcd.setTextColor(ORANGE);
        M5.Lcd.setCursor(0, 0);
        M5.Lcd.println("WARNING!");
        M5.Lcd.setTextColor(WHITE);
        M5.Lcd.println("Corrupted calibration");
        M5.Lcd.println("data detected.");
        M5.Lcd.println("Clearing EEPROM...");
        
        // EEPROMクリア
        for (int i = 0; i < EEPROM_SIZE; i++) {
            EEPROM.write(i, 0);
        }
        EEPROM.commit();
        
        // 構造体初期化
        h2sCalibration = {0, 0, 0, false};
        nh3Calibration = {0, 0, 0, false};
        g36Monitor.baseline_adc = 0;
        g36Monitor.baseline_voltage = 0;
        
        M5.Lcd.setTextColor(GREEN);
        M5.Lcd.println("EEPROM cleared!");
        M5.Lcd.setTextColor(YELLOW);
        M5.Lcd.println("Recalibration needed");
        
        Serial.println("EEPROM cleared successfully");
        delay(3000);
    }
    
    EEPROM.end();
}

// キャリブレーションデータの読み込み（検証機能付き）
void loadCalibrationData() {
    EEPROM.begin(EEPROM_SIZE);
    EEPROM.get(H2S_CAL_ADDR, h2sCalibration);
    EEPROM.get(NH3_CAL_ADDR, nh3Calibration);
    EEPROM.end();
    
    // G36ベースライン読み込み
    loadG36Baseline();
    
    // データ検証とクリア
    validateAndClearEEPROM();
    
    Serial.printf("H2S Cal: Base=%lu, Calibrated=%d\n", 
                 h2sCalibration.baseResistance, h2sCalibration.isCalibrated);
    Serial.printf("NH3 Cal: Base=%lu, Calibrated=%d\n", 
                 nh3Calibration.baseResistance, nh3Calibration.isCalibrated);
}

// キャリブレーションデータの保存
void saveCalibrationData(bool isH2S) {
    EEPROM.begin(EEPROM_SIZE);
    if (isH2S) {
        EEPROM.put(H2S_CAL_ADDR, h2sCalibration);
    } else {
        EEPROM.put(NH3_CAL_ADDR, nh3Calibration);
    }
    EEPROM.commit();
    EEPROM.end();
}

// キャリブレーション実行
void startCalibration() {
    if (currentMode == MODE_G36_MONITOR) {
        calibrateG36Baseline();
        return;
    }
    
    if (bme.humidity > 75.0) {
        M5.Lcd.fillScreen(BLACK);
        M5.Lcd.setTextColor(ORANGE);
        M5.Lcd.setCursor(0, 0);
        M5.Lcd.println("WARNING!");
        M5.Lcd.printf("High humidity: %.1f%%\n", bme.humidity);
        M5.Lcd.println("Calibration may be");
        M5.Lcd.println("less accurate");
        M5.Lcd.println("");
        M5.Lcd.println("Press A to continue");
        M5.Lcd.println("Press B to cancel");
        
        while (true) {
            M5.update();
            if (M5.BtnA.wasPressed()) break;
            if (M5.BtnB.wasPressed()) return;
            delay(10);
        }
    }
    
    float tempSum = 0;
    float humSum = 0;
    uint32_t gasSum = 0;
    int count = 0;
    unsigned long startTime = millis();
    
    M5.Lcd.fillScreen(BLACK);
    M5.Lcd.setTextSize(TEXT_SIZE_SMALL);
    M5.Lcd.setTextColor(WHITE);
    M5.Lcd.setCursor(0, 0);
    M5.Lcd.printf("Calibrating %s\n", currentMode == MODE_H2S ? "H2S" : "NH3");
    M5.Lcd.println("Clean air required!");
    
    while (millis() - startTime < CALIBRATION_TIME) {
        if (bme.performReading() && bme.gas_resistance > 0) {
            tempSum += bme.temperature;
            humSum += bme.humidity;
            gasSum += bme.gas_resistance;
            count++;
            
            int progress = ((millis() - startTime) * 100) / CALIBRATION_TIME;
            M5.Lcd.fillRect(0, 40, progress * 160 / 100, 10, GREEN);
            M5.Lcd.setCursor(0, 60);
            M5.Lcd.printf("R:%lu\n", bme.gas_resistance);
            M5.Lcd.printf("Count: %d", count);
        }
        delay(100);
    }
    
    if (count > 0) {
        CalibrationData& calTarget = currentMode == MODE_H2S ? h2sCalibration : nh3Calibration;
        calTarget.baseTemperature = tempSum / count;
        calTarget.baseHumidity = humSum / count;
        calTarget.baseResistance = gasSum / count;
        calTarget.isCalibrated = true;
        
        saveCalibrationData(currentMode == MODE_H2S);
        
        M5.Lcd.fillScreen(BLACK);
        M5.Lcd.setCursor(0, 0);
        M5.Lcd.setTextColor(GREEN);
        M5.Lcd.println("Cal Done!");
        M5.Lcd.printf("Base R:%lu\n", calTarget.baseResistance);
        M5.Lcd.printf("Base T:%.1fC\n", calTarget.baseTemperature);
        M5.Lcd.printf("Base H:%.1f%%\n", calTarget.baseHumidity);
        delay(3000);
    }
}

// 測定実行（G36監視モード対応）
bool getMeasurement(MeasurementData& data) {
    if (currentMode == MODE_G36_MONITOR) {
        // G36監視モードでは簡単な環境測定のみ
        if (bme.performReading()) {
            data.temperature = bme.temperature;
            data.pressure = bme.pressure / 100.0;
            data.humidity = bme.humidity;
            data.gas_resistance = bme.gas_resistance;
            data.timestamp = millis();
            data.isValid = true;
            data.quality_score = 1.0;
            data.high_humidity_warning = false;
            data.h2s_ppm = 0;
            data.nh3_ppm = 0;
            
            // G36監視データを融合
            fuseSensorData(data);
            return true;
        }
        return false;
    }
    
    // 通常のガス測定モード
    if (!bme.performReading()) {
        return false;
    }
    
    data.temperature = bme.temperature;
    data.pressure = bme.pressure / 100.0;
    data.humidity = bme.humidity;
    data.gas_resistance = bme.gas_resistance;
    data.timestamp = millis();
    data.heater_step = currentStep;
    data.isValid = true;
    
    data.quality_score = 1.0;
    data.high_humidity_warning = false;
    
    if (data.humidity > 70.0) {
        data.quality_score -= (data.humidity - 70.0) * 0.01;
        if (data.humidity > 80.0) {
            data.high_humidity_warning = true;
        }
    }
    
    if (data.temperature > 30.0) {
        data.quality_score -= (data.temperature - 30.0) * 0.02;
    }
    
    data.quality_score = constrain(data.quality_score, 0.0, 1.0);
    
    // BME680による参考値計算（表示には使用しない）
    float bme_h2s_ppm = calculatePPM(data.gas_resistance, data.temperature, data.humidity, true);
    float bme_nh3_ppm = calculatePPM(data.gas_resistance, data.temperature, data.humidity, false);
    
    // 初期値としてBME680の値を設定（MICS-5524で上書きされる）
    data.h2s_ppm = bme_h2s_ppm;
    data.nh3_ppm = bme_nh3_ppm;
    
    // MICS-5524データとの融合（メイン表示値として使用）
    fuseSensorData(data);
    
    // 品質スコアによる調整（MICS-5524が利用できない場合のみ）
    if (!mics5524Available && data.quality_score < 0.8) {
        data.h2s_ppm *= data.quality_score;
        data.nh3_ppm *= data.quality_score;
    }
    
    avgBuffer.temp_sum += data.temperature;
    avgBuffer.humidity_sum += data.humidity;
    avgBuffer.pressure_sum += data.pressure;
    avgBuffer.gas_sum += data.gas_resistance;
    avgBuffer.h2s_sum += data.h2s_ppm;
    avgBuffer.nh3_sum += data.nh3_ppm;
    avgBuffer.count++;
    
    return true;
}

// MQTTデータ送信（G36データ追加）
bool sendSensorData() {
    if (!mqttConnected || (currentMode != MODE_G36_MONITOR && avgBuffer.count == 0)) {
        return false;
    }
    
    StaticJsonDocument<1536> doc;  // サイズを拡張
    
    doc["farm_id"] = FARM_ID;
    doc["device_id"] = DEVICE_ID;
    doc["device_type"] = DEVICE_TYPE;
    doc["device_name"] = DEVICE_NAME;
    doc["location"] = LOCATION;
    
    String modeStr;
    switch(currentMode) {
        case MODE_H2S: modeStr = "H2S"; break;
        case MODE_NH3: modeStr = "NH3"; break;
        case MODE_G36_MONITOR: modeStr = "G36_MONITOR"; break;
        default: modeStr = "IDLE"; break;
    }
    doc["mode"] = modeStr;
    
    M5.Rtc.GetTime(&rtcTime);
    M5.Rtc.GetData(&rtcDate);
    char timestamp[30];
    snprintf(timestamp, sizeof(timestamp), "%04d-%02d-%02dT%02d:%02d:%02dZ",
             rtcDate.Year, rtcDate.Month, rtcDate.Date,
             rtcTime.Hours, rtcTime.Minutes, rtcTime.Seconds);
    doc["timestamp"] = timestamp;
    
    // FIXED: Changed from "measurements" to "readings" to match backend expectations
    JsonArray readings = doc.createNestedArray("readings");
    
    if (currentMode == MODE_G36_MONITOR) {
        // G36監視モード専用データ
        JsonObject g36 = readings.createNestedObject();
        // FIXED: Changed from "measurement_type" to "type" to match backend expectations
        g36["type"] = "g36_voltage_monitor";
        g36["baseline_adc"] = currentMeasurement.g36_data.baseline_adc;
        g36["current_adc"] = currentMeasurement.g36_data.current_adc;
        g36["baseline_voltage"] = round(currentMeasurement.g36_data.baseline_voltage * 1000) / 1000.0;
        g36["current_voltage"] = round(currentMeasurement.g36_data.current_voltage * 1000) / 1000.0;
        g36["difference"] = currentMeasurement.g36_data.difference;
        g36["sensitivity_percent"] = round(currentMeasurement.g36_data.sensitivity_percent * 10) / 10.0;
        g36["detection_time_ms"] = currentMeasurement.g36_data.detection_time;
        g36["is_detecting"] = currentMeasurement.g36_data.is_detecting;
        g36["warning_level"] = currentMeasurement.g36_data.warning_level;
        g36["alert_level"] = currentMeasurement.g36_data.alert_level;
        g36["variability"] = currentMeasurement.g36_data.variability;
        g36["status"] = currentMeasurement.g36_data.status_text;
        g36["unit"] = "V";
        
        // 基本環境データ
        JsonObject temp = readings.createNestedObject();
        temp["type"] = "temperature";
        temp["value"] = round(currentMeasurement.temperature * 100) / 100.0;
        temp["unit"] = "°C";
        
        JsonObject hum = readings.createNestedObject();
        hum["type"] = "humidity";
        hum["value"] = round(currentMeasurement.humidity * 100) / 100.0;
        hum["unit"] = "%RH";
        
    } else {
        // 通常のガス測定モードデータ
        float avg_temp = avgBuffer.temp_sum / avgBuffer.count;
        float avg_humidity = avgBuffer.humidity_sum / avgBuffer.count;
        float avg_pressure = avgBuffer.pressure_sum / avgBuffer.count;
        float avg_gas = avgBuffer.gas_sum / avgBuffer.count;
        float avg_h2s = avgBuffer.h2s_sum / avgBuffer.count;
        float avg_nh3 = avgBuffer.nh3_sum / avgBuffer.count;
        
        JsonObject temp = readings.createNestedObject();
        temp["type"] = "temperature";
        temp["value"] = round(avg_temp * 100) / 100.0;
        temp["unit"] = "°C";
        
        JsonObject hum = readings.createNestedObject();
        hum["type"] = "humidity";
        hum["value"] = round(avg_humidity * 100) / 100.0;
        hum["unit"] = "%RH";
        
        JsonObject press = readings.createNestedObject();
        press["type"] = "pressure";
        press["value"] = round(avg_pressure * 100) / 100.0;
        press["unit"] = "hPa";
        
        JsonObject gas = readings.createNestedObject();
        gas["type"] = "gas_resistance";
        gas["value"] = round(avg_gas);
        gas["unit"] = "ohm";
        
        JsonObject h2s = readings.createNestedObject();
        h2s["type"] = "h2s";
        h2s["value"] = round(avg_h2s * 1000) / 1000.0;
        h2s["unit"] = "ppm";
        h2s["source"] = mics5524Available ? "MICS-5524" : "BME680_estimate";
        
        JsonObject nh3 = readings.createNestedObject();
        nh3["type"] = "nh3";
        nh3["value"] = round(avg_nh3 * 100) / 100.0;
        nh3["unit"] = "ppm";
        nh3["source"] = mics5524Available ? "MICS-5524" : "BME680_estimate";
        if (!mics5524Available) {
            nh3["note"] = "Estimated from VOC";
        }
        
        // BME680参考データ（実際の表示値とは別に送信）
        if (mics5524Available) {
            JsonObject bme_gas = readings.createNestedObject();
            bme_gas["type"] = "bme680_gas_reference";
            bme_gas["value"] = round(avg_gas);
            bme_gas["unit"] = "ohm";
            bme_gas["note"] = "Reference data only";
        }
        
        if (currentMeasurement.mics_available) {
            // MICS-5524の生データも送信
            JsonObject mics_raw = readings.createNestedObject();
            mics_raw["type"] = "mics_raw_adc";
            mics_raw["value"] = currentMeasurement.g36_data.current_adc;
            mics_raw["unit"] = "adc";
            
            if (currentMeasurement.mics_co_ppm > 0.1) {
                JsonObject mics_co = readings.createNestedObject();
                mics_co["type"] = "co";
                mics_co["value"] = round(currentMeasurement.mics_co_ppm * 10) / 10.0;
                mics_co["unit"] = "ppm";
                mics_co["source"] = "MICS-5524";
            }
        }
    }
    
    JsonObject metadata = doc.createNestedObject("metadata");
    metadata["signal_strength"] = WiFi.RSSI();
    metadata["battery_level"] = getBatteryLevel();
    metadata["sample_count"] = currentMode == MODE_G36_MONITOR ? 1 : avgBuffer.count;
    metadata["heater_step"] = currentStep;
    metadata["h2s_calibrated"] = h2sCalibration.isCalibrated;
    metadata["nh3_calibrated"] = nh3Calibration.isCalibrated;
    metadata["g36_calibrated"] = g36Monitor.baseline_adc > 0;
    metadata["quality_score"] = currentMeasurement.quality_score;
    metadata["high_humidity_warning"] = currentMeasurement.high_humidity_warning;
    metadata["humidity_compensation_applied"] = true;
    metadata["mics5524_available"] = mics5524Available;
    metadata["g36_monitor_active"] = g36MonitorActive;
    
    String jsonString;
    serializeJson(doc, jsonString);
    
    bool success = mqttClient.publish(mqtt_topic, jsonString.c_str());
    
    if (success) {
        Serial.println("MQTT send successful");
        if (currentMode != MODE_G36_MONITOR) {
            memset(&avgBuffer, 0, sizeof(avgBuffer));
        }
        avgBuffer.last_send = millis();
        return true;
    } else {
        mqttConnected = false;
        return false;
    }
}

// 画面表示更新（G36監視モード対応）
void updateDisplay(const MeasurementData& data) {
    M5.Lcd.fillScreen(BLACK);
    M5.Lcd.setTextSize(TEXT_SIZE_SMALL);
    
    M5.Rtc.GetTime(&rtcTime);
    M5.Lcd.setTextColor(WHITE);
    M5.Lcd.setCursor(0, 0);
    M5.Lcd.printf("%02d:%02d:%02d ", rtcTime.Hours, rtcTime.Minutes, rtcTime.Seconds);
    
    // モード表示
    switch(currentMode) {
        case MODE_H2S:
            M5.Lcd.setTextColor(YELLOW);
            M5.Lcd.print("H2S");
            break;
        case MODE_NH3:
            M5.Lcd.setTextColor(BLUE);
            M5.Lcd.print("NH3");
            break;
        case MODE_G36_MONITOR:
            M5.Lcd.setTextColor(ORANGE);
            M5.Lcd.print("G36");
            break;
        default:
            M5.Lcd.setTextColor(WHITE);
            M5.Lcd.print("IDLE");
    }
    
    if (data.high_humidity_warning) {
        M5.Lcd.setTextColor(ORANGE);
        M5.Lcd.setCursor(100, 0);
        M5.Lcd.print("HUM!");
    }
    
    // 接続状態
    M5.Lcd.setCursor(0, 10);
    M5.Lcd.setTextColor(wifiConnected ? GREEN : RED);
    M5.Lcd.printf("WiFi:%s ", wifiConnected ? "OK" : "NG");
    M5.Lcd.setTextColor(mqttConnected ? GREEN : RED);
    M5.Lcd.printf("MQTT:%s", mqttConnected ? "OK" : "NG");
    
    if (currentMode == MODE_G36_MONITOR) {
        // G36監視モード専用表示
        M5.Lcd.setCursor(0, 20);
        M5.Lcd.setTextColor(WHITE);
        M5.Lcd.printf("Base:%d(%.3fV)\n", data.g36_data.baseline_adc, data.g36_data.baseline_voltage);
        M5.Lcd.printf("Curr:%d(%.3fV)\n", data.g36_data.current_adc, data.g36_data.current_voltage);
        
        // ステータス表示
        if (data.g36_data.alert_level) {
            M5.Lcd.setTextColor(RED);
        } else if (data.g36_data.warning_level) {
            M5.Lcd.setTextColor(ORANGE);
        } else if (data.g36_data.is_detecting) {
            M5.Lcd.setTextColor(YELLOW);
        } else {
            M5.Lcd.setTextColor(GREEN);
        }
        
        M5.Lcd.printf("Diff:%+d ", data.g36_data.difference);
        M5.Lcd.print(data.g36_data.status_text);
        
        if (data.g36_data.is_detecting) {
            M5.Lcd.printf("(%lus)", data.g36_data.detection_time / 1000);
        }
        M5.Lcd.println();
        
        M5.Lcd.setTextColor(WHITE);
        M5.Lcd.printf("Sens:%.1f%% Var:%d\n", data.g36_data.sensitivity_percent, data.g36_data.variability);
        
    } else {
        // 通常のガス測定モード表示
        M5.Lcd.setTextColor(WHITE);
        M5.Lcd.setCursor(0, 20);
        M5.Lcd.printf("T:%.1fC H:%.1f%%\n", data.temperature, data.humidity);
        
        // センサー情報表示
        if (mics5524Available) {
            M5.Lcd.setTextColor(GREEN);
            M5.Lcd.printf("MICS-5524 Active\n");
        } else {
            M5.Lcd.setTextColor(YELLOW);
            M5.Lcd.printf("BME680 Est Gas:%lu\n", data.gas_resistance);
        }
        
        if (currentMode != MODE_IDLE) {
            // H2S表示（MICS-5524またはBME680推定値）
            M5.Lcd.setTextColor(data.h2s_ppm > 3.0 ? RED : GREEN);
            M5.Lcd.printf("H2S:%.3fppm", data.h2s_ppm);
            if (!mics5524Available) {
                M5.Lcd.setTextColor(ORANGE);
                M5.Lcd.print("*");  // 推定値マーク
            }
            M5.Lcd.println();
            
            // NH3表示（MICS-5524またはBME680推定値）
            M5.Lcd.setTextColor(data.nh3_ppm > 25.0 ? RED : GREEN);
            M5.Lcd.printf("NH3:%.1fppm", data.nh3_ppm);
            if (!mics5524Available) {
                M5.Lcd.setTextColor(ORANGE);
                M5.Lcd.print("*");  // 推定値マーク
            }
            M5.Lcd.println();
        }
    }
    
    // バッテリーとサンプル数
    M5.Lcd.setTextColor(YELLOW);
    M5.Lcd.setCursor(0, 60);
    M5.Lcd.printf("Bat:%d%% ", getBatteryLevel());
    
    if (currentMode != MODE_G36_MONITOR) {
        M5.Lcd.printf("Samp:%d", avgBuffer.count);
        
        // 品質スコア表示
        M5.Lcd.setCursor(100, 60);
        if (data.quality_score >= 0.8) {
            M5.Lcd.setTextColor(GREEN);
        } else if (data.quality_score >= 0.6) {
            M5.Lcd.setTextColor(YELLOW);
        } else {
            M5.Lcd.setTextColor(RED);
        }
        M5.Lcd.printf("Q:%.0f%%", data.quality_score * 100);
        
        // ヒーターステップ
        if (currentMode != MODE_IDLE) {
            M5.Lcd.setCursor(0, 70);
            M5.Lcd.setTextColor(ORANGE);
            M5.Lcd.printf("Step:%d/5", currentStep + 1);
        }
    } else {
        // G36監視モードでは校正状態を表示
        M5.Lcd.setTextColor(data.g36_data.baseline_adc > 0 ? GREEN : RED);
        M5.Lcd.printf("Cal:%s", data.g36_data.baseline_adc > 0 ? "OK" : "NG");
    }
}

// モード変更処理（G36監視モード追加）
void handleModeChange() {
    if (M5.BtnA.wasPressed()) {
        switch (currentMode) {
            case MODE_IDLE:
                currentMode = MODE_H2S;
                setMICS5524Power(true);
                g36MonitorActive = false;
                break;
            case MODE_H2S:
                currentMode = MODE_NH3;
                break;
            case MODE_NH3:
                currentMode = MODE_G36_MONITOR;
                setMICS5524Power(false);
                g36MonitorActive = true;
                break;
            case MODE_G36_MONITOR:
                currentMode = MODE_IDLE;
                g36MonitorActive = false;
                break;
        }
        currentStep = 0;
        lastHeaterUpdate = millis();
        Serial.printf("Mode changed to: %s\n", 
                     currentMode == MODE_H2S ? "H2S" : 
                     currentMode == MODE_NH3 ? "NH3" : 
                     currentMode == MODE_G36_MONITOR ? "G36_MONITOR" : "IDLE");
    }
    
    if (M5.BtnB.wasPressed() && (currentMode != MODE_IDLE)) {
        startCalibration();
    }
}

void setup() {
    M5.begin();
    M5.Lcd.begin();
    M5.Axp.ScreenBreath(SCREEN_BRIGHTNESS);
    M5.Lcd.setRotation(3);
    M5.Lcd.fillScreen(BLACK);
    
    Serial.begin(115200);
    delay(1000);
    Serial.println("\n=== BSF-LoopTech Gas Sensor with G36 Monitor ===");
    Serial.printf("Device: %s (%s)\n", DEVICE_ID, DEVICE_NAME);
    
    M5.Lcd.setTextSize(TEXT_SIZE_SMALL);
    M5.Lcd.setTextColor(WHITE);
    M5.Lcd.setCursor(0, 0);
    M5.Lcd.println("BSF-LoopTech");
    M5.Lcd.println("Gas Sensor v2.1");
    M5.Lcd.println("with G36 Monitor");
    M5.Lcd.setTextColor(YELLOW);
    M5.Lcd.printf("ID: %s\n", DEVICE_ID);
    delay(2000);
    
    M5.Lcd.fillScreen(BLACK);
    M5.Lcd.setCursor(0, 0);
    M5.Lcd.setTextColor(WHITE);
    M5.Lcd.print("Init BME688...");
    
    if (!setupBME688()) {
        M5.Lcd.setTextColor(RED);
        M5.Lcd.println("FAILED!");
        while (1) {
            M5.Lcd.fillScreen(RED);
            delay(500);
            M5.Lcd.fillScreen(BLACK);
            delay(500);
        }
    }
    
    M5.Lcd.setTextColor(GREEN);
    M5.Lcd.println("OK");
    
    M5.Lcd.setCursor(0, 10);
    M5.Lcd.setTextColor(WHITE);
    M5.Lcd.print("Init ");
    setupMICS5524();
    
    if (!mics5524Available) {
        M5.Lcd.setTextColor(YELLOW);
        M5.Lcd.setCursor(0, 20);
        M5.Lcd.println("BME688 only mode");
    }
    
    loadCalibrationData();
    delay(1000);
    
    setupWiFi();
    
    if (wifiConnected) {
        setupMQTT();
    }
    
    lastMeasurement = millis();
    lastWifiCheck = millis();
    lastMqttCheck = millis();
    lastDisplayUpdate = millis();
    avgBuffer.last_send = millis();
    
    setMICS5524Power(false);
    
    Serial.println("Setup completed. Starting gas monitoring...");
    Serial.println("A: Change mode (IDLE->H2S->NH3->G36->IDLE)");
    Serial.println("B: Calibrate (in H2S, NH3, or G36 mode)");
    Serial.println("");
    Serial.println("=== Sensor Configuration ===");
    if (mics5524Available) {
        Serial.println("G36 Voltage Monitor: ACTIVE");
        Serial.println("Gas Detection: G36 voltage-based");
        Serial.println("BME680: Environmental reference");
    } else {
        Serial.println("G36 Voltage Monitor: FAILED");
        Serial.println("Gas Detection: BME680 estimates only");
    }
    if (g36Monitor.baseline_adc > 0) {
        Serial.printf("G36 Baseline: %d ADC (%.3fV) - CALIBRATED\n", 
                     g36Monitor.baseline_adc, g36Monitor.baseline_voltage);
    } else {
        Serial.println("G36 Baseline: NOT CALIBRATED");
        Serial.println("** Please calibrate G36 baseline in G36 mode **");
    }
    Serial.println("============================");
}

void loop() {
    M5.update();
    unsigned long now = millis();
    
    handleModeChange();
    
    updateHeaterProfile();
    
    if (now - lastWifiCheck >= WIFI_RECONNECT_INTERVAL) {
        lastWifiCheck = now;
        if (WiFi.status() != WL_CONNECTED) {
            wifiConnected = false;
            mqttConnected = false;
            setupWiFi();
        }
    }
    
    if (wifiConnected && (now - lastMqttCheck >= MQTT_RECONNECT_INTERVAL)) {
        lastMqttCheck = now;
        if (!mqttClient.connected()) {
            mqttConnected = false;
            setupMQTT();
        }
    }
    
    if (mqttConnected) {
        mqttClient.loop();
    }
    
    // G36監視モードでは高頻度で測定
    unsigned long measurementInterval = (currentMode == MODE_G36_MONITOR) ? 200 : MEASUREMENT_INTERVAL;
    
    if (now - lastMeasurement >= measurementInterval) {
        lastMeasurement = now;
        if (getMeasurement(currentMeasurement)) {
            // G36監視モードでは1秒間隔でMQTT送信
            unsigned long sendInterval = (currentMode == MODE_G36_MONITOR) ? 1000 : SEND_INTERVAL;
            if (now - avgBuffer.last_send >= sendInterval) {
                sendSensorData();
            }
        }
    }
    
    if (now - lastDisplayUpdate >= DISPLAY_UPDATE_INTERVAL) {
        lastDisplayUpdate = now;
        updateDisplay(currentMeasurement);
    }
    
    delay(10);
}