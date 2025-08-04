class Config:

    YC_BASE_URL = "https://www.ycombinator.com/companies"
    YC_BATCH_FILTER = "Summer%202025"
    LINKEDIN_BASE_URL = "https://www.linkedin.com"
    LINKEDIN_SEARCH_TERMS = ["YC S25", "Y Combinator S25"]

    REQUEST_DELAY = 2
    LINKEDIN_DELAY_SECONDS = 3
    MAX_RETRIES = 3
    TIMEOUT_SECONDS = 30
    
    USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    
    MAX_YC_COMPANIES = 100
    MAX_LINKEDIN_COMPANIES = 100

    GOOGLE_API_KEY = "AIzaSyC6X8Jw5iGdbUFQQ-YHj37JK41p_azhGRI"
    GOOGLE_SEARCH_ENGINE_ID = "113ece03704cb4057"