import logging
import time
import requests
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('scraper.log')
    ]
)
logger = logging.getLogger(__name__)


class BaseScraper:
    def __init__(self, config):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': config.USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        })
    
    def get_page(self, url: str, request_delay: int = None) -> BeautifulSoup:
        request_delay = request_delay or self.config.REQUEST_DELAY
        time.sleep(request_delay)
        
        for attempt in range(self.config.MAX_RETRIES):
            try:
                response = self.session.get(url, timeout=self.config.TIMEOUT_SECONDS)
                response.raise_for_status()
                return BeautifulSoup(response.content, 'html.parser')
            except Exception as e:
                if attempt == self.config.MAX_RETRIES - 1:
                    raise e
                time.sleep(2 ** attempt)
    
    def clean_text(self, text: str) -> str:
        if not text:
            return ""
        return ' '.join(text.split()).strip()