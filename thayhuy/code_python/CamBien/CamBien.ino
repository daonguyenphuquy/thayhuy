#include "DHTesp.h"
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include <NTPClient.h>
#include <WiFiUdp.h>
#include <ArduinoJson.h> // Thư viện JSON
#include <DHT.h>

#define SCREEN_WIDTH 128 // OLED display width, in pixels
#define SCREEN_HEIGHT 64 // OLED display height, in pixels
#define OLED_RESET     -1 // Reset pin # (or -1 if sharing Arduino reset pin)
#define SCREEN_ADDRESS 0x3C ///< See datasheet for Address; 0x3D for 128x64, 0x3C for 128x32

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);
DHTesp dht;
float temperature = 0, humidity = 0;

const char* ssid = "IoT";
const char* password = "234567Cn";

// Cấu hình MQTT
const char* mqttServer = "192.168.0.101";
const int mqttPort = 1883;               // Cổng MQTT
const char* mqttTopic = "CamBien"; // Topic để gửi dữ liệu

WiFiClient espClient;
PubSubClient client(espClient);

// Cấu hình NTPClient
WiFiUDP ntpUDP;
NTPClient timeClient(ntpUDP, "pool.ntp.org", 7 * 3600, 60000); // GMT+7 (điều chỉnh múi giờ)

// Hàm kết nối MQTT
void connectMQTT() {
  while (!client.connected()) {
    Serial.print("Đang kết nối tới MQTT...");
    String clientId = "ESP8266Client-";
    clientId += String(random(0xffff), HEX);

    if (client.connect(clientId.c_str())) {
      Serial.println("connected");
      client.subscribe(mqttTopic);
    } else {
      Serial.print("Lỗi!, rc=");
      Serial.print(client.state());
      Serial.println(" thực hiện kết nối lại sau 5s");
      delay(5000);
    }
  }
}

// Hàm chuyển đổi epoch time thành định dạng ngày dd/mm/yyyy
String formatDate(unsigned long epochTime) {
  int days = epochTime / 86400; // Một ngày có 86400 giây
  int year = 1970;

  // Tính năm
  while (days >= 365) {
    if ((year % 4 == 0 && year % 100 != 0) || (year % 400 == 0)) { // Năm nhuận
      if (days >= 366) {
        days -= 366;
        year++;
      } else {
        break;
      }
    } else {
      days -= 365;
      year++;
    }
  }

  // Tính tháng
  int monthDays[] = {31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31};
  if ((year % 4 == 0 && year % 100 != 0) || (year % 400 == 0)) {
    monthDays[1] = 29; // Năm nhuận, tháng 2 có 29 ngày
  }

  int month = 0;
  while (days >= monthDays[month]) {
    days -= monthDays[month];
    month++;
  }
  month++;
  int day = days + 1;

  // Định dạng ngày
  char dateBuffer[11];
  snprintf(dateBuffer, sizeof(dateBuffer), "%02d/%02d/%04d", day, month, year);
  return String(dateBuffer);
}

// Hàm kết nối WiFi
void setupWiFi() {
  delay(10);
  Serial.println();
  Serial.print("Kết nối tới ");
  Serial.println(ssid);

  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.print(".");
  }

  Serial.println("");
  Serial.println("WiFi connected");
  Serial.println("Địa chỉ IP ESP8266: ");
  Serial.println(WiFi.localIP());
}

void setup() {
  Serial.begin(115200);

  setupWiFi();

  client.setServer(mqttServer, mqttPort); // Thiết lập MQTT với địa chỉ IP

  timeClient.begin(); // Bắt đầu lấy thời gian

  if (!display.begin(SSD1306_SWITCHCAPVCC, SCREEN_ADDRESS)) {
    Serial.println(F("SSD1306 allocation failed"));
    for (;;); // Don't proceed, loop forever
  }
  display.display();
  delay(2000); // Pause for 2 seconds

  dht.setup(16, DHTesp::DHT11); // Pin GPIO16
  display.clearDisplay();
}

void loop() {
  // Cập nhật dữ liệu cảm biến
  if (millis() - dht.getMinimumSamplingPeriod() >= 0) {
    temperature = dht.getTemperature();
    humidity = dht.getHumidity();
  }

  // Hiển thị dữ liệu lên OLED
  display.clearDisplay();
  display.setTextSize(2);                     // Normal 1:2 pixel scale
  display.setTextColor(SSD1306_WHITE);        // Draw white text
  display.setCursor(0, 0);                    // Start at top-left corner
  display.print("Temp: ");
  display.print(temperature, 1);
  display.print((char)247);                   // Degree symbol
  display.println("C");

  display.print("Humi: ");
  display.print(humidity, 1);
  display.println("%");

  Serial.print("==> Temperature: ");
  Serial.print(temperature);
  Serial.print(" °C, ");
  Serial.print(" $ Humidity: ");
  Serial.print(humidity);
  Serial.println(" %");

  if (!client.connected()) {
    connectMQTT();
  }
  client.loop();
  // Cập nhật thời gian từ NTP
  timeClient.update();

  // Lấy epoch time
  unsigned long epochTime = timeClient.getEpochTime();

  // Định dạng ngày và giờ
  String formattedDate = formatDate(epochTime);       // Định dạng ngày dd/mm/yyyy
  String time = timeClient.getFormattedTime();        // Định dạng giờ HH:MM:SS
// Gửi dữ liệu qua MQTT mỗi 5 giây
  static unsigned long lastMsg = 0;
  if (millis() - lastMsg > 5000) {
    lastMsg = millis();
    String message = "{\"date\":\"" + formattedDate + "\",\"time\":\"" + time + "\",\"temperature\":\"" + temperature + "\",\"humidity\":\"" + humidity + "\"}";
    Serial.print("Sending message: ");
    Serial.println(message);
    client.publish(mqttTopic, message.c_str());
  }

  display.display();
  delay(500); // Giảm tải CPU và tránh nhấp nháy màn hình
}