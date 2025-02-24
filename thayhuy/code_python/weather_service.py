import requests
import logging
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Thiết lập logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class WeatherService:
    def __init__(self, api_key):
        """
        Khởi tạo Weather Service với OpenWeatherMap API key

        Parameters:
        api_key (str): OpenWeatherMap API key
        """
        self.api_key = api_key
        self.base_url = "https://api.openweathermap.org/data/2.5/weather"

        # Dictionary chứa thông tin các thành phố
        self.cities = {
            "thai_nguyen": {"name": "Thái Nguyên", "lat": "21.5942", "lon": "105.8432"},
            "hanoi": {"name": "Hà Nội", "lat": "21.0285", "lon": "105.8542"},
            "ho_chi_minh": {"name": "Hồ Chí Minh", "lat": "10.8231", "lon": "106.6297"},
            "da_nang": {"name": "Đà Nẵng", "lat": "16.0544", "lon": "108.2022"},
            "hue": {"name": "Huế", "lat": "16.4637", "lon": "107.5909"},
            "nha_trang": {"name": "Nha Trang", "lat": "12.2388", "lon": "109.1967"},
            "can_tho": {"name": "Cần Thơ", "lat": "10.0362", "lon": "105.7884"},
            "hai_phong": {"name": "Hải Phòng", "lat": "20.8449", "lon": "106.6881"}
        }
        logger.info("WeatherService đã được khởi tạo")

    def get_available_cities(self):
        """
        Trả về danh sách các thành phố có sẵn

        Returns:
        dict: Dictionary chứa key và tên các thành phố
        """
        return {key: city["name"] for key, city in self.cities.items()}

    def get_city_weather(self, city_key):
        """
        Lấy dữ liệu thời tiết cho thành phố được chọn

        Parameters:
        city_key (str): Khóa của thành phố (vd: 'thai_nguyen', 'hanoi',...)

        Returns:
        dict: Dữ liệu thời tiết đã được xử lý hoặc None nếu có lỗi
        """
        try:
            if city_key not in self.cities:
                raise ValueError(f"Không tìm thấy thành phố với key: {city_key}")

            city = self.cities[city_key]
            params = {
                'lat': city['lat'],
                'lon': city['lon'],
                'appid': self.api_key,
                'units': 'metric',  # Sử dụng đơn vị đo metric (Celsius)
                'lang': 'vi'  # Ngôn ngữ tiếng Việt
            }

            logger.info(f"Đang lấy dữ liệu thời tiết cho {city['name']}...")
            logger.debug(f"Request params: {params}")

            response = requests.get(self.base_url, params=params)
            response.raise_for_status()

            data = response.json()
            logger.debug(f"Received weather data: {data}")

            processed_data = {
                'city_name': city['name'],
                'temperature': round(data['main']['temp'], 1),
                'humidity': data['main']['humidity'],
                'description': data['weather'][0]['description'],
                'feels_like': round(data['main']['feels_like'], 1),
                'wind_speed': data['wind']['speed'],
                'pressure': data['main']['pressure'],
                'timestamp': datetime.now().strftime('%H:%M:%S %d/%m/%Y')
            }

            logger.info(f"Xử lý dữ liệu thời tiết cho {city['name']} thành công")
            return processed_data

        except requests.exceptions.RequestException as e:
            logger.error(f"Lỗi khi gửi request API: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Lỗi không xác định: {str(e)}")
            return None

    # Giữ lại phương thức cũ để tương thích ngược
    def get_thai_nguyen_weather(self):
        """
        Lấy dữ liệu thời tiết Thái Nguyên từ OpenWeatherMap API

        Returns:
        dict: Dữ liệu thời tiết đã được xử lý hoặc None nếu có lỗi
        """
        return self.get_city_weather('thai_nguyen')


# Lấy API key từ biến môi trường hoặc sử dụng giá trị mặc định
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "99d825cbcba6b47907017374daa43ac4")

if __name__ == "__main__":
    # Test code khi chạy file trực tiếp
    weather_service = WeatherService(OPENWEATHER_API_KEY)

    # In danh sách các thành phố có sẵn
    print("Danh sách các thành phố:")
    for key, name in weather_service.get_available_cities().items():
        print(f"- {key}: {name}")

    # Test lấy thời tiết cho một thành phố
    city_key = "thai_nguyen"  # Có thể thay đổi thành city key khác
    weather_data = weather_service.get_city_weather(city_key)

    if weather_data:
        print(f"\nThời tiết {weather_data['city_name']} hiện tại:")
        print(f"Nhiệt độ: {weather_data['temperature']}°C")
        print(f"Độ ẩm: {weather_data['humidity']}%")
        print(f"Mô tả: {weather_data['description']}")
        print(f"Cảm giác như: {weather_data['feels_like']}°C")
        print(f"Tốc độ gió: {weather_data['wind_speed']} m/s")
        print(f"Áp suất: {weather_data['pressure']} hPa")
        print(f"Thời gian cập nhật: {weather_data['timestamp']}")
    else:
        print("Không thể lấy dữ liệu thời tiết")