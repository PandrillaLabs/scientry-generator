import os
import re

import requests
from requests.adapters import HTTPAdapter
from urllib3 import Retry

from config.env_config import EnvConfig
from config.logger import GlobalLogger


class DataSubmitter:
    def __init__(self):
        self.logger = GlobalLogger().get_logger(self.__class__)
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.session.headers.update({"True-Client-IP": EnvConfig.CLIENT_IP})
        self.session.headers.update({"X-Session-ID": EnvConfig.COOKIE_ID})
        adapter = HTTPAdapter(
            pool_connections=128,
            pool_maxsize=128,
            max_retries=Retry(
                total=2,
                backoff_factor=0.2,
                status_forcelist=[429, 500, 502, 503, 504],
            ),
        )
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        self.DOI_REGEX = re.compile(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+", re.IGNORECASE)

    def normalize_doi(self, text: str) -> str | None:
        if not text:
            return None
        text = text.strip()
        text = text.replace("https://doi.org/", "")
        text = text.replace("http://doi.org/", "")
        text = text.replace("doi:", "")
        text = text.split("?")[0]
        text = text.split("#")[0]
        text = text.rstrip(".,;:)]}>\"'")
        match = self.DOI_REGEX.search(text)
        return match.group(0) if match else None

    def submit_dois(self, doi_set: set[str]):
        if not doi_set:
            self.logger.info("No DOIs to submit.")
            return
        cleaned_dois = set()
        for doi in doi_set:
            normalized_doi = self.normalize_doi(doi)
            if normalized_doi:
                cleaned_dois.add(normalized_doi)
        with open("dois.txt", "w") as f:
            for doi in sorted(cleaned_dois):
                f.write(doi + "\n")
        try:
            self.logger.info(f"Submitting {len(cleaned_dois)} DOIs to backend.")
            resp = self.session.post(
                EnvConfig.REQUEST_PAPERS_URL,
                json={"dois": list(cleaned_dois)}
            )
            if resp.ok and resp.json().get("code") == 0:
                self.logger.info(resp.json().get("message") or f"Successfully submitted {len(cleaned_dois)} DOIs.")
            else:
                self.logger.error(resp.json().get("message") or f"Failed to submit DOIs: {resp.json().get('message')}")
        except Exception as e:
            message = str(e)
            self.logger.error(f"Unexpected error occurred while submitting DOIs: {message}")