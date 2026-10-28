from langchain.agents import create_agent 
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from tools import web_search , scrape_url , search_arxiv, read_research_pdf
import os 

from dotenv import load_dotenv

load_dotenv()

# Gemini LLM model setup
llm = ChatGoogleGenerativeAI(model="gemini-3.5-flash-lite")

# 1st agent
def build_search_agent():
    return create_agent(
        model = llm ,
        tools = [web_search],
        system_prompt="You are a research assistant. Use the web_search tool to gather recent, reliable information — technical blogs, docs, papers, benchmarks — on the user's topic. Summarize findings with source URLs."
        
    )



# 2nd agent
def build_reader_agent():
    return create_agent(
        model = llm ,
        tools = [scrape_url],
        system_prompt="You are a technical reader. Given a topic and prior research results, pick the single most relevant and authoritative URL, scrape it with scrape_url, and summarize the deeper implementation details it contains."
   
        
    )

# 3rd Agent: arXiv Research Paper Search Agent (PhD Level Research)
def build_arxiv_agent():
    return create_agent(
        model=llm,
        tools=[search_arxiv],
        system_prompt="You are an expert academic research assistant. Use the search_arxiv tool to find relevant peer-reviewed preprints , papers, and scholarly articles across all scientific, mathematical, physics , chemistry , botany , biology , computer science, and technical advanced topics like RAG, LLM architectures, and Computer Vision domains based on the user's query."
    )

# 4th Agent: PDF Content Reader Agent (Papers ko deeply read karne ke liye)
def build_pdf_reader_agent():
    return create_agent(
        model=llm,
        tools=[read_research_pdf],
        system_prompt="You are an expert scientific paper analyst. Read the full text extracted from research PDFs to pull out core methodologies, mathematical formulations, proofs , and experimental results across any scientific or technical discipline ."
    )
# writer chain 

writer_promt = ChatPromptTemplate.from_messages([
    (
        "system", 
        "You are an elite, expert academic research writer and scientist. Your job is to synthesize raw scientific and technical research data into clear, objective, structured, and deeply insightful reports."
    ),
    (
        "human", 
        """Write a comprehensive, detailed academic research report based strictly on the gathered research data provided below. Do not extrapolate or assume facts not supported by the research.
   
Topic: {topic}

Research Gathered:     
{research}

Structure the report precisely as follows:
- **Introduction**: Brief overview of the topic, its core concepts, and academic/scientific significance.     
- **Core Methodology & Mathematical Formulations**: Detailed explanation of the approach, equations, or algorithms found in the research.     
- **Key Findings & Results**: Minimum 3 well-explained, detailed points backed by the gathered data and benchmarks/proofs.     
- **Conclusion**: A concise summary of insights, limitations, and future research directions.     
- **Sources**: List all distinct URLs, arXiv papers, and references found in the research data.

     
Ensure the tone is professional, , scientific, highly technical, and formatted cleanly using markdown."""),

])

writer_chain = writer_promt | llm  | StrOutputParser()


# critic_chain

critic_promt = ChatPromptTemplate.from_messages([
    
    (
        "system", 
        "You are an elite, rigorous, and constructive academic research critic (like a top-tier peer reviewer for major scientific and AI conferences). Be strictly objective, highly detailed, and specific."
    ),
    (
        "human", 
        """Review the research report below and evaluate it strictly based on academic depth, technical accuracy, mathematical rigor, and comprehensiveness.

Report:
{report}

Respond in this exact format:

Score: X/10

Strengths:
- [Detail what the report did exceptionally well regarding methodology, clarity, or analysis]
- [...]

Areas to Improve:
- [Specify missing nuances, weak explanations, or logical gaps]
- [...]

Actionable Recommendations to Reach 10/10:
- [Provide precise advice on what specific features, mathematical formulations, benchmarks, or references to add to elevate the report's quality]
- [...]

Specific Technical & Academic Recommendations (To reach 10/10):
- [Suggest exact missing mathematical equations, formulas, or proof steps that need to be incorporated]
- [Recommend specific foundational concepts, methodologies, or types of arXiv papers/benchmarks to research and add]
- [...]

""" )
]) 

critic_chain = critic_promt | llm  | StrOutputParser()