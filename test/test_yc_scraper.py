import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.config import Config
from src.scrapers import YCScraper, CompanyData


class TestYCScraper:

    @pytest.fixture
    def config(self):
        config = Config()
        config.MAX_YC_COMPANIES = 5
        return config
    
    @pytest.fixture
    def scraper(self, config):
        return YCScraper(config)
    
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
            
            if company.yc_page_url:
                assert 'ycombinator.com/companies/' in company.yc_page_url
    
    def test_create_company_from_data(self, scraper):
        data = {
            'name': 'Test Company',
            'website': 'https://testcompany.com',
            'one_liner': 'A test company',
            'slug': 'test-company'
        }
        
        company = scraper._create_company_from_data(data)
        
        assert company is not None
        assert company.name == 'Test Company'
        assert company.website == 'https://testcompany.com'
        assert company.description == 'A test company'
        assert company.yc_page_url == 'https://www.ycombinator.com/companies/test-company'
        
        company_no_name = scraper._create_company_from_data({'website': 'test.com'})
        assert company_no_name is None
    
    def test_scraper_handles_errors_gracefully(self, scraper):
        companies = scraper.scrape()
        assert isinstance(companies, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])