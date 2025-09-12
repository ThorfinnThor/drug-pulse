import os
import requests
import psycopg2
import pandas as pd
from bs4 import BeautifulSoup
from io import BytesIO
from psycopg2 import extras
from dotenv import load_dotenv

# Load env
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

FDA_ORANGEBOOK_PAGE = "https://www.fda.gov/drugs/drug-approvals-and-databases/orange-book-data-files"

def get_orangebook_url():
    """
    Scrape FDA Orange Book data page to find the current Products XLSX file.
    """
    print(f"Scraping {FDA_ORANGEBOOK_PAGE} for Orange Book files...")

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/116.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    resp = requests.get(FDA_ORANGEBOOK_PAGE, headers=headers, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if ("product" in href.lower()) and (
            href.endswith(".zip") or href.endswith(".xlsx") or href.endswith(".xls")
        ):
            if href.startswith("/"):
                href = "https://www.fda.gov" + href
            print(f"✅ Found Orange Book file: {href}")
            return href

    raise RuntimeError("Could not find Orange Book Products file on FDA site")

def fetch_orangebook_products():
    """
    Download and load the Orange Book products file into a DataFrame.
    """
    url = get_orangebook_url()
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()

    if url.endswith(".zip"):
        from zipfile import ZipFile
        from io import BytesIO
        zf = ZipFile(BytesIO(resp.content))
        # assume first file inside ZIP is the Excel
        fname = zf.namelist()[0]
        df = pd.read_excel(zf.open(fname))
    else:
        df = pd.read_excel(BytesIO(resp.content))

    print(f"✅ Orange Book data: {len(df)} rows loaded from {url}")
    return df

def upsert_orangebook(df, conn):
    """
    Insert/update Orange Book products into drugs table.
    """
    with conn.cursor() as cur:
        query = """
        INSERT INTO drugs (
            preferred_name, generic_name, brand_name, manufacturer_name,
            product_ndc, marketing_status
        )
        VALUES %s
        ON CONFLICT (product_ndc) DO UPDATE SET
            preferred_name = EXCLUDED.preferred_name,
            generic_name = EXCLUDED.generic_name,
            brand_name = EXCLUDED.brand_name,
            manufacturer_name = EXCLUDED.manufacturer_name,
            marketing_status = EXCLUDED.marketing_status;
        """

        rows = []
        for _, row in df.iterrows():
            rows.append((
                row.get("Ingredient", None),       # generic name
                row.get("Ingredient", None),
                row.get("Trade_Name", None),       # brand name
                row.get("Applicant", None),        # manufacturer
                row.get("Product_No", None),       # product ID
                row.get("Marketing_Status", None)  # marketing status
            ))

        extras.execute_values(cur, query, rows, page_size=500)
    conn.commit()
    print(f"✅ Upserted {len(rows)} Orange Book products into DB")

def main():
    print("Fetching Orange Book products...")
    df = fetch_orangebook_products()
    conn = psycopg2.connect(DATABASE_URL)
    try:
        upsert_orangebook(df, conn)
    finally:
        conn.close()

if __name__ == "__main__":
    main()
