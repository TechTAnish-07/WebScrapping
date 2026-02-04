# Biosimilar Tender Data Collection Project

This project is a screening task for the Data Science Intern role. The goal is to collect and structure publicly available data on adalimumab biosimilar tenders from **two different official sources**.

This script successfully scrapes awarded tender notices for adalimumab from:
1.  **UK Find a Tender Service** (`find-tender.service.gov.uk`)
2.  **UK Contracts Finder Service** (`contractsfinder.service.gov.uk`)

## Deliverables

* `scrape_tenders.py`: The main Python script used to scrape the data from both sources.
* `tender_data.csv`: The final, cleaned CSV file containing the structured data from both sources.
* `requirements.txt`: A list of all Python libraries needed to run the script.
* `html_FindATender.html`: Saved HTML copy of the scraped Find a Tender page.
* `html_ContractsFinder.html`: Saved HTML copy of the scraped Contracts Finder page.
* `README.md`: This file, explaining the project and methodology.

## ⚙️ How to Run the Script

1.  **Install Dependencies:**
    * Make sure you have Python installed.
    * Install Playwright browsers:
        ```bash
        playwright install chromium
        ```
    * Install required Python libraries:
        ```bash
        pip install -r requirements.txt
        ```

2.  **Run the Script:**
    Open your terminal, navigate to the project folder, and run:
    ```bash
    python scrape_tenders.py
    ```

3.  **Get the Output:**
    The script will:
    * Fetch the web pages (or use saved HTML files if they exist).
    * Parse the data.
    * Create a file named `tender_data.csv` in the same folder with the combined results.
    * Save/update the `html_FindATender.html` and `html_ContractsFinder.html` files.

## 🛠️ Tool Selection

This script uses **Playwright (for fetching)** and **BeautifulSoup (for parsing)**.

* **Playwright:** Chosen over simple `requests` to reliably handle potential JavaScript execution on the government portals, ensuring the full, final HTML is loaded before parsing[cite: 57]. It also helps mimic a real browser to minimize scraping detection.
* **BeautifulSoup:** Used for its effectiveness in parsing the specific HTML structures of the tender pages once fetched. Selectors were carefully adjusted for each site's unique layout.
* **Why Not Scrapy?** Scrapy is a powerful framework but considered overkill for this specific task. The requirement was to scrape data from two *pre-identified* URLs, not to perform large-scale crawling or discovery across entire websites. The Playwright + BeautifulSoup combination provided sufficient capability with less setup complexity.

## Data Cleaning & Handling

* **Dates:** Standardized to `YYYY-MM-DD` format using the `datetime` library.
* **Currency:** Values cleaned (removed '£', commas) using regular expressions (`re`) and converted to floats. GBP values were converted to INR using a static exchange rate.
* **Missing Data:** Fields not found on a page (e.g., Estimated Value on Contracts Finder, Number of Units) are left blank (`None`) in the final CSV, handled using `try-except` blocks.
* **Error Handling & Logging:** The script uses `try-except` blocks for robustness and `logging` to provide informative output about progress and potential issues during execution.
* **Rate Limiting:** A `time.sleep(5)` pause is included between requests to different websites as a polite measure.

## 💡 A Note on APIs (Production Approach)

While this script successfully scrapes the data via HTML parsing as required by the task, a more robust and professional approach for ongoing data collection would be to utilize official **APIs (Application Programming Interfaces)** if available.

* **UK Find a Tender:** Provides a Data and API section offering data in OCDS JSON format.
* **UK Contracts Finder:** Also potentially offers data feeds or has API access (though less explicitly advertised than Find a Tender).

Using APIs provides data in a structured format (like JSON), is generally faster, more stable (less likely to break if website layout changes), and is the preferred industry standard when available.