import os
import requests
import psycopg2
from psycopg2 import extras
import pandas as pd
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# FDA Orange Book TXT file (latest monthly update)
ORANGEBOOK_PRODUCTS_URL = "https://www.fda.gov/media/76860/download"  # products.txt

def fetch_orangebook_products():
    """
    Fetch and parse Orange Book products.txt into a DataFrame
    """
    print(f"Fetching Orange Book products file from {ORANGEBOOK_PRODUCTS_URL} ...")
    resp = requests.get(ORANGEBOOK_PRODUCTS_URL)
    resp.raise_for_status()

    # Save temp file
    with open("products.txt", "wb") as f:
        f.write(resp.content)

    # Load as DataFrame
    df = pd.read_csv("products.txt", sep="~", dtype=str)
    print(f"✅ Loaded {len(df)} Orange Book products")
    return df


def upsert_orangebook_products(df, conn):
    """
    Upsert Orange Book products into drugs table
    """
    with conn.cursor() as cur:
        query = """
        INSERT INTO drugs (
            appl_no, product_ndc, product_no, preferred_name,
            generic_name, brand_name, manufacturer_name,
            dosage_form, route, strength, marketing_status
        )
        VALUES %s
        ON CONFLICT (product_ndc) DO UPDATE SET
            preferred_name = EXCLUDED.preferred_name,
            generic_name = EXCLUDED.generic_name,
            brand_name = EXCLUDED.brand_name,
            manufacturer_name = EXCLUDED.manufacturer_name,
            dosage_form = EXCLUDED.dosage_form,
            route = EXCLUDED.route,
            strength = EXCLUDED.strength,
            marketing_status = EXCLUDED.marketing_status;
        """

        rows = []
        for _, row in df.iterrows():
            rows.append((
                row.get("Appl_No"),
                None,  # Orange Book does not always have NDC – we will link later
                row.get("Product_No"),
                row.get("Tradename") or row.get("Ingredient"),  # preferred_name
                row.get("Ingredient"),
                row.get("Tradename"),
                row.get("Applicant"),
                row.get("Dosage_Form"),
                row.get("Route"),
                row.get("Strength"),
                row.get("ProductMktStatus"),
            ))

        extras.execute_values(cur, query, rows, page_size=500)
    conn.commit()
    print(f"✅ Upserted {len(rows)} Orange Book products into drugs table")


def main():
    conn = psycopg2.connect(DATABASE_URL)
    try:
        df = fetch_orangebook_products()
        upsert_orangebook_products(df, conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
