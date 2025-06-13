#include <M5StickC.h>
#include <Wire.h>
#include <EEPROM.h>
#include <WiFi.h>
#include <PubSubClient.h>  // MQTT Client library
#include <time.h>
#include "Adafruit_BME680.h"
#include <ArduinoJson.h>   // JSON library for formatting data

// Device Settings
const char* DEVICE_ID = "taka001";  // デバイスID
const char* DEVICE_TYPE = "gas_sensor";  // デバイスタイプ
const char* FARM_ID = "farm123";  // ファームID

// WiFi and Server Settings
const char* ssid = "TP-LINK_6A98";
const char* password = "kohakukohaku";
const char* ntpServer = "pool.ntp.org";
const long gmtOffset_sec = 9 * 3600;  // JST
const int daylightOffset_sec = 0;

// MQTT Settings
const char* mqtt_server = "192.168.7.3";  // MQTT broker hostname
const int mqtt_port = 1883;              // MQTT broker port
const char* mqtt_user = NULL;            // MQTT username (if required)
const char* mqtt_password = NULL;       // MQTT password (if required)
char mqtt_topic[50];                    // Topic will be constructed as bsf/{farm_id}/{device_type}/{device_id}

// MQTT Client
WiFiClient espClient;
PubSubClient mqttClient(espClient);

Adafruit_BME680 bme;
RTC_TimeTypeDef rtcTime;
RTC_DateTypeDef rtcDate;

// Operation modes
enum OperationMode {
    MODE_SELECT,
    MODE_CALIBRATE,
    MODE_MEASURE_H2S,
    MODE_MEASURE_NH3
};

// Measurement state structure
struct MeasurementState {
    float temperature;
    float humidity;
    float pressure;
    float gas_resistance;
    uint32_t timestamp;
    bool isValid;
};

// Average buffer with separate gas resistances
struct AverageBuffer {
    float temp_sum;
    float humidity_sum;
    float pressure_sum;
    float h2s_gas_sum;
    float nh3_gas_sum;
    float h2s_ppm_sum;
    float nh3_ppm_sum;
    int count;
    unsigned long last_update;
} avgBuffer = {0};

// Global variables
OperationMode currentMode = MODE_SELECT;
MeasurementState currentMeasurement = {0};
MeasurementState baselineH2S = {0};
MeasurementState baselineNH3 = {0};

// Constants
const int SCREEN_WIDTH = 160;
const int SCREEN_HEIGHT = 80;
const int TEXT_SIZE_NORMAL = 2;
const int TEXT_SIZE_LARGE = 3;
const int EEPROM_SIZE = 512;
const int EEPROM_H2S_ADDR = 0;
const int EEPROM_NH3_ADDR = sizeof(MeasurementState);

// Gas sensor constants - adjusted based on typical values
const float H2S_SENSITIVITY = 0.0247;
const float NH3_SENSITIVITY = 0.0373;
const float H2S_BASELINE = 10.8;
const float NH3_BASELINE = 198.0;

// Heater profiles - optimized for gas detection
const uint16_t H2S_PROFILE[] = {200, 300, 250, 350, 200};
const uint16_t NH3_PROFILE[] = {250, 350, 300, 400, 250};
const int PROFILE_STEPS = 5;
const int PROFILE_DURATION = 100;
const int PROFILE_SWITCH_TIME = 5000;

// Timing constants
const unsigned long MEASUREMENT_INTERVAL = 2000;  // 2 seconds
const unsigned long AVERAGE_INTERVAL = 30000;     // 30 seconds
const unsigned long CALIBRATION_TIME = 30000;     // 30 seconds for zero calibration
const unsigned long MQTT_RECONNECT_INTERVAL = 5000; // 5 seconds between MQTT reconnection attempts

// Gas resistance validity thresholds
const float MIN_GAS_RESISTANCE = 100.0;    // minimum valid resistance
const float MAX_GAS_RESISTANCE = 50000.0;  // maximum valid resistance

unsigned long lastMeasurement = 0;
unsigned long lastProfileSwitch = 0;
unsigned long lastMqttReconnectAttempt = 0;
int currentProfileStep = 0;

// Color definitions
#define BLACK 0x0000
#define WHITE 0xFFFF
#define RED   0xF800
#define GREEN 0x07E0
#define BLUE  0x001F
#define YELLOW 0xFFE0

void updateRTC() {
    M5.Rtc.GetTime(&rtcTime);
    M5.Rtc.GetData(&rtcDate);
}

bool setupTime() {
    WiFi.begin(ssid, password);
    M5.Lcd.print("Connecting to WiFi");
    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 20) {
        delay(500);
        M5.Lcd.print(".");
        attempts++;
    }
    
    if (WiFi.status() == WL_CONNECTED) {
        M5.Lcd.println("\nConnected");
        M5.Lcd.println("Sync Time...");
        
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
            
            M5.Lcd.println("Time Synced!");
            delay(1000);
            return true;
        }
        M5.Lcd.println("Sync Failed!");
    } else {
        M5.Lcd.println("\nWiFi Failed!");
    }
    
    delay(2000);
    return false;
}

void setupMQTT() {
    // Construct the MQTT topic
    snprintf(mqtt_topic, sizeof(mqtt_topic), "bsf/%s/%s/%s", FARM_ID, DEVICE_TYPE, DEVICE_ID);
    
    // Set MQTT server and port
    mqttClient.setServer(mqtt_server, mqtt_port);
    
    // Connect to MQTT broker
    connectMQTT();
}

void connectMQTT() {
    // Only attempt to connect if we're not already connected and enough time has passed since last attempt
    if (!mqttClient.connected() && (millis() - lastMqttReconnectAttempt > MQTT_RECONNECT_INTERVAL)) {
        lastMqttReconnectAttempt = millis();
        
        Serial.print("Connecting to MQTT broker...");
        
        // Create a client ID based on device ID and a random number
        String clientId = "M5Stick-";
        clientId += DEVICE_ID;
        clientId += "-";
        clientId += String(random(0xffff), HEX);
        
        // Attempt to connect
        if (mqttClient.connect(clientId.c_str(), mqtt_user, mqtt_password)) {
            Serial.println("connected");
        } else {
            Serial.print("failed, rc=");
            Serial.print(mqttClient.state());
            Serial.println(" will try again later");
        }
    }
}

// ガス抵抗値の有効性チェック
bool isValidGasResistance(float resistance) {
    return (resistance > MIN_GAS_RESISTANCE && resistance < MAX_GAS_RESISTANCE);
}

float calculatePPM(float gas_resistance, float temperature, float humidity, bool isH2S) {
    const MeasurementState& baseline = isH2S ? baselineH2S : baselineNH3;
    
    // ベースラインチェック
    if (!baseline.isValid || !isValidGasResistance(baseline.gas_resistance)) {
        return 0.0;
    }

    // 現在の抵抗値チェック
    if (!isValidGasResistance(gas_resistance)) {
        return 0.0;
    }

    float resistance_ratio = gas_resistance / baseline.gas_resistance;
    float temp_correction = 1.0 + 0.02 * (temperature - baseline.temperature);
    float hum_correction = 1.0 + 0.01 * (humidity - baseline.humidity);
    
    float sensitivity = isH2S ? H2S_SENSITIVITY : NH3_SENSITIVITY;
    float baseline_value = isH2S ? H2S_BASELINE : NH3_BASELINE;
    
    float ppm = baseline_value - (log10(resistance_ratio) / sensitivity) * temp_correction * hum_correction;
    
    if (ppm < 0) ppm = 0;
    return isH2S ? constrain(ppm, 0.0, 10.0) : constrain(ppm, 0.0, 1000.0);
}

void performZeroCalibration() {
    M5.Lcd.fillScreen(BLACK);
    M5.Lcd.setTextSize(TEXT_SIZE_NORMAL);
    M5.Lcd.setTextColor(WHITE);
    M5.Lcd.setCursor(0, 0);
    M5.Lcd.println("Zero Calibration");
    M5.Lcd.println("Fresh Air...");
    
    float temp_sum = 0;
    float humidity_sum = 0;
    float pressure_sum = 0;
    float gas_sum = 0;
    int valid_count = 0;
    
    for (int i = 0; i < 30; i++) {
        if (bme.performReading()) {
            float current_resistance = bme.gas_resistance;
            if (isValidGasResistance(current_resistance)) {
                temp_sum += bme.temperature;
                humidity_sum += bme.humidity;
                pressure_sum += bme.pressure / 100.0;
                gas_sum += current_resistance;
                valid_count++;
            }
            
            M5.Lcd.setCursor(0, 40);
            M5.Lcd.printf("Progress: %d%%", (i + 1) * 3);
            M5.Lcd.setCursor(0, 60);
            M5.Lcd.printf("Valid: %d", valid_count);
        }
        delay(1000);
    }
    
    if (valid_count > 0) {
        baselineH2S.temperature = temp_sum / valid_count;
        baselineH2S.humidity = humidity_sum / valid_count;
        baselineH2S.pressure = pressure_sum / valid_count;
        baselineH2S.gas_resistance = gas_sum / valid_count;
        baselineH2S.timestamp = millis();
        baselineH2S.isValid = true;
        
        // NH3も同じベースラインを使用
        baselineNH3 = baselineH2S;
        
        EEPROM.begin(EEPROM_SIZE);
        EEPROM.put(EEPROM_H2S_ADDR, baselineH2S);
        EEPROM.put(EEPROM_NH3_ADDR, baselineNH3);
        EEPROM.commit();
        EEPROM.end();
        
        M5.Lcd.fillScreen(BLACK);
        M5.Lcd.setCursor(0, 0);
        M5.Lcd.println("Zero Cal Done!");
        M5.Lcd.printf("Base R: %.0f", baselineH2S.gas_resistance);
        delay(2000);
    }
}

void sendToMQTT(float temp, float humidity, float pressure, 
               float h2s_resistance, float nh3_resistance,
               float h2s_ppm, float nh3_ppm) {
    // Check if we're connected to MQTT broker
    if (!mqttClient.connected()) {
        connectMQTT();
        if (!mqttClient.connected()) {
            Serial.println("Failed to connect to MQTT broker, skipping data send");
            return;
        }
    }

    // Create a JSON document
    StaticJsonDocument<512> doc;
    
    // Create an array for readings
    JsonArray readings = doc.createNestedArray("readings");
    
    // Add temperature reading
    JsonObject tempReading = readings.createNestedObject();
    tempReading["type"] = "temperature";
    tempReading["value"] = temp;
    tempReading["unit"] = "°C";
    
    // Add humidity reading
    JsonObject humReading = readings.createNestedObject();
    humReading["type"] = "humidity";
    humReading["value"] = humidity;
    humReading["unit"] = "%";
    
    // Add pressure reading
    JsonObject pressReading = readings.createNestedObject();
    pressReading["type"] = "pressure";
    pressReading["value"] = pressure;
    pressReading["unit"] = "hPa";
    
    // Add H2S resistance reading
    if (h2s_resistance > 0) {
        JsonObject h2sResReading = readings.createNestedObject();
        h2sResReading["type"] = "h2s_resistance";
        h2sResReading["value"] = h2s_resistance;
        h2sResReading["unit"] = "ohm";
    }
    
    // Add NH3 resistance reading
    if (nh3_resistance > 0) {
        JsonObject nh3ResReading = readings.createNestedObject();
        nh3ResReading["type"] = "nh3_resistance";
        nh3ResReading["value"] = nh3_resistance;
        nh3ResReading["unit"] = "ohm";
    }
    
    // Add H2S ppm reading
    if (h2s_ppm > 0) {
        JsonObject h2sPpmReading = readings.createNestedObject();
        h2sPpmReading["type"] = "h2s";
        h2sPpmReading["value"] = h2s_ppm;
        h2sPpmReading["unit"] = "ppm";
    }
    
    // Add NH3 ppm reading
    if (nh3_ppm > 0) {
        JsonObject nh3PpmReading = readings.createNestedObject();
        nh3PpmReading["type"] = "nh3";
        nh3PpmReading["value"] = nh3_ppm;
        nh3PpmReading["unit"] = "ppm";
    }
    
    // Add timestamp
    updateRTC();
    char timestamp[25];
    snprintf(timestamp, sizeof(timestamp), "%04d-%02d-%02dT%02d:%02d:%02dZ", 
             rtcDate.Year, rtcDate.Month, rtcDate.Date,
             rtcTime.Hours, rtcTime.Minutes, rtcTime.Seconds);
    doc["timestamp"] = timestamp;
    
    // Serialize JSON to string
    String jsonString;
    serializeJson(doc, jsonString);
    
    // Publish to MQTT
    Serial.print("Publishing to topic: ");
    Serial.println(mqtt_topic);
    Serial.print("Message: ");
    Serial.println(jsonString);
    
    if (mqttClient.publish(mqtt_topic, jsonString.c_str())) {
        Serial.println("Publish success");
    } else {
        Serial.println("Publish failed");
    }
}

void displayMeasurement(float h2s_ppm, float nh3_ppm) {
    M5.Lcd.fillScreen(BLACK);
    M5.Lcd.setTextSize(TEXT_SIZE_NORMAL);
    M5.Lcd.setTextColor(WHITE);
    
    // Update and display time
    updateRTC();
    M5.Lcd.setCursor(0, 0);
    M5.Lcd.printf("%02d:%02d:%02d\n", rtcTime.Hours, rtcTime.Minutes, rtcTime.Seconds);
    
    // Display mode and device ID
    M5.Lcd.printf("%s\n", currentMode == MODE_MEASURE_H2S ? "H2S" : "NH3");
    M5.Lcd.setTextSize(1);
    M5.Lcd.printf("ID: %s\n", DEVICE_ID);
    M5.Lcd.setTextSize(TEXT_SIZE_NORMAL);
    
    // Display environmental data
    M5.Lcd.setTextColor(GREEN);
    M5.Lcd.printf("T:%.1fC\n", currentMeasurement.temperature);
    M5.Lcd.printf("H:%.1f%%\n", currentMeasurement.humidity);
    
    // Display gas data
    if (currentMode == MODE_MEASURE_H2S) {
        M5.Lcd.setTextColor(h2s_ppm > 3.0 ? RED : YELLOW);
        M5.Lcd.printf("H2S:%.3f\n", h2s_ppm);
    } else {
        M5.Lcd.setTextColor(nh3_ppm > 100.0 ? RED : YELLOW);
        M5.Lcd.printf("NH3:%.3f\n", nh3_ppm);
    }
}

void processMeasurement() {
    if (!bme.performReading()) {
        Serial.println("Failed to perform reading");
        return;
    }

    currentMeasurement.temperature = bme.temperature;
    currentMeasurement.humidity = bme.humidity;
    currentMeasurement.pressure = bme.pressure / 100.0;
    currentMeasurement.gas_resistance = bme.gas_resistance;
    currentMeasurement.timestamp = millis();
    currentMeasurement.isValid = true;

    float h2s_resistance = 0;
    float nh3_resistance = 0;
    float h2s_ppm = 0;
    float nh3_ppm = 0;

    // Get current gas resistance based on mode
    if (isValidGasResistance(bme.gas_resistance)) {
        if (currentMode == MODE_MEASURE_H2S) {
            h2s_resistance = bme.gas_resistance;
            h2s_ppm = calculatePPM(h2s_resistance, currentMeasurement.temperature, 
                                 currentMeasurement.humidity, true);
        } else {
            nh3_resistance = bme.gas_resistance;
            nh3_ppm = calculatePPM(nh3_resistance, currentMeasurement.temperature, 
                                 currentMeasurement.humidity, false);
        }
    }

    // Update averages
    avgBuffer.temp_sum += currentMeasurement.temperature;
    avgBuffer.humidity_sum += currentMeasurement.humidity;
    avgBuffer.pressure_sum += currentMeasurement.pressure;
    avgBuffer.h2s_gas_sum += h2s_resistance;
    avgBuffer.nh3_gas_sum += nh3_resistance;
    avgBuffer.h2s_ppm_sum += h2s_ppm;
    avgBuffer.nh3_ppm_sum += nh3_ppm;
    avgBuffer.count++;

    // Display current values
    displayMeasurement(h2s_ppm, nh3_ppm);
    
    // Output 30-second averages
    if (millis() - avgBuffer.last_update >= AVERAGE_INTERVAL && avgBuffer.count > 0) {
        float avg_temp = avgBuffer.temp_sum / avgBuffer.count;
        float avg_humidity = avgBuffer.humidity_sum / avgBuffer.count;
        float avg_pressure = avgBuffer.pressure_sum / avgBuffer.count;
        float avg_h2s_resistance = avgBuffer.h2s_gas_sum / avgBuffer.count;
        float avg_nh3_resistance = avgBuffer.nh3_gas_sum / avgBuffer.count;
        float avg_h2s_ppm = avgBuffer.h2s_ppm_sum / avgBuffer.count;
        float avg_nh3_ppm = avgBuffer.nh3_ppm_sum / avgBuffer.count;

        // Serial output
        updateRTC();
        Serial.printf("%s,%04d-%02d-%02d %02d:%02d:%02d,%.1f,%.1f,%.1f,%.0f,%.0f,%.3f,%.3f\n",
            DEVICE_ID,
            rtcDate.Year, rtcDate.Month, rtcDate.Date,
            rtcTime.Hours, rtcTime.Minutes, rtcTime.Seconds,
            avg_temp, avg_humidity, avg_pressure,
            avg_h2s_resistance, avg_nh3_resistance,
            avg_h2s_ppm, avg_nh3_ppm);

        // Send to MQTT
        sendToMQTT(avg_temp, avg_humidity, avg_pressure,
                  avg_h2s_resistance, avg_nh3_resistance,
                  avg_h2s_ppm, avg_nh3_ppm);

        // Reset averages
        memset(&avgBuffer, 0, sizeof(avgBuffer));
        avgBuffer.last_update = millis();
    }
}

void setup() {
    M5.begin();
    M5.Axp.ScreenBreath(15);
    M5.Lcd.setRotation(3);
    M5.Lcd.fillScreen(BLACK);
    M5.Lcd.setTextSize(TEXT_SIZE_NORMAL);
    
    Serial.begin(115200);
    Serial.println("Starting BME688 Monitor");
    
    // デバイス情報表示
    M5.Lcd.setTextColor(WHITE);
    M5.Lcd.setCursor(0, 0);
    M5.Lcd.printf("Device: %s\n", DEVICE_ID);
    
    // WiFiとNTP設定
    if (!setupTime()) {
        M5.Lcd.println("Time sync failed");
        delay(2000);
    }
    
    // MQTT設定
    setupMQTT();
    
    // センサー初期化
    Wire.begin(32, 33);
    if (!bme.begin()) {
        M5.Lcd.fillScreen(RED);
        M5.Lcd.setTextColor(WHITE);
        M5.Lcd.setCursor(10, 20);
        M5.Lcd.println("Sensor Error!");
        Serial.println("Could not find BME688!");
        while (1) delay(100);
    }
    
    // センサー設定
    bme.setTemperatureOversampling(BME680_OS_8X);
    bme.setHumidityOversampling(BME680_OS_2X);
    bme.setPressureOversampling(BME680_OS_4X);
    bme.setIIRFilterSize(BME680_FILTER_SIZE_3);
    bme.setGasHeater(320, 150);
    
    // EEPROMからキャリブレーションデータ読み込み
    EEPROM.begin(EEPROM_SIZE);
    EEPROM.get(EEPROM_H2S_ADDR, baselineH2S);
    EEPROM.get(EEPROM_NH3_ADDR, baselineNH3);
    EEPROM.end();
    
    // 起動時のゼロ校正
    M5.Lcd.println("Zero calibration...");
    delay(1000);
    performZeroCalibration();
    
    // CSV形式のヘッダー出力
    Serial.println("Device_ID,Timestamp,Temperature,Humidity,Pressure,H2S_Resistance,NH3_Resistance,H2S_PPM,NH3_PPM");
    
    // 初期画面表示
    drawMenuScreen();
}

void loop() {
    M5.update();
    
    // MQTT client loop
    mqttClient.loop();
    
    // Check MQTT connection
    if (!mqttClient.connected()) {
        connectMQTT();
    }
    
    if (M5.BtnB.wasPressed()) {
        switch (currentMode) {
            case MODE_SELECT:
                currentMode = (currentMode == MODE_MEASURE_H2S) ? 
                    MODE_MEASURE_NH3 : MODE_MEASURE_H2S;
                drawMenuScreen();
                break;
            
            case MODE_MEASURE_H2S:
            case MODE_MEASURE_NH3:
                currentMode = (currentMode == MODE_MEASURE_H2S) ? 
                    MODE_MEASURE_NH3 : MODE_MEASURE_H2S;
                resetAverageBuffer();
                break;
        }
    }
    
    if (M5.BtnA.wasPressed()) {
        switch (currentMode) {
            case MODE_SELECT:
                currentMode = MODE_MEASURE_H2S;
                resetAverageBuffer();
                break;
            
            case MODE_MEASURE_H2S:
            case MODE_MEASURE_NH3:
                performZeroCalibration();
                break;
        }
    }
    
    if (currentMode == MODE_MEASURE_H2S || currentMode == MODE_MEASURE_NH3) {
        // ヒータープロファイル更新
        unsigned long currentTime = millis();
        if (currentTime - lastProfileSwitch >= PROFILE_SWITCH_TIME) {
            currentProfileStep = (currentProfileStep + 1) % PROFILE_STEPS;
            const uint16_t* currentProfile = 
                (currentMode == MODE_MEASURE_H2S) ? H2S_PROFILE : NH3_PROFILE;
            bme.setGasHeater(currentProfile[currentProfileStep], PROFILE_DURATION);
            lastProfileSwitch = currentTime;
        }
        
        // 測定処理
        if (currentTime - lastMeasurement >= MEASUREMENT_INTERVAL) {
            lastMeasurement = currentTime;
            processMeasurement();
        }
    }
    
    delay(50);
}

void resetAverageBuffer() {
    memset(&avgBuffer, 0, sizeof(avgBuffer));
    avgBuffer.last_update = millis();
}

void drawMenuScreen() {
    M5.Lcd.fillScreen(BLACK);
    M5.Lcd.setTextSize(TEXT_SIZE_NORMAL);
    M5.Lcd.setTextColor(WHITE);
    
    M5.Lcd.setCursor(10, 0);
    M5.Lcd.printf("ID: %s\n", DEVICE_ID);
    
    M5.Lcd.setCursor(10, 20);
    M5.Lcd.println("Gas Select:");
    
    M5.Lcd.setCursor(10, 45);
    M5.Lcd.setTextColor(currentMode == MODE_MEASURE_H2S ? GREEN : WHITE);
    M5.Lcd.print(currentMode == MODE_MEASURE_H2S ? ">H2S" : " H2S");
    
    M5.Lcd.setCursor(10, 65);
    M5.Lcd.setTextColor(currentMode == MODE_MEASURE_NH3 ? GREEN : WHITE);
    M5.Lcd.print(currentMode == MODE_MEASURE_NH3 ? ">NH3" : " NH3");
}
