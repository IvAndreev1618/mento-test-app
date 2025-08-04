import time
from typing import List
from urllib.parse import quote

from src.models import CompanyData
from src.base_scraper import logger, BaseScraper

class GoogleSearchLinkedInScraper(BaseScraper):

    def scrape(self) -> List[CompanyData]:
        companies = []

        try:
            for term in self.config.LINKEDIN_SEARCH_TERMS:
                try:
                    logger.debug(f"Searching Google for LinkedIn companies with: {term}")
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
                    logger.error(f"Error reading Google API search batch {(start - 1) // 10 + 1}: {e}")
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