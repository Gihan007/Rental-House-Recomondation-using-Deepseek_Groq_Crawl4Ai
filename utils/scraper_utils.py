import json
import os
from typing import List, Set, Tuple

from crawl4ai import (
    AsyncWebCrawler,
    BrowserConfig,
    CacheMode,
    CrawlerRunConfig,
    LLMExtractionStrategy,
)

from models.venue import Venue
from utils.data_utils import is_complete_venue, is_duplicate_venue

def get_browser_config() -> BrowserConfig:
    return BrowserConfig(
        browser_type="chromium",
        headless=False,
        verbose=True,
    )

def get_llm_strategy(user_prompt_location: str , user_prompt_budget: str) -> LLMExtractionStrategy:
    return LLMExtractionStrategy(
        provider="groq/deepseek-r1-distill-llama-70b",
        api_token=os.getenv("GROQ_API_KEY"),
        schema=Venue.model_json_schema(),
        extraction_type="schema",
        instruction=(
            f"The user is looking for: {user_prompt_location} , and {user_prompt_budget} land. \n"
            "From the content below, extract only those venues that match the user's intents like user_prompt_location and user_prompt_budget. "
            "Return venue objects with name, location, price, capacity, rating, reviews, and a one-line description."
        ),
        input_format="markdown",
        verbose=True,
    )

async def check_no_results(
    crawler: AsyncWebCrawler,
    url: str,
    session_id: str,
) -> bool:
    result = await crawler.arun(
        url=url,
        config=CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            session_id=session_id,
        ),
    )
    if result.success:
        if "No Results Found" in result.cleaned_html:
            return True
    else:
        print(f"Error fetching page for 'No Results Found' check: {result.error_message}")
        
    return False

async def fetch_and_process_page(
    crawler: AsyncWebCrawler,
    page_number: int,
    base_url: str,
    css_selector: str,
    llm_strategy: LLMExtractionStrategy,
    session_id: str,
    required_keys: List[str],
    seen_names: Set[str],
    user_prompt_location: str,
    user_prompt_budget: int
) -> Tuple[List[dict], bool]:

    url = f"{base_url}?sort=date&order=desc&buy_now=0&urgent=0&page={page_number}"
    #print(f"Loading page {page_number}...")

    no_results = await check_no_results(crawler, url, session_id)
    if no_results:
        return [], True

    result = await crawler.arun(
        url=url,
        config=CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            extraction_strategy=llm_strategy,
            css_selector=css_selector,
            session_id=session_id,
        ),
    )

    if not (result.success and result.extracted_content):
        #print(f"Error fetching page {page_number}: {result.error_message}")
        return [], False

    extracted_data = json.loads(result.extracted_content)
    if not extracted_data:
        #print(f"No venues found on page {page_number}.")
        return [], False

    #print("Extracted data:", extracted_data)

    complete_venues = []
    for venue in extracted_data:
        #print("Processing venue:", venue)

        if venue.get("error") is False:
            venue.pop("error", None)

        if not is_complete_venue(venue, required_keys):
            continue

        if is_duplicate_venue(venue["name"], seen_names):
            #print(f"Duplicate venue '{venue['name']}' found. Skipping.")
            continue
        
        

        seen_names.add(venue["name"])
        complete_venues.append(venue)

    if not complete_venues:
        #print(f"No complete venues found on page {page_number}.")
        return [], False

    #print(f"Extracted {len(complete_venues)} venues from page {page_number}.")
    return complete_venues, False