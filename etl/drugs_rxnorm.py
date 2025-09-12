import os
import requests
import psycopg2
from psycopg2.extras import execute_values

RXNORM_BASE = "https://rxnav.nlm.nih.gov/REST"

def get_db_connection():
    return psycopg2.connect(dsn=os.environ["DATABASE_URL"])

def fetch_drugs(conn, limit=100):
    """
    Fetch drugs without RxNorm enrichment.
    """
    query = """
        SELECT id, product_ndc, brand_name, generic_name, substance_name
        FROM drugs
        WHERE rxnorm_id IS NULL
        LIMIT %s;
    """
    with conn.cursor() as cur:
        cur.execute(query, (limit,))
        return cur.fetchall()

def fetch_rxnorm_data(ndc):
    """
    Fetch RxNorm data for a given NDC.
    """
    url = f"{RXNORM_BASE}/rxcui.json?idtype=NDC&id={ndc}"
    r = requests.get(url)
    if r.status_code != 200:
        return None
    data = r.json()
    if "idGroup" not in data or "rxnormId" not in data["idGroup"]:
        return None
    rxcui = data["idGroup"]["rxnormId"][0]

    # Fetch properties (name, synonyms, TTY)
    props_url = f"{RXNORM_BASE}/rxcui/{rxcui}/allProperties.json?prop=names"
    r2 = requests.get(props_url)
    if r2.status_code != 200:
        return {"rxnorm_id": rxcui}
    props = r2.json()

    preferred_name, generic_name, brand_name = None, None, None
    ingredients, synonyms = [], []

    for item in props.get("propConceptGroup", {}).get("propConcept", []):
        name = item.get("propValue")
        tty = item.get("propName")

        if tty in ["SCD", "SBD"] and not preferred_name:
            preferred_name = name
        if tty == "IN":
            if not generic_name:
                generic_name = name
            ingredients.append(name)
        if tty == "BN" and not brand_name:
            brand_name = name

        synonyms.append(name)

    return {
        "rxnorm_id": rxcui,
        "preferred_name": preferred_name,
        "generic_name": generic_name,
        "brand_name": brand_name,
        "active_ingredient": ", ".join(ingredients) if ingredients else None,
        "synonyms": ", ".join(set(synonyms)) if synonyms else None,
    }

def upsert_rxnorm(conn, updates):
    """
    Update drug rows with RxNorm enrichment.
    """
    query = """
        UPDATE drugs
        SET rxnorm_id = data.rxnorm_id,
            preferred_name = COALESCE(data.preferred_name, drugs.preferred_name),
            generic_name = COALESCE(data.generic_name, drugs.generic_name, drugs.substance_name),
            brand_name = COALESCE(data.brand_name, drugs.brand_name),
            active_ingredient = COALESCE(data.active_ingredient, drugs.substance_name, drugs.generic_name),
            synonyms = COALESCE(data.synonyms, drugs.synonyms)
        FROM (VALUES %s) AS data(
            id, rxnorm_id, preferred_name, generic_name, brand_name, active_ingredient, synonyms
        )
        WHERE drugs.id = data.id::int;
    """
    with conn.cursor() as cur:
        execute_values(cur, query, updates)
    conn.commit()

def enrich_rxnorm(batch_size=100):
    """
    Main enrichment function.
    """
    conn = get_db_connection()
    drugs = fetch_drugs(conn, limit=batch_size)
    updates = []

    for drug_id, ndc, existing_brand, existing_generic, existing_substance in drugs:
        info = fetch_rxnorm_data(ndc)

        if not info:
            # no hit → fallback to existing FDA data
            updates.append((
                drug_id,
                None,
                existing_brand or existing_generic or existing_substance,
                existing_generic or existing_substance,
                existing_brand,
                existing_substance or existing_generic,
                None
            ))
            continue

        updates.append((
            drug_id,
            info["rxnorm_id"],
            info["preferred_name"] or existing_brand or existing_generic or existing_substance,
            info["generic_name"] or existing_generic or existing_substance,
            info["brand_name"] or existing_brand,
            info["active_ingredient"] or existing_substance or existing_generic,
            info["synonyms"]
        ))

    if updates:
        upsert_rxnorm(conn, updates)
        print(f"✅ Updated {len(updates)} drugs with RxNorm info")
    else:
        print("ℹ️ No updates this batch")

    conn.close()

if __name__ == "__main__":
    enrich_rxnorm(batch_size=100)
