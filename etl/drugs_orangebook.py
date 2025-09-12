import os
import requests
import psycopg2
import pandas as pd
from io import BytesIO
from psycopg2 import extras
from dotenv import load_dotenv

# Load env
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# Multiple Orange Book product URLs (FDA sometimes rotates these IDs)
ORANGEBOOK_URLS = [
    "https://www.fda.gov/media/76860/download",  # Older Products file
    "https://www.fda.gov/media/76862/download",  # Alternate Products file
]

def fetch_orangebook_products():
    """
    Try multiple Orange Book URLs until one works.
    Returns a Pandas DataFrame.
    """
    for url in ORANGEBOOK_URLS:
        print(f"Trying Orange Book products file from {url} ...")
        resp = requests.get(url)
        if resp.status_code == 200:
            print(f"✅ Successfully fetched Orange Book products from {url}")
            return pd.read_excel(BytesIO(resp.content))
        else:
            print(f"⚠️ Failed to fetch {url} with {resp.status_code}")
    raise RuntimeError("No valid Orange Book file could be fetched.")

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
                row.get("Ingredient", None),       # generic name
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
    print(f"✅ Orange Book data: {len(df)} rows fetched")

    conn = psycopg2.connect(DATABASE_URL)
    try:
        upsert_orangebook(df, conn)
    finally:
        conn.close()

if __name__ == "__main__":
    main()
