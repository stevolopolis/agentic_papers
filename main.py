from agents import Agent, Runner

import asyncio
import os

from openai import AsyncOpenAI

from agents import (
    Agent,
    Runner,
    function_tool,
    set_default_openai_api,
    set_default_openai_client,
    set_tracing_disabled,
)

import dotenv
import json
import sqlite3
import arxiv
import logging
from tqdm import tqdm
from datetime import datetime
from pydantic import BaseModel

dotenv.load_dotenv()

BASE_URL = os.getenv("EXAMPLE_BASE_URL") or ""
API_KEY = os.getenv("EXAMPLE_API_KEY") or ""
MODEL_NAME = os.getenv("EXAMPLE_MODEL_NAME") or ""

if not BASE_URL or not API_KEY or not MODEL_NAME:
    raise ValueError(
        "Please set EXAMPLE_BASE_URL, EXAMPLE_API_KEY, EXAMPLE_MODEL_NAME via env var or code."
    )


client = AsyncOpenAI(
    base_url=BASE_URL,
    api_key=API_KEY,
)
set_default_openai_client(client=client, use_for_tracing=False)
set_default_openai_api("chat_completions")
set_tracing_disabled(disabled=True)


class Author(BaseModel):
	name: str
	affiliation: str
	status: str     
     

class Paper(BaseModel):
    id: str
    title: str
    author_list: Author
    pub_venue: str
    pub_lab: str
    subjects: str
    abstract: str
    link_to_paper: str
    link_to_project_page: str


BASE_INSTRUCTIONS = (
    "You are a helpful assistant that can summarize daily papers on arxiv.org for me. "
    "You are responsible for reading the CS.ai subcategory of arxiv.org and summarize the papers into the Paper class. \n\n"
)

PROMPT = (
    "Here is the dictionary of information scraped from the Arxiv API for a paper"
    "Use these information to fill the Paper class. Put <missing> if the information is not available."
    "If the abstract is more than 100 words, shorten it."
)


def get_arxiv_papers(date: datetime = None):
    if date is None:
        date = datetime.now().strftime("%Y%m%d")

     # Use arXiv API instead of HTML scraping
    logging.info(f"Calling arxiv API for date: {date}")
    search = arxiv.Search(
        query=f"cat:cs.AI AND submittedDate:[{date}0000 TO {date}2359]",
        max_results=2000,
        sort_by=arxiv.SortCriterion.SubmittedDate
    )
    client = arxiv.Client()
    results = client.results(search)

    # Convert to structured format
    papers_data = []
    logging.info(f"Restructuring papers results for the agent...")
    for result in results:
        paper_info = {
            "id": result.entry_id,
            "title": result.title,
            "authors": [{"name": author.name} for author in result.authors],
            "abstract": result.summary,
            "comment": result.comment,
            "date_published": result.published.strftime("%Y-%m-%d"),
            "primary_category": result.primary_category,
            "categories": result.categories,
        }
        papers_data.append(paper_info)

    return papers_data


async def main():
    # Initialize the agent
    agent = Agent(
        name="Assistant",
        instructions=BASE_INSTRUCTIONS + PROMPT,
        model=MODEL_NAME,
        output_type=Paper,
    )

    date = "20250313"

    # Use arXiv API instead of HTML scraping
    raw_papers = get_arxiv_papers(date)
    
    # Create a connection to the database
    logging.info(f"Saving the papers into the database...")
    conn = sqlite3.connect("arxiv_papers.db")
    cursor = conn.cursor()

    # Create a table for the papers, if it doesn't exist
    cursor.execute("""CREATE TABLE IF NOT EXISTS papers (
        id TEXT, 
        title TEXT,
        author_list TEXT,
        pub_venue TEXT,
        pub_lab TEXT,
        subjects TEXT,
        abstract TEXT,
        date_published TEXT,
        link_to_paper TEXT,
        link_to_project_page TEXT
    )""")

    # Iterate through the papers 
    logging.info("Understanding the papers and saving them into the database...")
    for raw_paper in tqdm(raw_papers):
        # Convert paper dictionary to string
        logging.debug(f"Understanding the paper: {raw_paper['title']}")
        raw_paper_str = json.dumps(raw_paper)
        result = await Runner.run(agent, raw_paper_str)
        paper = result.final_output

        # Insert the parsed papers into the database
        logging.debug(f"Inserting the papers into the database...")
        # Replace <missing> with None
        for key, value in paper.__dict__.items():
            if value == "<missing>":
                paper.__dict__[key] = None
            elif key == "author_list":
                paper.__dict__[key] = value.name

        # Convert the paper dictionary to a tuple
        paper_tuple = tuple(paper.__dict__.values())
        # Insert the paper into the database
        cursor.execute(
            "INSERT INTO papers (id, title, author_list, pub_venue, pub_lab, subjects, abstract, date_published, link_to_paper, link_to_project_page) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", 
            paper_tuple
        ) 
        conn.commit()

    # Close the connection to the database
    conn.close()

if __name__ == "__main__":
    asyncio.run(main())