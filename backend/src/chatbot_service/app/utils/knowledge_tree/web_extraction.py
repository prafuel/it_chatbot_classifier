import os
import json
import requests
import trafilatura
from bs4 import BeautifulSoup
from app.common.constant import (
    DEFAULT_HEADERS, SITEMAP_INDEX_SUFFIX, SITEMAP_SUFFIX,
    DEFAULT_SITE_URL, DEFAULT_EXTRACTED_SITEMAP_URLS,
    DEFAULT_EXTRACTED_URLS, DEFAULT_URLS_CONTENT
)
from app.common.messages import LogMessages as Msg

class WebExtraction:
    def __init__(self, site_url, extracted_sitemap_urls, extracted_urls, urls_content):
        self.site_url = site_url.rstrip("/")
        self.EXTRACTED_SITEMAP_URLS = extracted_sitemap_urls
        self.EXTRACTED_URLS = extracted_urls
        self.URLS_CONTENT = urls_content

        # Create directories
        os.makedirs(self.EXTRACTED_URLS, exist_ok=True)
        os.makedirs(self.URLS_CONTENT, exist_ok=True)

    def get_xml(self, url):
        try:
            headers = DEFAULT_HEADERS

            r = requests.get(url, headers=headers, timeout=10)

            if r.status_code != 200:
                raise Exception(Msg.FETCH_XML_FAILED.format(url, r.status_code))

            return BeautifulSoup(r.content, 'lxml') # instead of r.content use its html version
        except Exception as e:
            print(Msg.GET_XML_ERROR.format(url, e))
            raise

    def resolve_sitemap(self):
        try:
            possible_sitemaps = [
                f"{self.site_url}{SITEMAP_INDEX_SUFFIX}",
                f"{self.site_url}{SITEMAP_SUFFIX}"
            ]

            headers = DEFAULT_HEADERS

            for sm in possible_sitemaps:
                try:
                    r = requests.get(sm, headers=headers, timeout=10)
                    if r.status_code == 200 and "<loc>" in r.text:
                        print(Msg.USING_SITEMAP.format(sm))
                        return sm
                except Exception:
                    continue

            raise Exception(Msg.NO_VALID_SITEMAP)
        except Exception as e:
            print(Msg.RESOLVE_SITEMAP_ERROR.format(e))
            raise

    def get_webcontent(self, url):
        try:
            downloaded = trafilatura.fetch_url(url)
            return trafilatura.extract(downloaded)
        except Exception as e:
            print(Msg.GET_WEBCONTENT_ERROR.format(url, e))
            return ""

    def get_all_siteurls(self):
        try:
            sitemap_url = self.resolve_sitemap()
            soup = self.get_xml(url=sitemap_url)

            locs = soup.find_all("loc")

            if not locs:
                raise Exception(Msg.NO_LOC_TAGS)

            urls = [loc.text.strip() for loc in locs]

            # Detect if it's a sitemap index or direct URL sitemap
            if any(url.endswith(".xml") for url in urls):
                # sitemap_index.xml → contains sitemap links
                with open(self.EXTRACTED_SITEMAP_URLS, "w+") as f:
                    for url in urls:
                        f.write(url + "\n")
            else:
                # sitemap.xml → contains actual page URLs
                os.makedirs(self.EXTRACTED_URLS, exist_ok=True)
                with open(os.path.join(self.EXTRACTED_URLS, "urls.txt"), "w") as f:
                    for url in urls:
                        f.write(url + "\n")
        except Exception as e:
            print(Msg.GET_ALL_SITEURLS_ERROR.format(e))
                

    def url_crawl(self):
        try:
            # Case 1: Already have direct URLs (from sitemap.xml)
            direct_file = os.path.join(self.EXTRACTED_URLS, "urls.txt")
            if os.path.exists(direct_file):
                print(Msg.USING_DIRECT_URL_LIST)
                return

            # Case 2: sitemap_index.xml flow
            with open(self.EXTRACTED_SITEMAP_URLS, "r") as f:
                for url in f.readlines():
                    key = str(url.split("/")[-1].replace(".xml", "").strip())

                    locs = self.get_xml(url=url.strip()).find_all("loc")
                    filtered_locs = [link.text.strip() for link in locs]

                    with open(os.path.join(self.EXTRACTED_URLS, f"{key}.txt"), "w") as f:
                        for loc in filtered_locs:
                            f.write(loc + "\n")
        except Exception as e:
            print(Msg.URL_CRAWL_ERROR.format(e))
                    
    def content_extraction(self):
        try:
            files = os.listdir(self.EXTRACTED_URLS)
            for file in files:
                json_file = file.replace(".txt", ".json")
                print("filename: ", json_file)

                with open(os.path.join(self.EXTRACTED_URLS, file), "r") as f, \
                    open(os.path.join(self.URLS_CONTENT, json_file), "w") as out:
                    for url in f.readlines():
                        url = url.strip()
                        print(url)
                        # content = self.get_webcontent(url)
                        try:
                            content = self.get_webcontent(url)
                            if not content:
                                content = ""
                        except Exception as e:
                            print(Msg.FETCH_URL_FAILED.format(url, e))
                            content = ""
                        # Write immediately after fetching
                        out.write(json.dumps({url: content}) + "\n")
                        out.flush()  # Force write to disk immediately
        except Exception as e:
            print(Msg.CONTENT_EXTRACTION_ERROR.format(e))

if __name__ == "__main__":
    webextraction = WebExtraction(
        site_url=DEFAULT_SITE_URL,
        extracted_sitemap_urls=DEFAULT_EXTRACTED_SITEMAP_URLS,
        extracted_urls=DEFAULT_EXTRACTED_URLS,
        urls_content=DEFAULT_URLS_CONTENT
    )
    webextraction.get_all_siteurls()
    webextraction.url_crawl()
    webextraction.content_extraction()
