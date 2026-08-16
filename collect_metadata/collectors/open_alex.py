import requests
from requests.adapters import HTTPAdapter
from urllib3 import Retry

from collect_metadata.collectors.doi_org import DoiOrg
from collect_metadata.collectors.paper_document_collector import PaperDocumentCollector
from config.logger import GlobalLogger
from collect_metadata.metadata_dto import MetadataDto

class OpenAlex:
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
        self.doi_org = DoiOrg()

    def _decompress_abstract(self, compressed_abstract: dict[str, list[int]]) -> str | None:
        if compressed_abstract is None:
            return None
        try:
            if not compressed_abstract:
                return None
            max_pos = max(p for positions in compressed_abstract.values() for p in positions)
            words = [""] * (max_pos + 1)
            for word, positions in compressed_abstract.items():
                for pos in positions:
                    words[pos] = word
            return " ".join(w for w in words if w)
        except Exception as e:
            self.logger.error(f"Error decompressing abstract: {e}")
            return None

    def _get_tags(self, paper_data) -> list[str]:
        primary_topic = paper_data.get("primary_topic", {})
        tags = []
        topic = primary_topic.get("id", "").split("/")[-1]
        if topic:
            tags.append("T" + topic if not topic.startswith("T") else topic)
        sub_field = primary_topic.get("subfield", {}).get("id", "").split("/")[-1]
        if sub_field:
            tags.append("SF" + sub_field)
        domain = primary_topic.get("domain", {}).get("id", "").split("/")[-1]
        if domain:
            tags.append("D" + domain)
        sdgs_list = paper_data.get("sustainable_development_goals", [])
        if sdgs_list:
            sdgs = [sdg.get("id", "").split("/")[-1] for sdg in sdgs_list if sdg.get("id")]
            tags.extend(["SDGS" + sdg for sdg in sdgs])
        return tags

    def get_doi_metadata(self, doi: str, json_metadata: dict, apa_citation: str) -> MetadataDto:
        try:
            response = self.session.get(f"https://api.openalex.org/works/doi:{doi}")
            response.raise_for_status()
            paper_data = response.json()
            title = paper_data.get("title") or paper_data.get("display_name") or None
            authors = [author.get("display_name").get("display_name") for author in paper_data.get("authorships", []) if author.get("author") and author.get("author").get("display_name")]
            abstract_text = self._decompress_abstract(paper_data.get("abstract_inverted_index")) or json_metadata.get("abstract") or None
            citation = apa_citation or None
            citation_map = json_metadata or None
            category_id = paper_data.get("primary_topic", {}).get("field", {}).get("id").split("/")[-1] or None
            tag_ids = self._get_tags(paper_data) or []
            source = paper_data.get("best_oa_location", {}).get("source", {})
            journalId = source.get("id").split("/")[-1] or None
            publisherId = source.get("host_organization").split("/")[-1] or None
            published_year = paper_data.get("publication_year") or None
            pdf_url = paper_data.get("best_oa_location", {}).get("pdf_url") or None
            markdown = PaperDocumentCollector().get_paper_markdown(doi, json_metadata, paper_data) or None
            if markdown:
                with open("output.md", "w", encoding="utf-8") as f:
                    f.write(markdown)
            return MetadataDto(
                doiId=doi,
                title=title,
                authors=authors,
                abstractText=abstract_text,
                citation=citation,
                citationMap=citation_map,
                categoryId=category_id,
                tagIds=tag_ids,
                journalId=journalId,
                publisherId=publisherId,
                publishedYear=published_year,
                pdfUrl=pdf_url
            )
        except requests.Timeout as e:
            self.logger.error(f"Timeout occurred while submitting DOIs: {e}")
        except requests.ConnectionError as e:
            self.logger.error(f"Connection error occurred while submitting DOIs: {e}")
        except requests.HTTPError as e:
            self.logger.error(f"HTTP error occurred while submitting DOIs: {e}")
        except requests.RequestException as e:
            self.logger.error(f"Error submitting DOIs: {e}")