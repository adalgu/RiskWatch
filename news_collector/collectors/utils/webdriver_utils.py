"""
WebDriver initialization and setup utilities
"""

import logging
import os
import platform
import shutil
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException, TimeoutException
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

# Configure logging at module level
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class WebDriverUtils:
    def __init__(self, headless=True, proxy=None, user_agent=None, use_remote=True, remote_url=None):
        self.driver = None
        self.headless = headless
        self.proxy = proxy
        self.user_agent = user_agent
        self.use_remote = use_remote
        
        # Get remote URL from environment variable or parameter
        self.remote_url = (
            remote_url or 
            os.getenv('SELENIUM_HUB_URL') or 
            'http://localhost:4444/wd/hub'
        )
        
        # Override the remote URL if it contains 'selenium-hub' and we're not in Docker
        if 'selenium-hub' in self.remote_url and not os.path.exists('/.dockerenv'):
            self.remote_url = self.remote_url.replace('selenium-hub', 'localhost')
        logger.info(f"Initialized with remote URL: {self.remote_url}")

    def clear_driver_cache(self):
        """웹드라이버 캐시 삭제"""
        cache_path = os.path.expanduser('~/.wdm')
        if os.path.exists(cache_path):
            try:
                shutil.rmtree(cache_path)
                logger.info("웹드라이버 캐시 삭제 완료")
            except Exception as e:
                logger.error(f"캐시 삭제 실패: {str(e)}")

    def get_driver_path(self):
        """시스템 아키텍처에 따른 적절한 드라이버 설정"""
        system = platform.system()
        machine = platform.machine()

        logger.info(f"Operating System: {system}")
        logger.info(f"Machine Architecture: {machine}")

        # 기존 캐시 삭제
        self.clear_driver_cache()

        if system == "Darwin" and machine == "arm64":
            # M1/M2 Mac을 위한 설정
            os.environ['WDM_ARCHITECTURE'] = 'arm64'
            driver_path = ChromeDriverManager().install()
            os.chmod(driver_path, 0o755)  # 실행 권한 부여
            return driver_path
        else:
            return ChromeDriverManager().install()

    def get_chrome_options(self):
        """Chrome 옵션 설정"""
        chrome_options = Options()

        # 기본 옵션 설정
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")

        # 크래시 방지 옵션 추가
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-infobars")
        chrome_options.add_argument("--disable-popup-blocking")

        # 추가 안정성 옵션
        chrome_options.add_argument('--disable-web-security')
        chrome_options.add_argument('--disable-client-side-phishing-detection')
        chrome_options.add_argument('--disable-notifications')
        chrome_options.add_argument('--disable-setuid-sandbox')
        chrome_options.add_argument('--force-device-scale-factor=1')

        # 메모리 관련 옵션
        chrome_options.add_argument('--disable-accelerated-2d-canvas')
        chrome_options.add_argument('--disable-accelerated-jpeg-decoding')
        chrome_options.add_argument('--disable-accelerated-mjpeg-decode')
        chrome_options.add_argument('--disable-accelerated-video-decode')
        chrome_options.add_argument('--disable-gpu-vsync')
        chrome_options.add_argument('--disable-software-rasterizer')

        # M1/M2 Mac 관련 추가 설정
        if platform.system() == "Darwin" and platform.machine() == "arm64":
            chrome_options.add_argument("--disable-gpu-sandbox")
            chrome_options.add_argument("--ignore-certificate-errors")
            chrome_options.binary_location = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

        # User Agent 설정
        if self.user_agent:
            chrome_options.add_argument(f'user-agent={self.user_agent}')
        else:
            chrome_options.add_argument(
                'user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36'
            )

        # Proxy 설정
        if self.proxy:
            chrome_options.add_argument(f'--proxy-server={self.proxy}')

        # 헤드리스 모드 설정
        if self.headless:
            chrome_options.add_argument("--headless=new")

        return chrome_options

    def initialize_remote_driver(self):
        """원격 WebDriver 초기화"""
        try:
            chrome_options = self.get_chrome_options()
            chrome_options.set_capability('acceptInsecureCerts', True)

            logger.info(f"Connecting to Selenium Hub at: {self.remote_url}")
            self.driver = webdriver.Remote(
                command_executor=self.remote_url,
                options=chrome_options
            )
            logger.info("원격 WebDriver 초기화 성공")
            return self.driver

        except Exception as e:
            logger.error(f"원격 WebDriver 초기화 실패: {str(e)}")
            raise

    def initialize_local_driver(self):
        """로컬 WebDriver 초기화"""
        try:
            chrome_options = self.get_chrome_options()
            driver_path = self.get_driver_path()
            service = Service(driver_path)

            self.driver = webdriver.Chrome(
                service=service,
                options=chrome_options
            )
            logger.info("로컬 WebDriver 초기화 성공")
            return self.driver

        except Exception as e:
            logger.error(f"로컬 WebDriver 초기화 실패: {str(e)}")
            raise

    def initialize_driver(self):
        """WebDriver 초기화 및 설정"""
        try:
            if self.use_remote:
                self.driver = self.initialize_remote_driver()
            else:
                self.driver = self.initialize_local_driver()

            self.driver.implicitly_wait(10)
            return self.driver

        except WebDriverException as e:
            logger.error(f"WebDriver 초기화 실패: {str(e)}")
            self.quit_driver()
            raise
        except Exception as e:
            logger.error(f"예상치 못한 오류 발생: {str(e)}")
            self.quit_driver()
            raise

    def wait_for_element(self, by, value, timeout=10):
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return element
        except TimeoutException:
            logger.error(f"요소를 찾을 수 없음: {value}")
            raise

    def quit_driver(self):
        if self.driver:
            try:
                self.driver.quit()
                logger.info("WebDriver 종료됨")
            except Exception as e:
                logger.error(f"WebDriver 종료 중 오류 발생: {str(e)}")


def initialize_driver(proxy: str = None, user_agent: str = None, use_remote: bool = True) -> webdriver.Chrome:
    """Initialize Chrome WebDriver with options"""
    driver_utils = WebDriverUtils(
        headless=True,
        proxy=proxy,
        user_agent=user_agent,
        use_remote=use_remote
    )
    return driver_utils.initialize_driver()
