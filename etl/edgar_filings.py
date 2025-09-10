#!/usr/bin/env python3
"""
SEC EDGAR Filings ETL Script
Fetches SEC filings from EDGAR RSS and stores in filing table
"""
import os
import requests
import psycopg2
from dotenv import load_dotenv
import logging
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
import re

from db import get_db_connection 

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# SEC EDGAR RSS URL
EDGAR_RSS_URL = "https://www.sec.gov/Archives/edgar/xbrlrss.xml"

def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'db.wahqfdgybivndsplphro.supabase.co'),
        port=os.getenv('DB_PORT', '5432'),
        database=os.getenv('DB_NAME', 'postgres'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD')
    )

def get_tracked_ciks(conn):
    """Get list of CIKs we want to track from companies table"""
    with conn.cursor() as cur:
        cur.execute("SELECT id, cik FROM public.companies WHERE cik IS NOT NULL")
        return {row[1]: row[0] for row in cur.fetchall()}

def fetch_edgar_rss():
    """Fetch EDGAR RSS feed"""
    logger.info("Fetching EDGAR RSS feed...")
    
    headers = {
        'User-Agent': 'PharmaIntel ETL (contact@pharmaintel.com)'  # SEC requires user agent
    }
    
    try:
        response = requests.get(EDGAR_RSS_URL, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Parse XML
        root = ET.fromstring(response.content)
        
        # Extract namespace
        namespace = {'edgar': 'http://www.sec.gov/Archives/edgar'}
        
        filings = []
        items = root.findall('.//item')
        
        for item in items:
            filing = {
                'title': item.find('title').text if item.find('title') is not None else '',
                'link': item.find('link').text if item.find('link') is not None else '',
                'description': item.find('description').text if item.find('description') is not None else '',
                'pub_date': item.find('pubDate').text if item.find('pubDate') is not None else '',
            }
            
            # Extract CIK and form type from description
            desc = filing['description']
            cik_match = re.search(r'CIK:\s*(\d+)', desc)
            form_match = re.search(r'Form Type:\s*([^\s,]+)', desc)
            
            if cik_match and form_match:
                filing['cik'] = cik_match.group(1).zfill(10)  # Pad to 10 digits
                filing['form_type'] = form_match.group(1)
                filings.append(filing)
        
        logger.info(f"Parsed {len(filings)} filings from RSS")
        return filings
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching EDGAR RSS: {str(e)}")
        return []
    except ET.ParseError as e:
        logger.error(f"Error parsing RSS XML: {str(e)}")
        return []

def extract_financial_data(filing_url):
    """Extract basic financial data from filing (simplified)"""
    # This is a simplified version - real implementation would parse XBRL
    # For now, return None values
    return {
        'cash_usd': None,
        'rnd_expense_usd': None,
        'revenue_usd': None
    }

def upsert_filings(filings, tracked_ciks, conn):
    """Upsert filings into database"""
    logger.info("Processing SEC filings...")
    
    relevant_forms = {'10-K', '10-Q', '8-K', '20-F', 'S-1', 'S-3'}
    
    with conn.cursor() as cur:
        processed = 0
        
        for filing in filings:
            cik = filing.get('cik')
            form_type = filing.get('form_type')
            
            # Only process tracked companies and relevant forms
            if cik not in tracked_ciks or form_type not in relevant_forms:
                continue
            
            company_id = tracked_ciks[cik]
            
            try:
                # Parse filing date
                pub_date = filing.get('pub_date', '')
                filing_date = None
                if pub_date:
                    try:
                        filing_date = datetime.strptime(pub_date, '%a, %d %b %Y %H:%M:%S %Z').date()
                    except:
                        try:
                            filing_date = datetime.strptime(pub_date[:25], '%a, %d %b %Y %H:%M:%S').date()
                        except:
                            continue
                
                # Extract financial data (simplified)
                financial_data = extract_financial_data(filing.get('link', ''))
                
                # Upsert filing
                cur.execute("""
                    INSERT INTO public.filings 
                    (company_id, cik, form_type, filing_date, url, cash_usd, rnd_expense_usd, revenue_usd)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (company_id, cik, form_type, filing_date, url) DO UPDATE SET
                        cash_usd = EXCLUDED.cash_usd,
                        rnd_expense_usd = EXCLUDED.rnd_expense_usd,
                        revenue_usd = EXCLUDED.revenue_usd
                """, (
                    company_id, cik, form_type, filing_date, filing.get('link', ''),
                    financial_data['cash_usd'], financial_data['rnd_expense_usd'], 
                    financial_data['revenue_usd']
                ))
                
                processed += 1
                
            except Exception as e:
                logger.warning(f"Error processing filing: {str(e)}")
                continue
        
        conn.commit()
        logger.info(f"Processed {processed} SEC filings")

def main():
    """Main ETL function"""
    try:
        conn = get_db_connection()
        logger.info("Connected to database")
        
        # Get tracked CIKs
        tracked_ciks = get_tracked_ciks(conn)
        logger.info(f"Tracking {len(tracked_ciks)} companies")
        
        if not tracked_ciks:
            logger.info("No companies with CIKs to track")
            return
        
        # Fetch filings
        filings = fetch_edgar_rss()
        
        if filings:
            upsert_filings(filings, tracked_ciks, conn)
            logger.info("EDGAR filings ETL completed successfully!")
        else:
            logger.info("No filings to process")
            
    except Exception as e:
        logger.error(f"ETL failed: {str(e)}")
        raise
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    main()
