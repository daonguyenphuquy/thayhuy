# app.py
from flask import Flask, render_template, jsonify, request
import paho.mqtt.client as mqtt
import json
import logging
from datetime import datetime
from weather_service import WeatherService
from config import OPENWEATHER_API_KEY

# Thiết lập logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# MQTT Configuration
MQTT_BROKER = "192.168.0.101"
MQTT_PORT = 1883
MQTT_TOPIC_CONTROL = "CamBien/control"  # Topic để gửi lệnh điều khiển đến ESP
MQTT_TOPIC_SENSOR = "CamBien"          # Topic nhận dữ liệu từ ESP

class SensorData:
    def __init__(self):
        self.soil_moisture = 0
        self.temperature = 0
        self.target_humidity = 40
        self.target_temperature = 25
        self.historical_data = []
        self.last_update = None

        # Khởi tạo MQTT client
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_message = self.on_message
        self.mqtt_client.on_connect = self.on_connect
        try:
            self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
            self.mqtt_client.subscribe(MQTT_TOPIC_SENSOR)
            self.mqtt_client.loop_start()
            logger.info("MQTT client đã được khởi tạo")
        except Exception as e:
            logger.error(f"Lỗi khi khởi tạo MQTT: {e}")

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("Đã kết nối với MQTT Broker!")
            client.subscribe(MQTT_TOPIC_SENSOR)
        else:
            logger.error(f"Kết nối thất bại, mã lỗi: {rc}")

    def on_message(self, client, userdata, message):
        try:
            # Giải mã dữ liệu JSON từ ESP8266
            data = json.loads(message.payload.decode())
            logger.info(f"Nhận được dữ liệu: {data}")

            # Cập nhật giá trị từ cảm biến
            self.temperature = float(data.get('temperature', 0))
            self.soil_moisture = float(data.get('humidity', 0))  # ESP gửi độ ẩm trong trường 'humidity'
            self.last_update = datetime.now()

            # Lưu vào lịch sử
            timestamp = datetime.now().strftime('%H:%M:%S')
            self.historical_data.append({
                'time': timestamp,
                'soil_moisture': self.soil_moisture,
                'temperature': self.temperature,
                'target_humidity': self.target_humidity,
                'target_temperature': self.target_temperature
            })

            # Giữ 50 điểm dữ liệu gần nhất
            if len(self.historical_data) > 50:
                self.historical_data.pop(0)

            # Kiểm tra và điều khiển độ ẩm
            self.check_and_control_moisture()

        except Exception as e:
            logger.error(f"Lỗi khi xử lý dữ liệu MQTT: {e}")

    def check_and_control_moisture(self):
        """Kiểm tra và gửi tín hiệu điều khiển đến ESP"""
        try:
            if self.soil_moisture < self.target_humidity:
                logger.info(f"Độ ẩm ({self.soil_moisture}%) thấp hơn ngưỡng ({self.target_humidity}%), BẬT bơm")
                self.publish_control(1)  # Bật bơm
            else:
                logger.info(f"Độ ẩm ({self.soil_moisture}%) cao hơn hoặc bằng ngưỡng ({self.target_humidity}%), TẮT bơm")
                self.publish_control(0)  # Tắt bơm
        except Exception as e:
            logger.error(f"Lỗi trong check_and_control_moisture: {e}")

    def publish_control(self, value):
        """Gửi lệnh điều khiển đến ESP"""
        try:
            self.mqtt_client.publish(MQTT_TOPIC_CONTROL, str(value))
            logger.info(f"Đã gửi lệnh điều khiển: {value}")
        except Exception as e:
            logger.error(f"Lỗi khi gửi lệnh điều khiển: {e}")

# Khởi tạo đối tượng sensor
sensor = SensorData()

@app.route('/update_sensor', methods=['POST'])
def update_sensor():
    try:
        data = request.get_json()
        if 'target_humidity' in data:
            sensor.target_humidity = float(data['target_humidity'])
            sensor.check_and_control_moisture()
        if 'target_temperature' in data:
            sensor.target_temperature = float(data['target_temperature'])

        return jsonify({
            'status': 'success',
            'soil_moisture': sensor.soil_moisture,
            'temperature': sensor.temperature,
            'target_humidity': sensor.target_humidity,
            'target_temperature': sensor.target_temperature
        })
    except Exception as e:
        logger.error(f"Lỗi trong update_sensor: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/get_sensor_data')
def get_sensor_data():
    return jsonify({
        'status': 'success',
        'soil_moisture': sensor.soil_moisture,
        'temperature': sensor.temperature,
        'target_humidity': sensor.target_humidity,
        'target_temperature': sensor.target_temperature,
        'historical_data': sensor.historical_data
    })

# Route mới để lấy danh sách các thành phố
@app.route('/api/cities')
def get_cities():
    try:
        weather_service = WeatherService(OPENWEATHER_API_KEY)
        cities = weather_service.get_available_cities()
        return jsonify({
            'status': 'success',
            'data': cities
        })
    except Exception as e:
        logger.error(f"Lỗi khi lấy danh sách thành phố: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Không thể lấy danh sách thành phố'
        }), 500

# Route mới để lấy thời tiết cho một thành phố cụ thể
@app.route('/api/weather/<city_key>')
def get_city_weather(city_key):
    try:
        weather_service = WeatherService(OPENWEATHER_API_KEY)
        weather_data = weather_service.get_city_weather(city_key)
        if weather_data:
            return jsonify({
                'status': 'success',
                'data': weather_data
            })
        return jsonify({
            'status': 'error',
            'message': 'Không thể lấy dữ liệu thời tiết'
        }), 500
    except Exception as e:
        logger.error(f"Lỗi khi lấy thời tiết cho thành phố {city_key}: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Lỗi khi lấy dữ liệu thời tiết: {str(e)}'
        }), 500

# Giữ lại route cũ để tương thích ngược
@app.route('/api/weather')
def get_weather():
    weather_service = WeatherService(OPENWEATHER_API_KEY)
    weather_data = weather_service.get_thai_nguyen_weather()

    if weather_data:
        return jsonify({
            'status': 'success',
            'data': weather_data
        })

    return jsonify({
        'status': 'error',
        'message': 'Không thể lấy dữ liệu thời tiết'
    }), 500

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)