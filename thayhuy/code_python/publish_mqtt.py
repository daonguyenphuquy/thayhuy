import paho.mqtt.client as mqtt
import time
import logging
import json
from datetime import datetime

# Thiết lập logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Cấu hình MQTT Broker
MQTT_BROKER = "192.168.0.101"
MQTT_PORT = 1883
MQTT_TOPIC = "CamBien"

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("Kết nối MQTT thành công!")
    else:
        logger.error(f"Kết nối MQTT thất bại với mã lỗi {rc}")

def on_publish(client, userdata, mid):
    logger.info(f"Message {mid} đã được publish thành công")

def publish_sensor_data():
    try:
        client = mqtt.Client()
        client.on_connect = on_connect
        client.on_publish = on_publish

        logger.info(f"Đang kết nối tới MQTT broker {MQTT_BROKER}")
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()

        while True:
            # Lấy thời gian hiện tại
            now = datetime.now()
            date_str = now.strftime("%d/%m/%Y")
            time_str = now.strftime("%H:%M:%S")

            # Tạo dữ liệu theo định dạng của ESP8266
            data = {
                "date": date_str,
                "time": time_str,
                "temperature": "25.5",  # Thay bằng giá trị thực từ cảm biến của bạn
                "humidity": "65.0"      # Thay bằng giá trị thực từ cảm biến của bạn
            }

            message = json.dumps(data)
            logger.info(f"Đang gửi dữ liệu: {message}")
            client.publish(MQTT_TOPIC, message)
            time.sleep(5)  # Đợi 5 giây như ESP8266

    except Exception as e:
        logger.error(f"Lỗi khi gửi MQTT: {e}")
        if 'client' in locals():
            client.disconnect()
            client.loop_stop()

if __name__ == "__main__":
    publish_sensor_data()