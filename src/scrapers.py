import logging
import time
import re
import json
import random
import html as html_module
from dataclasses import dataclass
from typing import List, Dict, Any
from urllib.parse import quote


import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from streamlit import success

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('scraper.log')
    ]
)
logger = logging.getLogger(__name__)


class RequestLimitsExceeded(Exception):
    pass


@dataclass
class CompanyData:
    name: str
    website: str = ""
    description: str = ""
    yc_page_url: str = ""
    linkedin_page_url: str = ""
    has_linkedin_yc_mention: bool = False

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

class YCScraper(BaseScraper):

    def scrape(self) -> List[CompanyData]:
        companies = []
        driver = None
        
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            
            driver = webdriver.Chrome(options=chrome_options)
            driver.set_page_load_timeout(10)
            
            if self.config.YC_BATCH_FILTER:
                url = f"{self.config.YC_BASE_URL}?batch={self.config.YC_BATCH_FILTER}"
            else:
                url = self.config.YC_BASE_URL
            
            driver.get(url)

            try:
                WebDriverWait(driver, 1).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'a[href*="/companies/"]'))
                )
                logger.info("Found links to company pages")
            except:
                logger.warning("No company links found")

            company_links_elements = self._load_all_companies_links(driver)
            company_links = self._extract_company_links(company_links_elements)
            
            try:
                companies = self._scrape_individual_company_pages(driver, company_links)
            except RequestLimitsExceeded as e:
                logger.warning(f"YC scraping stopped due to request limits: {e}")
            
            logger.info(f"YC scraper completed with {len(companies)} companies")
            return companies

        except Exception as e:
            logger.error(f"YC scraping failed: {e}")
            driver.quit()
            return companies
        finally:
            driver.quit()


    def _load_all_companies_links(self, driver) -> list:
        current_links = []
        try:
            previous_company_count = 0
            stable_count_iterations = 0
            max_scrolls = 20
            
            for scroll_attempt in range(max_scrolls):
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(0.5)
                
                current_soup = BeautifulSoup(driver.page_source, 'html.parser')
                current_links = current_soup.find_all(
                    'a',
                    href=lambda x: x and '/companies/' in x,
                )
                current_company_count = len(current_links)

                if current_company_count > previous_company_count:
                    previous_company_count = current_company_count
                    stable_count_iterations = 0
                else:
                    stable_count_iterations += 1
                
                if stable_count_iterations >= 2:
                    break
            return current_links

        except Exception as e:
            logger.error(f"Error loading companies page: {e}")


    def _extract_company_links(self, link_elements) -> List[str]:
        company_links = []
        for link in link_elements:
            href = link.get('href', '')
            if href.startswith('/companies/'):
                full_url = f"https://www.ycombinator.com{href}"
                if full_url not in company_links:
                    company_links.append(full_url)
        return company_links
    

    def _scrape_individual_company_pages(self, driver, company_links: List[str]) -> List[CompanyData]:
        companies = []
        companies_counter = 0

        for company_url in company_links:
            try:
                company = self._scrape_single_company_with_retry(driver, company_url)
                if company:
                    companies.append(company)
                time.sleep(random.uniform(0.3, 1.3))
                companies_counter += 1
                if companies_counter == 10:
                    time.sleep(random.uniform(0.2, 1.5))
                    companies_counter = 0

            except RequestLimitsExceeded:
                logger.warning(f"Request limits exceeded. Stopping with {len(companies)} companies collected ")
                break

        logger.info("Finished scraping individual company pages")
        return companies
    
    def _scrape_single_company_with_retry(self, driver, company_url: str) -> CompanyData | None:
        try:
            driver.get(company_url)

            try:
                WebDriverWait(driver, 1).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, '[data-page*="ShowPage"]'))
                )
            except:
                logger.warning(f"React components may not have loaded for {company_url}")
                time.sleep(2)

            html_content = driver.page_source
            body_string = html_content[html_content.find('<body'):html_content.find('</body>') + 7]

            company = self._extract_company_from_page(body_string, company_url)
            if company:
                return company
            else:
                logger.warning(f"No company data extracted from {company_url}")
                return None

        except Exception as e:
            if ("Connection refused" in str(e) or
                "HTTPConnectionPool" in str(e) or
                "Max retries exceeded" in str(e) or
                "NewConnectionError" in str(e) or
                "timeout" in str(e).lower()):

                logger.error(f"Request limits or connection issues detected: {e}")
                raise RequestLimitsExceeded(f"Request limits exceeded while processing {company_url}: {e}")
            else:
                time.sleep(1)

        return None

    def _extract_company_from_page(self, content: str, company_url: str) -> CompanyData | None:
        try:
            data_page_pattern = r'data-page="([^"]*(?:\\.[^"]*)*)"'
            match = re.search(data_page_pattern, content)

            if not match:
                logger.info(f"No data-page attribute found in {company_url}")
                return None

            escaped_json = match.group(1)
            data_page = html_module.unescape(escaped_json)

            if 'ShowPage' in data_page and 'company' in data_page.lower():
                try:
                    company_data_json = json.loads(data_page)
                    company_json_props = company_data_json.get('props', {})
                    if 'company' in company_json_props and isinstance(company_json_props['company'], dict):
                        company_data = company_json_props.get('company')
                        return self._create_company_from_data(company_data)

                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error from {company_url}: {e}")
                    return None

        except Exception as e:
            logger.error(f"Error processing React element from {company_url}: {e}")
            return None


    def _create_company_from_data(self, data: Dict[str, Any]) -> CompanyData | None:
        try:
            name = data.get('name', '').strip()
            if not name:
                return None
            
            website = data.get('website', '').strip()
            description = data.get('one_liner', data.get('long_description', '')).strip()
            slug = data.get('slug', '')
            yc_page_url = f"https://www.ycombinator.com/companies/{slug}" if slug else ""
            
            return CompanyData(
                name=name,
                website=website,
                description=description,
                yc_page_url=yc_page_url,
                linkedin_page_url="",
                has_linkedin_yc_mention=False
            )
            
        except Exception as e:
            logger.warning(f"Error creating company from data: {e}")
            return None

class GoogleSearchLinkedInScraper(BaseScraper):

    def scrape(self) -> List[CompanyData]:
        companies = []

        logger.info(f"Scraping Google Search LinkedIn Scraper")
        
        try:
            for term in self.config.LINKEDIN_SEARCH_TERMS:
                try:
                    logger.info(f"Searching Google for LinkedIn companies with: {term}")
                    term_companies = self._search_companies_with_google_api(term)
                    companies.extend(term_companies)
                    time.sleep(1)
                except Exception as e:
                    logger.error(f"Error searching for term '{term}': {e}")
                    continue
            
            seen_names = set()
            deduplicated = []
            for company in companies:
                name_key = company.name.lower()
                if name_key not in seen_names:
                    seen_names.add(name_key)
                    deduplicated.append(company)
            
            logger.info(f"LinkedIn scraper found {len(deduplicated)} unique companies")
            return deduplicated[:self.config.MAX_LINKEDIN_COMPANIES]
            
        except Exception as e:
            logger.error(f"LinkedIn scraping failed: {e}")
            return []
    
    def _search_companies_with_google_api(self, search_term: str) -> List[CompanyData]:
        companies = []
        
        try:
            query = f'site:linkedin.com/company "({search_term})"'

            for start in range(1, 92, 10):
                try:
                    api_url = (
                        f"https://www.googleapis.com/customsearch/v1"
                        f"?key={self.config.GOOGLE_API_KEY}"
                        f"&cx={self.config.GOOGLE_SEARCH_ENGINE_ID}"
                        f"&q={quote(query)}"
                        f"&start={start}"
                    )
                    
                    search_api_response = self.session.get(api_url, timeout=self.config.TIMEOUT_SECONDS)
                    search_api_response.raise_for_status()
                    response_data = search_api_response.json()
                    page_companies = self._extract_companies_from_api_response(response_data)
                    
                    if page_companies:
                        companies.extend(page_companies)
                    else:
                        if start > 1:
                            break

                    time.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"Error on Google API page {(start-1)//10 + 1}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error in Google API search: {e}")
        
        return companies
    
    def _extract_companies_from_api_response(self, data: dict) -> List[CompanyData]:
        companies = []
        
        try:
            items = data.get('items', [])
            
            for item in items:
                try:
                    title = item.get('title', '')
                    link = item.get('link', '')
                    snippet = item.get('snippet', '')
                    
                    if 'linkedin.com/company/' not in link:
                        continue
                    
                    company_name = self._extract_company_name_from_title(title)
                    
                    if company_name and link:
                        clean_name = self._clean_company_name(company_name)
                        
                        company = CompanyData(
                            name=clean_name,
                            website="",
                            description=snippet[:200] if snippet else "",
                            yc_page_url="",
                            linkedin_page_url=link,
                            has_linkedin_yc_mention=True
                        )
                        
                        companies.append(company)
                        logger.debug(f"Found LinkedIn company: {clean_name} -> {link}")
                
                except Exception as e:
                    logger.warning(f"Error processing API result: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Error extracting companies from API response: {e}")
        
        return companies
    
    def _extract_company_name_from_title(self, title: str) -> str:
        if not title:
            return ""
        try:
            title = title.strip()
            
            separators = [' | LinkedIn', ' - LinkedIn', ' | ', ' - ', ' on LinkedIn']
            
            for separator in separators:
                if separator in title:
                    company_name = title.split(separator)[0].strip()
                    if company_name:
                        return company_name
            
            if title.endswith(' LinkedIn'):
                title = title[:-9].strip()
            elif title.endswith('LinkedIn'):
                title = title[:-8].strip()
            
            return title
            
        except Exception as e:
            logger.warning(f"Error extracting company name from title '{title}': {e}")
            return ""
    
    def _clean_company_name(self, name: str) -> str:
        import re
        patterns = [
            r'\s*\(YC S25\)\s*',
            r'\s*\(Y Combinator S25\)\s*',
            r'\s*\(YCombinator S25\)\s*',
            r'\s*YC S25\s*',
            r'\s*Y Combinator S25\s*',
            r'\s*YCombinator S25\s*'
        ]
        
        cleaned_name = name
        for pattern in patterns:
            cleaned_name = re.sub(pattern, '', cleaned_name, flags=re.IGNORECASE)
        
        return cleaned_name.strip()