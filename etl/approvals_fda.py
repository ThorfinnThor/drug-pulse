#!/usr/bin/env python3
"""
FDA Approvals ETL Script
Fetches FDA drug approvals from openFDA API and upserts into database
"""

import os
import requests
import psycopg2
from psycopg2 import extras
from dotenv import load_dotenv
import logging
from datetime import datetime
import json

from db import get_db_connection

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

FDA_API_BASE = "https://api.fda.gov"


def fetch_fda_approvals(limit=100, max_skip=25000):
    """Fetch FDA approvals with pagination and extract brand/generic names"""
    approvals = []
    skip = 0

    while skip <= max_skip:
        url = f"{FDA_API_BASE}/drug/drugsfda.json"
        params = {"limit": limit, "skip": skip}

        try:
            resp = requests.get(url, params=params, timeout=30)
            if resp.status_code == 404:
                break
            resp.raise_for_status()

            data = resp.json()
            results = data.get("results", [])
            if not results:
                break

            for r in results:
                submissions = r.get("submissions", [])
                for sub in submissions:
                    approvals.append({
                        "application_number": r.get("application_number"),
                        "sponsor": r.get("sponsor_name"),
                        "brand_name": (
                            (r.get("openfda", {}).get("brand_name", [None])[0])
                            if r.get("openfda") and r["openfda"].get("brand_name")
                            else (r.get("products", [{}])[0].get("brand_name") if r.get("products") else None)
                        ),
                        "generic_name": (
                            (r.get("openfda", {}).get("generic_name", [None])[0])
                            if r.get("openfda") and r["openfda"].get("generic_name")
                            else (r.get("products", [{}])[0].get("active_ingredients", [{}])[0].get("name") if r.get("products") else None)
                        ),
                        "submission_type": sub.get("submission_type"),
                        "submission_number": sub.get("submission_number"),
                        "submission_status": sub.get("submission_status"),
                        "submission_status_date": sub.get("submission_status_date"),
                        "products": r.get("products", []),
                    })

            logger.info(f"Fetched {len(results)} approvals from skip={skip}")
            skip += limit

        except Exception as e:
            logger.error(f"Error fetching FDA approvals at skip={skip}: {e}")
            break

    logger.info(f"Total {len(approvals)} FDA approvals fetched")
    return approvals


def upsert_approvals(approvals, conn):
    """Insert or update FDA approvals in DB"""
    with conn.cursor() as cur:
        query = """
            INSERT INTO approvals (
                application_number, sponsor, brand_name, generic_name,
                submission_type, submission_number, submission_status,
                submission_status_date, products
            )
            VALUES %s
            ON CONFLICT (application_number, submission_number)
            DO UPDATE SET
                sponsor = EXCLUDED.sponsor,
                brand_name = EXCLUDED.brand_name,
                generic_name = EXCLUDED.generic_name,
                submission_status = EXCLUDED.submission_status,
                submission_status_date = EXCLUDED.submission_status_date,
                products = EXCLUDED.products;
        """

        rows = [
            (
                a.get("application_number"),
                a.get("sponsor"),
                a.get("brand_name"),
                a.get("generic_name"),
                a.get("submission_type"),
                a.get("submission_number"),
                a.get("submission_status"),
                a.get("submission_status_date"),
                json.dumps(a.get("products", [])),
            )
            for a in approvals
        ]

        extras.execute_values(cur, query, rows)
    conn.commit()
    logger.info(f"Upserted {len(approvals)} FDA approvals into DB")


def main():
    try:
        conn = get_db_connection()
        logger.info("Connected to database")

        approvals = fetch_fda_approvals()

        if approvals:
            upsert_approvals(approvals, conn)
            logger.info("FDA approvals ETL completed successfully!")
        else:
            logger.info("No approvals to process")

    except Exception as e:
        logger.error(f"FDA approvals ETL failed: {e}")
        raise
    finally:
        if "conn" in locals():
            conn.close()


if __name__ == "__main__":
    main()
