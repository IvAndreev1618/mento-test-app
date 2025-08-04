from dataclasses import dataclass


@dataclass
class CompanyData:
    name: str
    website: str = ""
    description: str = ""
    yc_page_url: str = ""
    linkedin_page_url: str = ""
    has_linkedin_yc_mention: bool = False