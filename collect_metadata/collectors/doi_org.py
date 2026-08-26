import requests
from requests.adapters import HTTPAdapter
from urllib3 import Retry
from citeproc import CitationStylesStyle, CitationStylesBibliography, Citation, CitationItem
from citeproc.source.json import CiteProcJSON
from citeproc import formatter

from config.logger import GlobalLogger

class DoiOrg:
    def __init__(self):
        self.logger = GlobalLogger().get_logger(self.__class__)
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

    def get_json_citation(self, doi: str) -> dict:
        try:
            response = self.session.get(f"https://doi.org/{doi}", headers={"Accept": "application/vnd.citationstyles.csl+json;q=1"})
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as e:
            response = e.response
            error_reason = (f"HTTP {response.status_code}: "f"{response.reason or str(e)}") if response else str(e)
            raise Exception(f"Failed to get JSON Citation: {error_reason}")
        except Exception as e:
            self.logger.error(f"Error getting JSON Citation: {e}")
            raise Exception(f"Failed to get JSON Citation")

    def get_apa_citation(self, citation_json: dict) -> str:
        try:
            if "id" not in citation_json:
                citation_json["id"] = citation_json.get("DOI", "ref1")
            bib_source = CiteProcJSON([citation_json])
            style = CitationStylesStyle("apa", validate=False)
            bibliography = CitationStylesBibliography(style, bib_source, formatter.plain)
            bibliography.register(Citation([CitationItem(citation_json["id"])]))
            return str(bibliography.bibliography()[0])
        except Exception as e:
            self.logger.error(f"Error getting apa citation DOIs: {e}")
            raise Exception(f"Failed to get APA Citation")