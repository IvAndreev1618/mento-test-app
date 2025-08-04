import streamlit as st
import pandas as pd
import logging
from datetime import datetime
import time
from typing import List
from src.config import Config
from src.scrapers import CompanyData, YCScraper, GoogleSearchLinkedInScraper

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log')
    ]
)
logger = logging.getLogger(__name__)

class DataProcessor:

    def process_companies(self, yc_companies: List[CompanyData], linkedin_companies: List[CompanyData]) -> List[CompanyData]:
        cleaned_yc = self._clean_companies(yc_companies)
        cleaned_linkedin = self._clean_companies(linkedin_companies)
        merged_companies = self._merge_yc_and_linkedin_data(cleaned_yc, cleaned_linkedin)
        
        return merged_companies
    
    def _clean_companies(self, companies: List[CompanyData]) -> List[CompanyData]:
        cleaned = []
        for company in companies:
            if company.name and len(company.name.strip()) > 1:
                company.name = company.name.strip()
                company.description = company.description.strip() if company.description else ""
                company.website = self._normalize_url(company.website)
                company.yc_page_url = self._normalize_url(company.yc_page_url)
                company.linkedin_page_url = self._normalize_url(company.linkedin_page_url)
                cleaned.append(company)
        return cleaned
    
    def _merge_yc_and_linkedin_data(self, yc_companies: List[CompanyData], linkedin_companies: List[CompanyData]) -> List[CompanyData]:
        merged = []
        
        linkedin_by_name = {self._normalize_company_name(c.name): c for c in linkedin_companies}
        
        logger.info(f"Merging data: {len(yc_companies)} YC companies, {len(linkedin_companies)} LinkedIn companies")
        
        for yc_company in yc_companies:
            normalized_name = self._normalize_company_name(yc_company.name)
            
            linkedin_match = linkedin_by_name.get(normalized_name)
            
            if linkedin_match and linkedin_match.linkedin_page_url:
                yc_company.linkedin_page_url = linkedin_match.linkedin_page_url
                yc_company.has_linkedin_yc_mention = linkedin_match.has_linkedin_yc_mention
                logger.info(f"Merged LinkedIn URL for YC company: {yc_company.name}")

            merged.append(yc_company)
        
        yc_names = set(self._normalize_company_name(c.name) for c in yc_companies)
        
        for linkedin_company in linkedin_companies:
            normalized_name = self._normalize_company_name(linkedin_company.name)
            
            if normalized_name not in yc_names:
                merged.append(linkedin_company)
                logger.info(f"Added LinkedIn-only company: {linkedin_company.name}")
        
        logger.info(f"Merge complete: {len(merged)} total companies")
        return merged
    
    def _normalize_company_name(self, name: str) -> str:
        if not name:
            return ""
        
        normalized = name.lower().strip()
        
        suffixes = [' inc', ' inc.', ' llc', ' ltd', ' ltd.', ' corp', ' corp.', ' co', ' co.']
        for suffix in suffixes:
            if normalized.endswith(suffix):
                normalized = normalized[:-len(suffix)].strip()
        
        import re
        normalized = re.sub(r'[^\w\s]', '', normalized)
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized
    
    def _normalize_url(self, url: str) -> str:
        if not url:
            return ""
        url = url.strip()
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        return url.rstrip('/')

class Dashboard:
    def __init__(self, companies: List[CompanyData]):
        self.companies = companies
    
    def render(self):
        st.title("YC S25 Company Parser")
        st.markdown("**Parser for Y Combinator S25 batch**")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Companies", len(self.companies))
        
        with col2:
            linkedin_mentions = len([c for c in self.companies if c.has_linkedin_yc_mention])
            st.metric("LinkedIn YC Mentions", linkedin_mentions)
        
        with col3:
            percentage = round((linkedin_mentions / max(len(self.companies), 1)) * 100, 1)
            st.metric("LinkedIn Mention %", f"{percentage}%")
        
        search_term = st.text_input("Search Companies", placeholder="Enter company name or description...")
        
        filtered_companies = self.companies
        if search_term:
            filtered_companies = [
                c for c in self.companies 
                if search_term.lower() in c.name.lower() or 
                   search_term.lower() in c.description.lower()
            ]
        
        if filtered_companies:
            st.subheader(f"Company Data ({len(filtered_companies)} companies)")
            
            df_data = []
            for company in filtered_companies:
                df_data.append({
                    "YC Company Name": company.name,
                    "Website": company.website,
                    "Description": company.description[:150] + "..." if len(company.description) > 150 else company.description,
                    "YC Page Link": company.yc_page_url,
                    "LinkedIn Page Link": company.linkedin_page_url,
                    "YC S25 Mentioned on LinkedIn": "Yes" if company.has_linkedin_yc_mention else "No"
                })
            
            df = pd.DataFrame(df_data)
            
            st.dataframe(
                df,
                use_container_width=True,
                column_config={
                    "Website": st.column_config.LinkColumn("Website"),
                    "YC Page Link": st.column_config.LinkColumn("YC Page Link"),
                    "LinkedIn Page Link": st.column_config.LinkColumn("LinkedIn Page Link")
                },
                hide_index=True
            )
            
            st.subheader("Export Data")
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("Download CSV"):
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="Download CSV",
                        data=csv,
                        file_name=f"yc_s25_companies_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
            
            with col2:
                if st.button("Download JSON"):
                    import json
                    json_data = json.dumps(df_data, indent=2)
                    st.download_button(
                        label="Download JSON",
                        data=json_data,
                        file_name=f"yc_s25_companies_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json"
                    )
        else:
            st.info("No companies found matching your search criteria.")

@st.cache_data(ttl=3600)
def scrape_companies() -> List[CompanyData]:
    config = Config()
    processor = DataProcessor()
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        status_text.text("Scraping YC Directory...")
        progress_bar.progress(20)
        
        yc_scraper = YCScraper(config)
        yc_companies = yc_scraper.scrape()
        
        status_text.text(f"YC Directory: {len(yc_companies)} companies found")
        progress_bar.progress(50)
        
        status_text.text("Scraping Google for LinkedIn...")
        progress_bar.progress(70)
        
        linkedin_scraper = GoogleSearchLinkedInScraper(config)
        linkedin_companies = linkedin_scraper.scrape()
        
        status_text.text(f"LinkedIn: {len(linkedin_companies)} companies found")
        progress_bar.progress(85)
        
        status_text.text("Merging YC and LinkedIn data...")
        merged_companies = processor.process_companies(yc_companies, linkedin_companies)
        
        progress_bar.progress(100)
        status_text.text(f"Found {len(merged_companies)} companies ({len(yc_companies)} from YC, {len(linkedin_companies)} from LinkedIn)")
        
        time.sleep(2)
        progress_bar.empty()
        status_text.empty()
        
        return merged_companies
        
    except Exception as e:
        st.error(f"Scraping failed: {str(e)}")
        progress_bar.empty()
        status_text.empty()
        return []

def main():
    st.set_page_config(
        page_title="YC S25 Company Parser",
        layout="wide"
    )
    
    st.sidebar.title("Controls")
    if st.sidebar.button("Refresh"):
        st.cache_data.clear()
        st.rerun()
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Last Updated:** " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### About")
    st.sidebar.markdown("""
    This app scrapes YC S25 companies from:
    - Y Combinator directory
    - LinkedIn search results
    
    **Data Fields:**
    - YC Company Name
    - Website
    - Description
    - YC Page Link
    - LinkedIn Page Link
    - YC S25 Mentioned on LinkedIn
    """)
    
    companies = scrape_companies()
    dashboard = Dashboard(companies)
    dashboard.render()

if __name__ == "__main__":
    main()