from app import schema
from app.utils.knowledge_tree.web_extraction import WebExtraction
from app.utils.knowledge_tree.creating_knowledge_bot import CreateGraphBot

def fetch_from_web(body: schema.WebExtractionSchema):
    web_extractor = WebExtraction(
        site_url=body.url,
        extracted_sitemap_urls=body.extracted_sitemap_urls,
        extracted_urls=body.extracted_urls,
        urls_content=body.urls_content
    )
    web_extractor.get_all_siteurls()
    web_extractor.url_crawl()
    web_extractor.content_extraction()

def build_tree(body: schema.GraphBotSchema):
    graph_builder = CreateGraphBot(
        urls_content=body.urls_content,
        csv_output=body.csv_output,
        output_pkl=body.output_pkl,
        output_tree=body.output_tree,
        output_flat=body.output_flat
    )
    graph_builder.to_csv()
    graph_builder.to_pickle()
    graph_builder.to_json()