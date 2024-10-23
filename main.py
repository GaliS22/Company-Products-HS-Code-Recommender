import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options


class WebScraper:
    def __init__(self, driver_path):
        self.driver_path = driver_path

    def fetch_html_with_beautifulsoup(self, url):
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.83 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            # Parsing with BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            title = soup.title.string if soup.title else "No title found"
            meta_tags = [meta.get('content') for meta in soup.find_all('meta')]

            return {"status": "success", "method": "BeautifulSoup", "title": title, "meta_tags": meta_tags}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def fetch_html_with_selenium(self, url):
        try:
            # Set up Selenium options (headless mode)
            options = Options()
            options.add_argument("--headless")
            service = Service(self.driver_path)
            driver = webdriver.Chrome(service=service, options=options)

            driver.get(url)


            # After the page is loaded and cookies are handled, extract the HTML
            html_content = driver.page_source
            driver.quit()

            # Parse with BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            title = soup.title.string if soup.title else "No title found"
            meta_tags = [meta.get('content') for meta in soup.find_all('meta')]

            return {"status": "success", "method": "Selenium", "title": title, "meta_tags": meta_tags}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def scrape_page(self, url):
        # Try BeautifulSoup first
        result = self.fetch_html_with_beautifulsoup(url)

        # If BeautifulSoup fails, fallback to Selenium
        if result['status'] == "error":
            print(f"BeautifulSoup failed with error: {result['message']}. Falling back to Selenium...")
            result = self.fetch_html_with_selenium(url)

        return result

if __name__ == "__main__":
    driver_path = "C:\Program Files (x86)\chromedriver.exe"  # Update this to your chromedriver path
    url = "http://example.com"  # input URL

    scraper = HybridWebScraper(driver_path)
    result = scraper.scrape_page(url)

    if result['status'] == "success":
        print(f"Scraped using: {result['method']}")
        print(f"Title: {result['title']}")
        print(f"Meta Tags: {result['meta_tags']}")
    else:
        print(f"Failed to scrape the page. Error: {result['message']}")


