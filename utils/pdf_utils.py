import os
from pathlib import Path
import re
import shutil
import uuid
import fitz
import requests
from config.logger import GlobalLogger
from mineru.cli.common import convert_pdf_bytes_to_bytes
from mineru.backend.pipeline.pipeline_analyze import (doc_analyze_streaming as pipeline_doc_analyze_streaming)
from mineru.data.data_reader_writer.filebase import (FileBasedDataWriter)
from mineru.backend.pipeline.pipeline_middle_json_mkcontent import (MakeMode, union_make)

class PDFUtils:
    def __init__(self):
        self.logger = GlobalLogger().get_logger(self.__class__)
        self.session = requests.Session()
        self.default_headers = {
            "User-Agent": (
                "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Mobile Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "en-US,en-IN;q=0.9,en;q=0.8"
        }

    def download_file(self, online_file_path: str):
        self.logger.info(f"Attempting to download file from: {online_file_path}")
        try:
            # First attempt (direct)
            self.logger.info(f"Downloading: {online_file_path}")
            response = self.session.get(
                online_file_path,
                headers={**self.default_headers},
                allow_redirects=True,
                timeout=60
            )
            # Fallback if forbidden (403)
            if response.status_code == 403:
                self.logger.warning(f"403 Forbidden. Retrying with page session: {online_file_path}")
                try:
                    base_url = online_file_path.split("/doi/")[0] + "/"
                    article_page = self.session.get(
                        base_url, headers=self.default_headers, timeout=60, allow_redirects=True
                    )
                    if article_page.status_code == 200:
                        self.logger.info("Fetched article page, retrying PDF download...")
                        response = self.session.get(
                            online_file_path,
                            headers={**self.default_headers, "Referer": base_url},
                            timeout=60,
                            allow_redirects=True
                        )
                except Exception as inner_e:
                    self.logger.error(f"Failed fallback request: {inner_e}")
                    raise Exception(f"Failed to download file after fallback")
            if response.status_code == 200:
                os.makedirs("downloads", exist_ok=True)
                safe_name = os.path.basename(online_file_path).replace("?", "_")
                unique_name = f"{uuid.uuid4().hex}_{safe_name or 'paper.pdf'}"
                local_file_path = os.path.join("downloads", unique_name)
                with open(local_file_path, "wb") as file:
                    file.write(response.content)
                self.logger.info(f"Downloaded successfully: {local_file_path}")
                return local_file_path
            else:
                self.logger.warning(f"Download failed: {response.status_code} for {online_file_path}")
                raise Exception(f"Failed to download file: HTTP {response.status_code}")
        except Exception as e:
            self.logger.error(f"Error downloading file: {e}")
            raise Exception(f"Failed to download file")

    def is_valid_pdf(self, file_path: str) -> bool:
        try:
            if not os.path.exists(file_path) or os.path.getsize(file_path) < 20:
                self.logger.warning("PDF validation failed: file missing or too small.")
                return False
            with open(file_path, "rb") as f:
                header = f.read(8)
                if b"%PDF-" not in header:
                    self.logger.warning("PDF validation failed: missing PDF header.")
                    return False
            try:
                doc = fitz.open(file_path)
            except Exception:
                self.logger.warning("PDF validation failed: PyMuPDF could not open file.")
                return False
            if doc.page_count == 0:
                self.logger.warning("PDF validation failed: zero pages.")
                doc.close()
                return False
            try:
                _ = doc.load_page(0).get_text("text")
            except Exception:
                self.logger.warning("PDF validation failed: cannot read page content.")
                doc.close()
                return False
            doc.close()
            return True
        except Exception as e:
            self.logger.error(f"Unexpected PDF validation error: {e}")
            return False

    def write_file(self, path: str, data: str):
        for method in ['utf-8', 'ascii']:
            try:
                bit_data = data.encode(encoding=method, errors='replace')
                with open(path, 'wb') as f:
                    f.write(bit_data)
            except:
                continue

    def pdf_to_markdown(self, online_file_path: str) -> str:
        local_file_path = self.download_file(online_file_path)
        if not local_file_path:
            self.logger.warning("Failed to download PDF.")
            raise Exception(f"Failed to download PDF")
        if not self.is_valid_pdf(local_file_path):
            self.logger.warning("Downloaded file is not a valid PDF.")
            if os.path.exists(local_file_path):
                os.remove(local_file_path)
            raise Exception(f"Downloaded file is not a valid PDF")
        pdf_path = Path(local_file_path)
        output_dir = Path(pdf_path.stem)
        md_output_path = output_dir.with_suffix(".md")
        output_dir.mkdir(exist_ok=True)
        image_dir = output_dir / "images"
        image_dir.mkdir(exist_ok=True)
        pdf_bytes = convert_pdf_bytes_to_bytes(pdf_path.read_bytes())
        image_writer = FileBasedDataWriter(str(image_dir))
        md_content = None
        try:
            def on_doc_ready(doc_index, model_list, middle_json, ocr_enable):
                nonlocal md_content
                md_content = union_make(
                    middle_json["pdf_info"],
                    MakeMode.MM_MD,
                    image_dir.name
                )
                md_content = re.sub(
                    r'!\[[^\]]*\]\(images/[^)]+\)',
                    '',
                    md_content
                )
                md_content = re.sub(
                    r'\n{3,}',
                    '\n',
                    md_content
                )
                self.write_file(md_output_path, md_content)
                self.logger.info(
                    f"Document {doc_index} is ready, the markdown content has been generated"
                )
            pipeline_doc_analyze_streaming(
                pdf_bytes_list=[pdf_bytes],
                image_writer_list=[image_writer],
                lang_list=["ch"],
                on_doc_ready=on_doc_ready,
                parse_method="auto",
                formula_enable=True,
                table_enable=True,
                client_side_output_generation=False,
            )
            md_content = md_content.encode("utf-8", "replace").decode("utf-8")
            return md_content
        finally:
            if os.path.exists(local_file_path):
                os.remove(local_file_path)
            if output_dir.exists():
                shutil.rmtree(output_dir, ignore_errors=True)
            if md_output_path.exists():
                md_output_path.unlink(missing_ok=True)
