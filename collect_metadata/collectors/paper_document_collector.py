import re

import requests
from requests.adapters import HTTPAdapter
from urllib3 import Retry
from bs4 import BeautifulSoup

from config.logger import GlobalLogger
from utils.pdf_utils import PDFUtils

class PaperDocumentCollector:
    def __init__(self):
        self.logger = GlobalLogger().get_logger(self.__class__)
        self.pdf_utils = PDFUtils()
        self.session = requests.Session()
        adapter = HTTPAdapter(
            pool_connections=64,
            pool_maxsize=64,
            max_retries=Retry(
                total=2,
                backoff_factor=0.2,
                status_forcelist=[429, 500, 502, 503, 504],
            ),
        )
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        self.DOI_REGEX = re.compile(
            r"(?<!\w)(10\.\d{4,9}/[-._;()/:A-Za-z0-9]+?)(?=[\"'<>\s]|$)",
            re.IGNORECASE,
        )

    def get_markdown_from_pdf(self, pdf_url: str) -> str | None:
        try:
            markdown_text = self.pdf_utils.pdf_to_markdown(pdf_url)
            return markdown_text
        except Exception as e:
            self.logger.error(f"Error converting PDF to Markdown: {e}")
            return None

    def get_paper_markdown(self, doi_id: str, json_citation: dict, paper_data: dict) -> str | None:
        # ARXIV
        if "arxiv" in doi_id.lower():
            arxiv_id = doi_id.split("/arxiv.")[-1].strip().split("/arXiv.")[-1]
            pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
            markdown_text = self.get_markdown_from_pdf(pdf_url)
            if markdown_text:
                return markdown_text

        # CSL JSON
        if json_citation and json_citation.get("URL", "") != "":
            pdf_url = json_citation.get("URL", "")
            markdown_text = self.get_markdown_from_pdf(pdf_url)
            if markdown_text:
                return markdown_text
            page = self.session.get(pdf_url, timeout=10, allow_redirects=True)
            if page.status_code == 200:
                if "application/pdf" in page.headers.get("Content-Type", ""):
                    markdown_text = self.get_markdown_from_pdf(page.request.url)
                    if markdown_text:
                        return markdown_text
                # HTML PAGE
                html_content = BeautifulSoup(page.text, "lxml")
                meta_tag = html_content.find("meta", attrs={"name": "citation_pdf_url"})
                if meta_tag and meta_tag.get("content"):
                    pdf_url = meta_tag.get("content")
                    markdown_text = self.get_markdown_from_pdf(pdf_url)
                    if markdown_text:
                        return markdown_text

        # OpenAlex
        if paper_data and paper_data.get("best_oa_location", {}).get("pdf_url"):
            pdf_url = paper_data.get("best_oa_location", {}).get("pdf_url")
            markdown_text = self.get_markdown_from_pdf(pdf_url)
            if markdown_text:
                return markdown_text

        # ThirdIon/Libkey
        encoded_url = requests.utils.quote(doi_id, safe="")
        resp = self.session.get(f"https://api.thirdiron.com/v2/articles/doi%3A{encoded_url}", timeout=10)
        if resp.status_code == 200:
            pdf_link = resp.json().get("data", {}).get("attributes", {}).get("fullTextFile") or None
            if pdf_link:
                markdown_text = self.get_markdown_from_pdf(pdf_link)
                if markdown_text:
                    return markdown_text

        # NO PDF FOUND
        self.logger.warning(f"Failed to retrieve PDF for DOI: {doi_id}")
        return None