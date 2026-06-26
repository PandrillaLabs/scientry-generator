import subprocess
import sys
from collect_dois.doi_collector import DoiCollector
import gradio as gr
import nltk

from config.logger import GlobalLogger


class ScientryCollector:
    def __init__(self):
        self.logger = GlobalLogger().get_logger(self.__class__)
        self.doi_collector = DoiCollector()

    # Chrome Installer
    def installChrome(self):
        silence = {
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL
        }
        subprocess.run(['apt-get', 'update'], **silence)
        subprocess.run(['apt-get', 'install', '-y', 'wget', 'unzip'], **silence)
        subprocess.run(['wget', 'https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb'], **silence)
        subprocess.run(['apt-get', 'install', '-y', './google-chrome-stable_current_amd64.deb'], **silence)
        subprocess.run(['rm', 'google-chrome-stable_current_amd64.deb'], **silence)
        subprocess.run(['apt-get', 'clean'], **silence)
        subprocess.run(['clear'], **silence)

    def collect_dois(self):
        self.doi_collector.collect_dois()

    def load_ui(self):
        with gr.Blocks() as app:
            gr.Markdown("# Scientry Collector Backend")
            with gr.Tabs():
                with gr.TabItem("DOI Collector"):
                    with gr.Column():
                        gr.Markdown("DOI Collector collects DOIs & Categories from various sources.")
                        gr.Button("Start Scientry DOI Collector", variant="primary").click(self.collect_dois)
                # with gr.TabItem("Primary Data Collector"):
                #         gr.Markdown("Primary Data Collector collects Paper's metadata and PDF links from various sources.")
                #         with gr.Column():
                #             gr.Button("Start 10 Scientry Primary Data Collector", variant="primary").click(collect_10_primary_data)
                #             gr.Button("Start 100 Looped Scientry Primary Data Collector", variant="secondary").click(collect_100_primary_data)
                #             gr.Button("Start 1000 Looped Scientry Primary Data Collector", variant="huggingface").click(collect_1000_primary_data)
                # with gr.TabItem("AI Data Generator"):
                #         gr.Markdown("AI Data Generator Generated AI Content for DOI Paper using PDF links from LLM Model.")
                #         with gr.Column():
                #             gr.Button("Start 10 Scientry AI Data Generator", variant="primary").click(generate_10_ai_data)
                #             gr.Button("Start 100 Looped Scientry AI Data Generator", variant="secondary").click(generate_100_ai_data)
                #             gr.Button("Start 1000 Looped Scientry AI Data Generator", variant="huggingface").click(generate_1000_ai_data)
                # with gr.TabItem("Flash Cards & Synopsis Data Generator (Deprecated)"):
                #         gr.Markdown("Flash Cards & Synopsis Data Generator Generated Flash Cards & Synopsis for DOI Paper using PDF links from LLM Model.")
                #         with gr.Column():
                #             gr.Button("Start 10 Scientry FCS Data Generator (Deprecated)", variant="primary").click(generate_10_fcs_data)
                #             gr.Button("Start 100 Looped Scientry FCS Data Generator (Deprecated)", variant="secondary").click(generate_100_fcs_data)
                #             gr.Button("Start 1000 Looped Scientry FCS Data Generator (Deprecated)", variant="huggingface").click(generate_1000_fcs_data)
                # with gr.TabItem("Image Regenerator"):
                #         gr.Markdown("Regenerate Image for given Title, Category and Summary.")
                #         with gr.Row():
                #             with gr.Column():
                #                 doi_id_input = gr.Textbox(label="DOI ID", lines=2, placeholder="10.1234/abcd.efgh.ijkl", max_lines=2)
                #                 title_input = gr.Textbox(label="Paper Title", lines=2, placeholder="An Example Paper Title", max_lines=2)
                #                 category_input = gr.Textbox(label="Paper Category", lines=2, placeholder="Computer Science, IT,...", max_lines=2)
                #                 summary_input = gr.Textbox(label="Paper Summary", lines=4, placeholder="This paper discusses...", max_lines=4)
                #             output_image = gr.Image(label="Generated Image", type="filepath")
                #             image_url = gr.Textbox(label="Image URL", lines=2, placeholder="Image URL", max_lines=2)
                #         gr.Button("Generate Image", variant="primary").click(
                #             generate_image,
                #             inputs=[doi_id_input, title_input, category_input, summary_input],
                #             outputs=[output_image, image_url]
                #         )
        return app

if __name__ == "__main__":
    sc = ScientryCollector()
    if sys.platform != 'win32':
        sc.installChrome()
    nltk.download('punkt', quiet=True)
    nltk.download('punkt_tab', quiet=True)
    sc.load_ui().queue(default_concurrency_limit=1).launch(server_name="0.0.0.0", server_port=7860)