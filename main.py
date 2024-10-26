import os
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from langchain_groq import ChatGroq
from langchain_core.prompts import (
    PromptTemplate,
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate
)
from pydantic import BaseModel, Field
from deep_translator import GoogleTranslator
import string

# Environment variables for sensitive data
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY environment variable not set.")

class WebScraper:
    def __init__(self, driver_path):
        self.driver_path = driver_path

    def is_meaningful_text(self, text):
        """Check if the text is meaningful."""
        return bool(text) and not (text.startswith('http') or len(text) < 5)

    def detect_and_translate(self, text, target_language="en"):
        """Detect language and translate the given text to the target language."""
        if not self.is_meaningful_text(text):
            return text  # Return original if not meaningful
        try:
            translation = GoogleTranslator(source="auto", target=target_language).translate(text)
            print(f"Original Text: {text}")
            print(f"Translated Text: {translation}")
            return translation
        except ValueError as ve:
            print(f"Value Error during translation: {ve}")
            return text
        except Exception as e:
            print(f"Translation failed: {e}")
            return text  # Fallback to original text if translation fails

    def fetch_html_with_beautifulsoup(self, url):
        """Fetch HTML content using BeautifulSoup."""
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.83 Safari/537.36'}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            title = soup.title.string if soup.title else "No title found"
            meta_tags = [meta.get('content') for meta in soup.find_all('meta')]

            # Extracting IDs from the HTML
            ids = [tag['id'] for tag in soup.find_all(id=True)]  # Get all IDs from elements with 'id' attribute

            # Translate title and meta tags after filtering out IDs
            title_translated = self.detect_and_translate(title)
            meta_tags_translated = [self.detect_and_translate(tag) for tag in meta_tags if tag]

            return {
                "status": "success",
                "method": "BeautifulSoup",
                "title_original": title,
                "title_translated": title_translated,
                "meta_tags_original": meta_tags,
                "meta_tags_translated": meta_tags_translated,
                "ids": ids  # Include IDs in the result for reference
            }
        except requests.exceptions.RequestException as e:
            return {"status": "error", "message": f"Request failed: {e}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def fetch_html_with_selenium(self, url):
        """Fetch HTML content using Selenium."""
        try:
            options = Options()
            options.add_argument("--headless")
            service = Service(self.driver_path)
            driver = webdriver.Chrome(service=service, options=options)

            driver.get(url)
            html_content = driver.page_source
            driver.quit()

            soup = BeautifulSoup(html_content, 'html.parser')
            title = soup.title.string if soup.title else "No title found"
            meta_tags = [meta.get('content') for meta in soup.find_all('meta')]

            # Extracting IDs from the HTML
            ids = [tag['id'] for tag in soup.find_all(id=True)]  # Get all IDs from elements with 'id' attribute

            # Translate title and meta tags after filtering out IDs
            title_translated = self.detect_and_translate(title)
            meta_tags_translated = [self.detect_and_translate(tag) for tag in meta_tags if tag]

            return {
                "status": "success",
                "method": "Selenium",
                "title_original": title,
                "title_translated": title_translated,
                "meta_tags_original": meta_tags,
                "meta_tags_translated": meta_tags_translated,
                "ids": ids  # Include IDs in the result for reference
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def scrape_page(self, url):
        """Scrape the page using both BeautifulSoup and Selenium."""
        result = self.fetch_html_with_beautifulsoup(url)
        if result['status'] == "error":
            print(f"BeautifulSoup failed with error: {result['message']}. Falling back to Selenium...")
            result = self.fetch_html_with_selenium(url)

        return result

class Comp_goods(BaseModel):
    """Class for generating potential products based on website details"""
    setup: str = Field(..., description='Results from webscraper')
    goods: str = Field(..., description="Likely products based on company details")

# Initialize the language model
llm = ChatGroq(
    model="llama3-groq-70b-8192-tool-use-preview",
    api_key=GROQ_API_KEY
)

# Updated goods string with a focus on related products
goods = (
    "Based on the title and meta tags, analyze the keywords and industry-specific terms to "
    "infer the types of goods or products the company might be associated with. "
    "Focus on identifying possible goods categories or services directly relevant to the company's field."
)

# Update prompt to better specify related goods
prompt = ChatPromptTemplate(
    [
        SystemMessagePromptTemplate.from_template(
            "You are an expert in identifying products and goods a company might sell based on its website content, "
            "taking into account industry-specific keywords and phrases."
        ),
        HumanMessagePromptTemplate.from_template(
            "Here is the information from the company's website (in English):\n"
            "Title: {setup}\n"
            "Meta Tags: {goods}. "
            "Based on these details, determine what specific types of products or services this company likely offers."
        )
    ]
)

# Constructing the chain
chain = prompt | llm.with_structured_output(Comp_goods)

# Input website URL
text = input("Enter website of supplier: ")

if __name__ == "__main__":
    driver_path = "C:/Program Files (x86)/chromedriver.exe"  # Update this to your chromedriver path
    url = text

    scraper = WebScraper(driver_path)
    result = scraper.scrape_page(url)

    if result['status'] == "success":
        print(f"Scraped using: {result['method']}")
        print(f"Original Title: {result['title_original']}")
        print(f"Translated Title: {result['title_translated']}")
        print(f"Original Meta Tags: {result['meta_tags_original']}")
        print(f"Translated Meta Tags: {result['meta_tags_translated']}")

        # Constructing Comp_goods instance
        setup = f"Title: {result['title_translated']}\nMeta Tags: {', '.join(result['meta_tags_translated'])}"
        comp_goods_instance = Comp_goods(setup=setup, goods=goods)

        # Invoke LLM with structured output
        try:
            response = chain.invoke({"setup": comp_goods_instance.setup, "goods": comp_goods_instance.goods})
            print("LLM Response:", response)
        except Exception as e:
            print(f"LLM invocation failed: {str(e)}")
    else:
        print(f"Failed to scrape the page. Error: {result['message']}")
