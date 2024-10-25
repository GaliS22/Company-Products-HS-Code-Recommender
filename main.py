import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate, HumanMessagePromptTemplate, SystemMessagePromptTemplate
from typing import Optional
from pydantic import BaseModel, Field


GROQ_API_KEY="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"

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


class Comp_goods(BaseModel):
    """
    This class is to generate possible products of a company based on the title and metadata of the website
    """
    setup: str = Field(..., description='Results from webscraper')
    goods: str = Field(..., description="The products based on the details about the company")


llm = ChatGroq(
    model="llama3-groq-70b-8192-tool-use-preview",
    api_key=GROQ_API_KEY
)

prompt = ChatPromptTemplate(
    [
        SystemMessagePromptTemplate.from_template("use the data from class Webscraper"),
        HumanMessagePromptTemplate.from_template("Tell me which products this company is likely to sell")
    ]
)

chain = prompt | llm.with_structured_output(Comp_goods)


# Example flow where the website is provided
text = input("Enter website of supplier: ")

if __name__ == "__main__":
    driver_path = "C:/Program Files (x86)/chromedriver.exe"  # Update this to your chromedriver path
    url = text  # input URL

    scraper = WebScraper(driver_path)
    result = scraper.scrape_page(url)

    if result['status'] == "success":
        print(f"Scraped using: {result['method']}")
        print(f"Title: {result['title']}")
        print(f"Meta Tags: {result['meta_tags']}")

        # Construct Comp_goods from the scraped data
        setup = f"Title: {result['title']}\nMeta Tags: {', '.join(result['meta_tags'])}"
        goods = "Based on the title and meta tags, infer the products the company is likely to sell."

        comp_goods_instance = Comp_goods(setup=setup, goods=goods)

        # Pass the instance to the chain
        response = chain.invoke({"setup": comp_goods_instance.setup, "goods": comp_goods_instance.goods})
        print(response)

    else:
        print(f"Failed to scrape the page. Error: {result['message']}")
