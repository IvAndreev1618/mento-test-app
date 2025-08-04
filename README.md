# YC S25 Company Parser - Simplified Streamlit App

- This is an implementation of YCombinator Summer 2025 (YC S25) companies data parsing
- Initial task was to use linkedin data alongside the data from ycombinator official website
- Due to linkedin restrictions towards data parsing and scrapping this implementation uses official Google Search API 
in order to find indexed linkedin data of the companies
- Dashboard is either using combination from both data sources, or from the one that is present

## Workflow

- **Main page**: Streamlit main page starts
- **YCombinator data scrapping**: Scrapping Ycombinator official website to find companies from Summer 2025 batch
- **Google Search requests**: Requesting Google Search API to find linkedin data on YC S25 search term
- **Merging data sources**: Combining data to one dashboard
- **File loading**: Giving user the ability to load csv or json data representation

## Data Fields the app searches for

The app extracts and displays exactly 6 fields:

1. **YC Company Name** - Company name from Y Combinator site
2. **Website** - Company's official website URL
3. **Description** - Company description/tagline
4. **YC Page Link** - Link to company's Y Combinator profile
5. **LinkedIn Page Link** - Link to company's LinkedIn page (if found)
6. **YC S25 Mentioned on LinkedIn** - Flag indicating if "YC S25" is mentioned on LinkedIn

## App Structure

```
mento-test-app/
├── app.py                  # Main Streamlit application
├── src/                    # Source code package
│   ├── __init__.py         # Package initialization
│   ├── base_scraper.py     #
│   ├── config.py           # Configuration settings
│   ├── exceptions.py       # Custom exceptions
│   ├── google_scrapper.py  # Google Search Linkedin scrapers
│   ├── models.py           # Models 
│   └── yc_scrapper.py      # YC scraper
├── test/                   # Test package
│   ├── __init__.py         # Test package initialization
│   ├── test_yc_scraper.py      # YC scraper integration tests
│   └── test_linkedin_scraper.py # Google Search Linkedin scraper integration tests
├── requirements.txt    # Python dependencies
└── README.md          # This file
```

This project is for demonstration purpose only. Ensure compliance with terms of service of scraped websites in case
of any production related usage