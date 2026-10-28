from agents import build_reader_agent, build_search_agent, build_arxiv_agent, build_pdf_reader_agent, writer_chain, critic_chain 
import time
from tools import web_search
from langgraph.graph import StateGraph, END
from typing import TypedDict
import re

# 1. State Schema define karein
class ResearchState(TypedDict):
    topic: str
    research_results: str
    arxiv_results: str
    pdf_content: str
    web_results: str
    scraped_content: str
    report: str
    critique: str
    score: float
    iteration: int

# 2. Step 1 se 4 tak ke agents ko ek 'research_node' mein rakhein (with Failure Fallbacks)
def research_node(state: ResearchState):
    topic = state["topic"]
    
    # --- STEP 1: General Research Agent ---
    try:
        print("\n" + "  ="*50)
        print("step 1 - research agent is working .....")
        print("  ="*50)
        research_agent = build_search_agent()
        research_result = research_agent.invoke({
            "messages": [("user", f"Conduct thorough academic and technical research on: {topic}. Use arXiv search, PDF reading, and web search to gather detailed methodologies, equations, and facts.")]
        })
        state["research_results"] = research_result["messages"][-1].content
    except Exception as e:
        print(f"⚠️ Research Agent failed: {e}")
        state["research_results"] = "General research data unavailable. Proceeding with backup channels."
    time.sleep(2)

    # --- STEP 2: arXiv Research Paper Search Agent (With Fallback) ---
    try:
        print("\n" + "  ="*40)
        print("Step 2 - arXiv Research Agent is finding academic preprints...")
        print("  ="*40)
        arxiv_agent = build_arxiv_agent()
        arxiv_result = arxiv_agent.invoke({
            "messages": [("user", f"Find top academic research papers, preprints, and titles with their PDF URLs related to: {topic}.")]
        })
        state["arxiv_results"] = arxiv_result["messages"][-1].content
    except Exception as e:
        print(f"⚠️ arXiv Agent failed ({e}), using fallback handling...")
        state["arxiv_results"] = "arXiv preprints temporarily unavailable (Rate-limited or offline). Relying on core search and web insights."
    time.sleep(2)

    # --- STEP 3: PDF Content Reader Agent (With Fallback) ---
    try:
        print("\n" + "  ="*40)
        print("Step 3 - PDF Reader Agent is reading research papers...")
        print("  ="*40)
        pdf_agent = build_pdf_reader_agent()
        pdf_result = pdf_agent.invoke({
            "messages": [("user", f"Based on the arXiv papers found, use the read_research_pdf tool on the most relevant PDF URL to extract core methodologies, mathematical equations, and proofs for: {topic}.\n\narXiv Data:\n{state['arxiv_results'][:1000]}")]
        })
        state["pdf_content"] = pdf_result["messages"][-1].content
    except Exception as e:
        print(f"⚠️ PDF Reader Agent failed ({e}), using fallback handling...")
        state["pdf_content"] = "Deep PDF extraction unavailable. Proceeding with structural insights from search results."
    time.sleep(2)

    # --- Web Search ---
    try:
        raw_web = web_search.invoke({"query": topic})
        state["web_results"] = raw_web
    except Exception as e:
        state["web_results"] = f"Web search failed: {str(e)}"
    time.sleep(2)

    # --- STEP 4: Web URL Scraper Reader Agent ---
    try:
        print("\n" + "  ="*50)
        print("step 4 - Scraper Reader agent is scraping top web resources ........")
        print("  ="*50)
        reader_agent = build_reader_agent()
        reader_result = reader_agent.invoke({
            "messages": [("user", f"Pick the best technical URL from the web results and scrape it for deeper implementation details on: {topic}.\n\nWeb Results:\n{str(state['web_results'])[:800]}")]
        })
        state['scraped_content'] = reader_result["messages"][-1].content
    except Exception as e:
        print(f"⚠️ Scraper Agent failed: {e}")
        state['scraped_content'] = "Scraped content fallback data utilized."
    time.sleep(2)

    return state

# 3. Writer Node (Agar rewrite hoga toh critic ka feedback bhi sath jayega)
def writer_node(state: ResearchState):
    topic = state["topic"]
    critique = state.get("critique", "")
    iteration = state.get("iteration", 0)

    print("\n" + "  ="*50)
    print(f"step 5 - Writer is drafting report (Attempt {iteration + 1}) ....")
    print("  ="*50)

    research_combined = (
        f"RESEARCH RESULTS : \n {state.get('research_results', '')} \n\n"
        f"ARXIV PAPERS METADATA ---\n{state.get('arxiv_results', '')}\n\n"
        f"DEEP PDF PAPER EXTRACTION (Math/Formulations) ---\n{state.get('pdf_content', '')}\n\n"
        f"DETAILED SCRAPED CONTENT : \n {state.get('scraped_content', '')}"
    )

    # Agar ye loop-back hai, toh critic ke sujhaav add kar dein
    if critique:
        research_combined += f"\n\nCRITICAL REVIEW FEEDBACK FROM PREVIOUS DRAFT (Fix these points):\n{critique}"

    state["report"] = writer_chain.invoke({
        "topic": topic,
        "research": research_combined
    })

    print("\n" + "="*30 + " GENERATED REPORT " + "="*30)
    print(state["report"])
    time.sleep(3)
    return state

# 4. Critic Node
def critic_node(state: ResearchState):
    print("\n" + "  ="*50)
    print("Step 6 - Critic Chain is evaluating and scoring the report...")
    print("  ="*50)

    state["critique"] = critic_chain.invoke({
        "report": state["report"]
    })

    print("\n" + "="*30 + " CRITIC REVIEW & SCORE " + "="*30)
    print(state["critique"])
    print("="*80 + "\n")
    time.sleep(3)
    return state

# 5. Routing Logic (Score Check karke decide karega ki loop chalana hai ya nahi)
def should_rewrite(state: ResearchState) -> str:
    critique_text = state.get("critique", "")
    iteration = state.get("iteration", 0)

    # Max 2 iterations allow karenge taaki infinite loop na bane
    if iteration >= 2:
        return "end"

    score_match = re.search(r'([0-9.]+)\s*/\s*10', critique_text)
    score = float(score_match.group(1)) if score_match else 7.0
    state["score"] = score

    print(f"\n[Evaluator] Current Report Score: {score}/10 (Iteration: {iteration})")

    if score < 8.0:
        state["iteration"] = iteration + 1
        print("Score < 8.0 detected! Sending report back to Writer with Critic feedback...")
        return "rewrite"
    else:
        print("Target score achieved! Finalizing report.")
        return "end"

# 6. Main Graph Runner Pipeline
def run_research_pipeline(topic: str) -> dict:
    workflow = StateGraph(ResearchState)

    workflow.add_node("research_node", research_node)
    workflow.add_node("writer_node", writer_node)
    workflow.add_node("critic_node", critic_node)

    workflow.set_entry_point("research_node")
    workflow.add_edge("research_node", "writer_node")
    workflow.add_edge("writer_node", "critic_node")

    # Conditional loop edge
    workflow.add_conditional_edges(
        "critic_node",
        should_rewrite,
        {
            "rewrite": "writer_node",
            "end": END
        }
    )

    app = workflow.compile()
    initial_state = {"topic": topic, "iteration": 0}
    final_state = app.invoke(initial_state)
    return final_state

if __name__ == "__main__":
    topic = input("\nEnter a research topic :  ")
    run_research_pipeline(topic)