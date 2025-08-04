import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.config import Config
from src.scrapers import GoogleSearchLinkedInScraper, CompanyData


class TestLinkedInScraper:

    @pytest.fixture
    def config(self):
        config = Config()
        config.MAX_LINKEDIN_COMPANIES = 3
        config.LINKEDIN_SEARCH_TERMS = ["YC S25"]
        return config
    
    @pytest.fixture
    def scraper(self, config):
        return GoogleSearchLinkedInScraper(config)
    
    def test_scrape_returns_valid_company_data(self, scraper):
        companies = scraper.scrape()
        
        assert isinstance(companies, list)
        
        if companies:
            company = companies[0]
            assert isinstance(company, CompanyData)
            assert isinstance(company.name, str)
            assert len(company.name.strip()) > 0
            assert isinstance(company.website, str)
            assert isinstance(company.description, str)
            assert isinstance(company.yc_page_url, str)
            assert isinstance(company.linkedin_page_url, str)
            assert isinstance(company.has_linkedin_yc_mention, bool)
            
            if company.linkedin_page_url:
                assert 'linkedin.com/company/' in company.linkedin_page_url
    
    def test_clean_company_name(self, scraper):
        assert scraper._clean_company_name("Test Company (YC S25)") == "Test Company"
        assert scraper._clean_company_name("Test Company YC S25") == "Test Company"
        assert scraper._clean_company_name("Test Company") == "Test Company"
        assert scraper._clean_company_name("") == ""
    
    def test_extract_company_name_from_title(self, scraper):
        assert scraper._extract_company_name_from_title("Test Company | LinkedIn") == "Test Company"
        assert scraper._extract_company_name_from_title("Another Company - LinkedIn") == "Another Company"
        assert scraper._extract_company_name_from_title("Simple Company") == "Simple Company"
        assert scraper._extract_company_name_from_title("") == ""
    
    def test_scraper_handles_errors_gracefully(self, scraper):

        companies = scraper.scrape()
        assert isinstance(companies, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])