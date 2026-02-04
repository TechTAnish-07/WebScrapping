# 🕷️ UK Tender Web Scraper (Find a Tender & Contracts Finder)

This repository contains a **Python-based web scraping solution** that extracts tender and award information from **UK government procurement portals**:

- **Find a Tender Service**
- **Contracts Finder**

The scraper follows **ethical scraping practices**, supports **dynamic websites using Playwright**, and exports structured data into a **CSV file**.

---

## 📌 Features

- ✅ Scrapes **dynamic, JavaScript-rendered pages** using Playwright
- ✅ Parses HTML using **BeautifulSoup**
- ✅ Handles **multiple tender sources**
- ✅ Extracts key tender & award metadata
- ✅ Converts GBP values to INR
- ✅ Graceful error handling & logging
- ✅ Saves rendered HTML locally (for debugging & offline parsing)
- ✅ Exports clean, structured data to CSV

---

## 📊 Data Extracted

The scraper collects the following fields (when available):

- Tender ID / Reference Number  
- Tender Title  
- Issuing Authority  
- Publication Date  
- Award Date  
- Contract Duration  
- Final Contract Price (Original Currency)  
- Estimated Contract Value (Original & INR)  
- Currency  
- Winning Company / Companies  
- Participating Companies (Bidders)  
- Source URL  

---

## ⚖️ Ethical Web Scraping Practices

This project follows responsible scraping principles:

- ✔️ Respects `robots.txt`
- ✔️ Uses delays between requests
- ✔️ Uses a real browser user-agent
- ✔️ Avoids excessive requests
- ✔️ Logs activity for transparency
- ✔️ Scrapes only publicly accessible information

> **Note:** This project is intended for **educational and research purposes only**.

---

## 🧰 Tech Stack

- **Python 3**
- **Playwright** (Dynamic page rendering)
- **BeautifulSoup (bs4)** (HTML parsing)
- **Requests**
- **Pandas** (Data processing)
- **Regex**
- **Logging**

---

## 📁 Project Structure

├── scraper.py
├── html_FindATender.html
├── html_ContractsFinder.html
├── tender_data.csv
├── README.md

- `html_*.html` → Saved rendered HTML for debugging
- `tender_data.csv` → Final extracted dataset


pip install -r requirements.txt
