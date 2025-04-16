import asyncio
from crawl4ai import AsyncWebCrawler
from dotenv import load_dotenv

#from config import BASE_URL, CSS_SELECTOR, REQUIRED_KEYS
from utils.data_utils import save_venues_to_csv
from utils.scraper_utils import fetch_and_process_page, get_browser_config, get_llm_strategy

load_dotenv()

BASE_URL = "https://ikman.lk/en/ads/sri-lanka/land-for-rent"
CSS_SELECTOR = "[class^='container--2uFyv']"
REQUIRED_KEYS = [
    "name", "price", "location", "capacity", "rating", "reviews", "description",
]

async def crawl_venues():
    user_prompt_location = input("Tell me what Location of land you're looking for: ")
    user_prompt_budget = input("Tell me what is ur Budget: ")

    browser_config = get_browser_config()
    llm_strategy = get_llm_strategy(user_prompt_location , user_prompt_budget)
    session_id = "venue_crawl_session"

    page_number = 1
    all_venues = []
    seen_names = set()

    async with AsyncWebCrawler(browser = browser_config) as crawler:
        while (page_number != 10):
            venues, no_results_found = await fetch_and_process_page(
                crawler,
                page_number,
                BASE_URL,
                CSS_SELECTOR,
                llm_strategy,
                session_id,
                REQUIRED_KEYS,
                seen_names,
                user_prompt_location, 
                user_prompt_budget
            )

            if no_results_found:
                #print("No more venues found. Ending crawl.")
                break

            if not venues:
                #print(f"No venues extracted from page {page_number}.")
                break

            all_venues.extend(venues)
            page_number += 1
            await asyncio.sleep(2)

    if all_venues:
        save_venues_to_csv(all_venues, "complete_venues.csv")
        print(f"Saved {len(all_venues)} venues to 'complete_venues.csv'.")
    else:
        print("No venues were found during the crawl.")

    #llm_strategy.show_usage()

async def main():
    await crawl_venues()

if __name__ == "__main__":
    asyncio.run(main())