from tkinter.ttk import Separator
import pymupdf as fitz # PyMuPDF
from urllib import response
import urllib.request

from langchain.tools import tool 
import requests
from bs4 import BeautifulSoup
from tavily import TavilyClient
import os


from langchain_google_genai import ChatGoogleGenerativeAI

from rich import print 

from dotenv import load_dotenv
load_dotenv()

tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

@tool
def web_search(query : str) -> str:
    """Search the web for recent and reliable information on a topic . Returns Titles , URLs and snippets."""

    results = tavily.search(query=query , max_results=5)

    out = []

    for r in results['results']:
        out.append(
            f"Title:{r['title']}\nURL: {r['url']} \nSnippet:{['content'][:300]}\n"
        )

    return "\n----\n".join(out)

@tool
def scrape_url(url:str) -> str:
    """Scrape and return clean text content from a given URL for depper reading."""

    try:
        resp = requests.get(url,timeout=8, headers={"User-Agent":"Mozilla/5.0"})
        soup = BeautifulSoup(resp.text,"html.parser")

        for tag in soup(["script" , "style" ,"nav" , "footer" , "header"]):
            tag.decompose()
            return soup.get_text(Separator=" " , strip=True)[:3000]
    except Exception as e:
        return f"Could not scrape URL: {str(e)}"  
  


import arxiv

@tool
def search_arxiv(query: str) -> str:
    """Search arXiv for academic papers on RAG, LLMs, or Computer Vision. Returns titles, authors, summaries, and PDF links."""
    
    # ✅ Create a client instance (Required for newer arxiv package versions)
    client = arxiv.Client(
        page_size=5,
        delay_seconds=3.0,  # Do requests ke beech 3 second ka gap
        num_retries=3
    )
    
    search = arxiv.Search(
        query=query,
        max_results=3,
        sort_by=arxiv.SortCriterion.Relevance
    )

    try:
       out = []
         # ✅ Use client.results(search) instead of search.results()
       for paper in client.results(search):
          out.append(
             f"Title: {paper.title}\n"
             f"Authors: {','.join([a.name for a in paper.authors])}\n"
             f"Summary: {paper.summary}\n"
             f"PDF URL: {paper.pdf_url}\n"
        )
       return "\n----\n".join(out)
    except Exception as e:
        return f"arXiv search temporarily rate-limited. Skipping to web search fallback. Error: {str(e)}"

@tool
def read_research_pdf(pdf_url: str) -> str:
    """Download and extract full text from an academic research PDF URL for deep analysis."""
    try:
        local_filename, _ = urllib.request.urlretrieve(pdf_url)
        doc = fitz.open(local_filename)
        text = ""
        for page in doc:
            text += page.get_text()
        # Return first 15,000 characters to stay within context limits while capturing core methodology
        return text[:15000]
    except Exception as e:
        return f"Failed to read PDF: {str(e)}"