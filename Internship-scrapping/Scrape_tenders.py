import requests
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
import logging
from datetime import datetime
import os # Import the os module

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Currency Rates (Static) ---
# Both UK sites use GBP
GBP_TO_INR_RATE = 116.95  # Rate as of 2025-10-25
# EUR_TO_INR_RATE = 102.11 # Not needed if only using UK sites

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"

# Ensure filenames have .html extension and are distinct
OUTPUT_HTML_FILES = ['html_FindATender.html', 'html_ContractsFinder.html']

# --- Helper Functions ---

def fetch_dynamic_html(url, wait_for_selector=None, wait=5, timeout=60):
    """Fetches fully rendered HTML using Playwright."""
    logging.info(f"Rendering page via Playwright: {url}")
    html_content = None
    playwright_instance = None
    browser = None
    context = None
    page = None
    try:
        playwright_instance = sync_playwright().start()
        browser = playwright_instance.chromium.launch(headless=False, args=["--no-sandbox"])
        context = browser.new_context(user_agent=USER_AGENT)
        page = context.new_page()
        page.set_default_timeout(timeout * 1000)

        logging.info(f"Navigating to {url}...")
        page.goto(url, wait_until="load", timeout=timeout * 1000)
        logging.info("Initial page load complete.")

        if wait_for_selector:
            logging.info(f"Waiting for selector: '{wait_for_selector}' (up to {timeout // 2}s)")
            page.locator(wait_for_selector).wait_for(timeout=(timeout // 2 * 1000))
            logging.info(f"Selector '{wait_for_selector}' found.")
        else:
             logging.info(f"Waiting {wait} seconds for dynamic content...")
             page.wait_for_timeout(wait * 1000)

        html_content = page.content()
        logging.info(f"Successfully rendered and fetched HTML for {url} (Length: {len(html_content)} bytes)")

    except Exception as e:
        logging.error(f"Playwright failed to render {url}: {e}")
        html_content = None # Ensure None is returned on error
    finally:
        # Gracefully close resources
        if page:
            try: page.close()
            except Exception as e: logging.error(f"Error closing page: {e}")
        if context:
             try: context.close()
             except Exception as e: logging.error(f"Error closing context: {e}")
        if browser:
            try: browser.close()
            except Exception as e: logging.error(f"Error closing browser: {e}")
        if playwright_instance:
             try: playwright_instance.stop()
             except Exception as e: logging.error(f"Error stopping Playwright: {e}")

    return html_content


def clean_currency(text, rate):
    if not text: return None, None
    cleaned_text = re.sub(r'[£€,]', '', text.split(' ')[0]).replace(' ', '').replace('\xa0', '')
    try:
        original_value = float(cleaned_text)
        inr_value = round(original_value * rate, 2)
        return original_value, inr_value
    except (ValueError, TypeError):
        return None, None

def clean_date(text, date_format='%d %B %Y'):
    if not text: return None
    try:
        date_part = text.split(',')[0].strip()
        return datetime.strptime(date_part, date_format).strftime('%Y-%m-%d')
    except (ValueError, AttributeError):
        for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%d %b %Y']:
            try:
                # Handle potential extra text like '(by 5:00pm)'
                date_only = text.strip().split('(')[0].strip()
                return datetime.strptime(date_only, fmt).strftime('%Y-%m-%d')
            except (ValueError, TypeError):
                continue
        logging.warning(f"Could not parse date: '{text}' with any known format.")
        return text

# --- Scraper 1: UK Find a Tender (find-tender.service.gov.uk) ---

def scrape_uk_tender(url):
    """Scrapes the tender notice from the UK Find a Tender service using Playwright or local file."""
    logging.info(f"--- Processing UK Find a Tender ---")
    html_file_path = OUTPUT_HTML_FILES[0]
    html_content = None

    if os.path.exists(html_file_path):
        logging.info(f"Found existing HTML file: {html_file_path}. Reading from file.")
        try:
            with open(html_file_path, 'r', encoding='utf-8') as f: html_content = f.read()
            if not html_content: logging.warning(f"Existing HTML file {html_file_path} is empty. Will try fetching.")
            else: logging.info(f"Successfully read HTML from {html_file_path}")
        except Exception as e:
            logging.error(f"Error reading HTML file {html_file_path}: {e}. Will try fetching.")
            html_content = None

    if not html_content:
        logging.info(f"No valid local HTML found. Fetching from URL: {url}")
        html_content = fetch_dynamic_html(url, wait_for_selector='h1.govuk-heading-l', wait=5)
        if html_content:
            try:
                with open(html_file_path, 'w', encoding='utf-8') as f: f.write(html_content)
                logging.info(f"Saved fetched UK HTML to {html_file_path}")
            except IOError as e: logging.error(f"Failed to save fetched UK HTML: {e}")
        else:
            logging.error(f"Failed to fetch HTML for UK URL {url}. Cannot proceed.")
            return None

    soup = BeautifulSoup(html_content, 'html.parser')
    data = {"Source URL": url, "Currency (Original)": "GBP"}

    try: data['Tender Title'] = soup.find('h1', class_='govuk-heading-l').get_text(strip=True)
    except Exception: data['Tender Title'] = None
    try:
        id_p = soup.find('p', string=re.compile(r'Notice identifier:', re.I))
        data['Tender ID/Reference Number'] = id_p.get_text(strip=True).replace('Notice identifier:', '').strip() if id_p else None
    except Exception: data['Tender ID/Reference Number'] = None
    try:
        pub_p = soup.find('p', string=re.compile(r'Published', re.I))
        pub_date_text = pub_p.get_text(strip=True).replace('Published', '').strip() if pub_p else None
        data['Publication Date'] = clean_date(pub_date_text, '%d %B %Y')
    except Exception: data['Publication Date'] = None
    try:
        h1_title = soup.find('h1', class_='govuk-heading-l')
        authority_ul = h1_title.find_next('ul', class_='govuk-list') if h1_title else None
        authority_li = authority_ul.find('li') if authority_ul else None
        data['Issuing Authority'] = authority_li.get_text(strip=True) if authority_li else None
    except Exception: data['Issuing Authority'] = None
    try:
        award_date_span = soup.find('span', string=re.compile(r'V\.2\.1\)\s+Date of conclusion of the contract', re.I))
        h4_award_date = award_date_span.find_parent('h4') if award_date_span else None
        award_date_p = h4_award_date.find_next_sibling('p') if h4_award_date else None
        data['Award Date'] = clean_date(award_date_p.get_text(strip=True), '%d %B %Y') if award_date_p else None
    except Exception: data['Award Date'] = None
    try:
        winners = []
        winner_spans = soup.find_all('span', string=re.compile(r'V\.2\.3\)\s+Name and address of the contractor', re.I))
        for winner_span in winner_spans:
            h4_winner = winner_span.find_parent('h4')
            winner_p = h4_winner.find_next_sibling('p') if h4_winner else None
            if winner_p: winners.append(winner_p.get_text(strip=True))
        data['Winning Company/Companies'] = ", ".join(winners) if winners else None
    except Exception: data['Winning Company/Companies'] = None
    try:
        value_span = soup.find('span', string=re.compile(r'V\.2\.4\)\s+Information on value of contract/lot', re.I))
        final_price_text, est_price_text = None, None
        if value_span:
            h4_values = value_span.find_parent('h4')
            if h4_values:
                p1 = h4_values.find_next_sibling('p')
                p2 = p1.find_next_sibling('p') if p1 else None
                if p1:
                    p1_text = p1.get_text()
                    if 'Initial estimated' in p1_text: est_price_text = p1_text.split(':')[-1].strip()
                    elif 'Total value' in p1_text: final_price_text = p1_text.split(':')[-1].strip()
                if p2:
                    p2_text = p2.get_text()
                    if 'Initial estimated' in p2_text: est_price_text = p2_text.split(':')[-1].strip()
                    elif 'Total value' in p2_text: final_price_text = p2_text.split(':')[-1].strip()
        data['Final Contract Price (Original)'], _ = clean_currency(final_price_text, 1)
        val, inr = clean_currency(est_price_text, GBP_TO_INR_RATE)
        data['Estimated Contract Value (Original)'] = val
        data['Estimated Contract Value (INR)'] = inr
    except Exception: data['Final Contract Price (Original)'], data['Estimated Contract Value (Original)'], data['Estimated Contract Value (INR)'] = None, None, None
    try:
        start_date, end_date = None, None
        lot1_section = soup.find(id='object-1-lot-1')
        h4_duration_heading_span = lot1_section.find('span', string=re.compile(r'II\.2\.7\)\s+Duration of the contract', re.I)) if lot1_section else None
        if h4_duration_heading_span:
            h4_duration = h4_duration_heading_span.find_parent('h4')
            if h4_duration:
                possible_tags = h4_duration.find_next_siblings(['p','dd'], limit=5)
                for tag in possible_tags:
                    tag_text = tag.get_text()
                    if 'Start date:' in tag_text: start_date = clean_date(tag_text.replace('Start date:', '').strip(), '%d %B %Y')
                    elif 'End date:' in tag_text: end_date = clean_date(tag_text.replace('End date:', '').strip(), '%d %B %Y')
                    if start_date and end_date: break
        if not (start_date and end_date):
            desc_heading_span = soup.find('span', string=re.compile(r'II\.1\.4\)\s+Short description', re.I))
            desc_h4 = desc_heading_span.find_parent('h4') if desc_heading_span else None
            desc_p = desc_h4.find_next_sibling('p', class_='govuk-body') if desc_h4 else None
            if desc_p:
                desc_text = desc_p.get_text()
                match = re.search(r'Period of framework:\s*(\d{1,2}\s+\w+\s+\d{4})\s+to\s+(\d{1,2}\s+\w+\s+\d{4})', desc_text, re.IGNORECASE)
                if match:
                    start_date = clean_date(match.group(1), '%d %B %Y')
                    end_date = clean_date(match.group(2), '%d %B %Y')
        data['Contract Duration'] = f"{start_date} to {end_date}" if start_date and end_date else None
    except Exception: data['Contract Duration'] = None
    try:
        bidders_span = soup.find('span', string=re.compile(r'V\.2\.2\)\s+Information about tenders', re.I))
        h4_bidders = bidders_span.find_parent('h4') if bidders_span else None
        bidders_p = h4_bidders.find_next_sibling('p', string=re.compile(r'Number of tenders received:', re.I)) if h4_bidders else None
        data['List of Participating Companies (bidders)'] = bidders_p.get_text(strip=True).split(':')[-1].strip() if bidders_p else None
    except Exception: data['List of Participating Companies (bidders)'] = None
    data['Number of units/doses required'] = None

    if data.get('Tender Title') or data.get('Issuing Authority'):
        logging.info("Successfully parsed UK Find a Tender.")
    else:
        logging.warning("Parsed UK Find a Tender, but key fields seem missing. Review html_FindATender.html.")
    return data

# --- Scraper 2: UK Contracts Finder (contractsfinder.service.gov.uk) --- REVISED
def scrape_contracts_finder_tender(url):
    """Scrapes the tender notice from the UK Contracts Finder service using Playwright or local file."""
    logging.info(f"--- Processing UK Contracts Finder Tender ---")
    html_file_path = OUTPUT_HTML_FILES[1] # Use the second filename
    html_content = None

    # --- Check if HTML file exists ---
    if os.path.exists(html_file_path):
        logging.info(f"Found existing HTML file: {html_file_path}. Reading from file.")
        try:
            with open(html_file_path, 'r', encoding='utf-8') as f: html_content = f.read()
            if not html_content: logging.warning(f"Existing HTML file {html_file_path} is empty. Will try fetching.")
            else: logging.info(f"Successfully read HTML from {html_file_path}")
        except Exception as e:
            logging.error(f"Error reading HTML file {html_file_path}: {e}. Will try fetching.")
            html_content = None

    # --- Fetch if file doesn't exist or read failed ---
    if not html_content:
        logging.info(f"No valid local HTML found. Fetching from URL: {url}")
        # Use the confirmed correct selector for the title
        html_content = fetch_dynamic_html(url, wait_for_selector='h1.govuk-heading-l', wait=3)
        if html_content:
            try:
                with open(html_file_path, 'w', encoding='utf-8') as f: f.write(html_content)
                logging.info(f"Saved fetched Contracts Finder HTML to {html_file_path}")
            except IOError as e: logging.error(f"Failed to save fetched Contracts Finder HTML: {e}")
        else:
            logging.error(f"Failed to fetch HTML for Contracts Finder URL {url}. Cannot proceed.")
            return None

    # --- Proceed with Parsing ---
    soup = BeautifulSoup(html_content, 'html.parser')
    data = {"Source URL": url, "Currency (Original)": "GBP"}

    # --- Helper to find data following a specific H4 heading ---
    def find_data_after_h4(context_soup, heading_text):
        try:
            # Find h4 containing the strong tag with the text
            h4_tag = context_soup.find(lambda tag: tag.name == 'h4' and tag.find('strong', string=re.compile(r'\s*' + re.escape(heading_text) + r'\s*', re.I)))
            if h4_tag:
                p_tag = h4_tag.find_next_sibling('p')
                if p_tag:
                    return p_tag.get_text(strip=True)
            return None
        except Exception: return None

    # --- Extract data ---
    try:
        # Title selector confirmed from screenshot
        title_tag = soup.find('h1', class_='govuk-heading-l') # Use correct class 'l' not 'xl'
        data['Tender Title'] = title_tag.get_text(strip=True) if title_tag else None
    except Exception: data['Tender Title'] = None

    try:
        match = re.search(r'/notice/([\w-]+)', url)
        data['Tender ID/Reference Number'] = match.group(1) if match else None
    except Exception: data['Tender ID/Reference Number'] = None

    # Issuing Authority - Attempt to find "Buyer:" in summary list first
    try:
        buyer_dt = soup.find('dt', class_='govuk-summary-list__key', string=re.compile(r'\s*Buyer:\s*', re.I))
        if buyer_dt:
            buyer_dd = buyer_dt.find_next_sibling('dd', class_='govuk-summary-list__value')
            data['Issuing Authority'] = buyer_dd.get_text(strip=True) if buyer_dd else None
        else:
            # Fallback: Get Contact Name from "About the buyer" section
            logging.info("Buyer name not in summary list, looking for Contact Name.")
            about_buyer_heading = soup.find('h3', string=re.compile(r'About the buyer', re.I))
            if about_buyer_heading:
                 # Use the helper function to find data after 'Contact name' h4
                 contact_name = find_data_after_h4(about_buyer_heading.parent, 'Contact name')
                 data['Issuing Authority'] = contact_name # Use contact name as proxy
                 logging.info(f"Using Contact Name as Issuing Authority: {contact_name}")
            else:
                 data['Issuing Authority'] = None
                 logging.warning("Could not find Buyer or Contact Name.")

    except Exception as e:
         logging.warning(f"Error parsing Issuing Authority: {e}")
         data['Issuing Authority'] = None


    # Find data within the "Award information" section
    award_info_heading = soup.find('h3', string=re.compile(r'Award information', re.I))
    award_info_section = award_info_heading.parent if award_info_heading else soup # Search within this section

    data['Publication Date'] = clean_date(find_data_after_h4(soup, 'Published date'), '%d %B %Y') # Look page-wide
    data['Award Date'] = clean_date(find_data_after_h4(award_info_section, 'Awarded date'), '%d %B %Y')

    value_text = find_data_after_h4(award_info_section, 'Total value of contract')
    val, inr = clean_currency(value_text, GBP_TO_INR_RATE)
    data['Final Contract Price (Original)'] = val
    data['Estimated Contract Value (Original)'] = None # Still likely unavailable
    data['Estimated Contract Value (INR)'] = None # Still likely unavailable

    start_date_text = find_data_after_h4(award_info_section, 'Contract start date')
    end_date_text = find_data_after_h4(award_info_section, 'Contract end date')
    start_date = clean_date(start_date_text, '%d %B %Y')
    end_date = clean_date(end_date_text, '%d %B %Y')
    data['Contract Duration'] = f"{start_date} to {end_date}" if start_date and end_date else None

    # Get Winners
    try:
        winners = []
        if award_info_section:
            # Find all H4s directly within the award info section that don't contain standard labels
            possible_winner_h4s = award_info_section.find_all('h4', recursive=False) # Only direct children H4s
            standard_labels = ['awarded date', 'contract start date', 'contract end date', 'total value of contract']
            for h4 in possible_winner_h4s:
                 h4_text = h4.get_text(strip=True).lower()
                 is_standard_label = any(label in h4_text for label in standard_labels)
                 if not is_standard_label:
                     # Assume this H4 contains the winner name (often within a strong tag)
                     winner_name_tag = h4.find('strong') or h4
                     winner_name = winner_name_tag.get_text(strip=True)
                     if winner_name: winners.append(winner_name)
            data['Winning Company/Companies'] = ", ".join(winners) if winners else None
        else: data['Winning Company/Companies'] = None
    except Exception as e:
         logging.warning(f"Could not parse CF Winners: {e}")
         data['Winning Company/Companies'] = None

    data['List of Participating Companies (bidders)'] = None # Not available
    data['Number of units/doses required'] = None # Not available

    if data.get('Tender Title') or data.get('Issuing Authority'):
        logging.info("Successfully parsed Contracts Finder tender.")
    else:
        logging.warning("Parsed Contracts Finder tender, but key fields seem missing. Review html_ContractsFinder.html.")
    return data

# --- Main Execution Block ---
if __name__ == "__main__":

    # --- URLs to Scrape ---
    UK_FINDATENDER_URL = "https://www.find-tender.service.gov.uk/Notice/008624-2023" #here we can give list of link and using for loop we can store data
    UK_CONTRACTSFINDER_URL = "https://www.contractsfinder.service.gov.uk/notice/05c544dc-9e6f-452d-87c1-bf00f3ce73ac" # Source 2

    # Update HTML filenames list to match functions
    OUTPUT_HTML_FILES = ['html_FindATender.html', 'html_ContractsFinder.html']

    all_tender_data = []

    # --- Scrape Site 1 (Find a Tender) ---
    uk_fa_data = scrape_uk_tender(UK_FINDATENDER_URL)
    if uk_fa_data:
        all_tender_data.append(uk_fa_data)
    else:
        logging.error(f"UK Find a Tender scraping returned no data for {UK_FINDATENDER_URL}")

    logging.info("Pausing for 5 seconds before next request...")
    time.sleep(5)

    # --- Scrape Site 2 (Contracts Finder) ---
    uk_cf_data = scrape_contracts_finder_tender(UK_CONTRACTSFINDER_URL) # Call the CF function
    if uk_cf_data:
        all_tender_data.append(uk_cf_data)
    else:
        logging.error(f"UK Contracts Finder scraping returned no data for {UK_CONTRACTSFINDER_URL}")

    # --- Combine and Export ---
    if all_tender_data:
        logging.info(f"Successfully scraped {len(all_tender_data)} tenders. Combining data...")
        df = pd.DataFrame(all_tender_data)
        final_columns = [
            'Tender ID/Reference Number', 'Tender Title', 'Issuing Authority',
            'Publication Date', 'Award Date', 'Contract Duration',
            # Adjusted value columns based on typical Contracts Finder data
            'Final Contract Price (Original)', 'Estimated Contract Value (INR)', # Keep INR for consistency if UK FaT had it
            'Estimated Contract Value (Original)', 'Currency (Original)',
            'Winning Company/Companies', 'List of Participating Companies (bidders)',
            'Number of units/doses required', 'Source URL'
        ]
        df = df.reindex(columns=final_columns) # Ensure columns exist and are ordered
        try:
            df.to_csv("tender_data.csv", index=False, encoding='utf-8-sig')
            logging.info("✅ Successfully saved all data to tender_data.csv")
        except Exception as e:
            logging.error(f"Failed to save CSV: {e}")
    else:
        logging.error("❌ No data was successfully scraped from any source. CSV not created.")

    logging.info("Script finished.")