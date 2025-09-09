#!/usr/bin/env python3
"""
FastAPI endpoints for PharmaIntel
Provides REST API for search and data access
"""
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="PharmaIntel API",
    description="Pharmaceutical strategy intelligence API",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class SearchResult(BaseModel):
    type: str
    id: str
    label: str
    description: str

class SearchResponse(BaseModel):
    q: str
    hits: List[SearchResult]

class TrialFunnelItem(BaseModel):
    phase: str
    n: int

class LateStageTrialItem(BaseModel):
    trial_id: str
    phase: str
    primary_completion_date: Optional[str]

class IndicationResponse(BaseModel):
    indication: Dict[str, Any]
    funnel: List[TrialFunnelItem]
    late_stage_trials: List[LateStageTrialItem]

class ForecastRequest(BaseModel):
    patients: int
    treatment_rate: float
    price_per_year: float
    duration_years: float
    pos: float
    wacc: float
    competition_factor: float
    years_to_launch: int

class ForecastResponse(BaseModel):
    peak_sales: float
    rnpv: float
    assumptions: Dict[str, Any]

# Database connection
def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'db.wahqfdgybivndsplphro.supabase.co'),
        port=os.getenv('DB_PORT', '5432'),
        database=os.getenv('DB_NAME', 'postgres'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD'),
        cursor_factory=RealDictCursor
    )

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "PharmaIntel API is running", "timestamp": datetime.now().isoformat()}

@app.get("/api/search", response_model=SearchResponse)
async def search(q: str):
    """Global search endpoint using materialized view"""
    if not q or len(q.strip()) < 2:
        raise HTTPException(status_code=400, detail="Query must be at least 2 characters")
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Use PostgreSQL full-text search
            cur.execute("""
                SELECT entity_type, entity_id, title, description
                FROM public.search_mv
                WHERE search_vector @@ plainto_tsquery('english', %s)
                ORDER BY ts_rank(search_vector, plainto_tsquery('english', %s)) DESC
                LIMIT 20
            """, (q, q))
            
            results = cur.fetchall()
            
        conn.close()
        
        hits = [
            SearchResult(
                type=row['entity_type'],
                id=row['entity_id'],
                label=row['title'],
                description=row['description']
            )
            for row in results
        ]
        
        return SearchResponse(q=q, hits=hits)
        
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        raise HTTPException(status_code=500, detail="Search failed")

@app.get("/api/indications/{indication_id}", response_model=IndicationResponse)
async def get_indication(indication_id: int):
    """Get indication details with funnel and late-stage trials"""
    try:
        conn = get_db_connection()
        
        # Get indication details
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, label, description, mesh_id, icd10
                FROM public.indications
                WHERE id = %s
            """, (indication_id,))
            
            indication = cur.fetchone()
            if not indication:
                raise HTTPException(status_code=404, detail="Indication not found")
        
        # Get funnel data
        with conn.cursor() as cur:
            cur.execute("""
                SELECT phase, trial_count as n
                FROM public.v_trial_funnel_by_indication
                WHERE indication_id = %s
                ORDER BY CASE phase 
                    WHEN '1' THEN 1
                    WHEN '1/2' THEN 2
                    WHEN '2' THEN 3
                    WHEN '2/3' THEN 4
                    WHEN '3' THEN 5
                    WHEN '4' THEN 6
                    ELSE 7
                END
            """, (indication_id,))
            
            funnel_data = cur.fetchall()
        
        # Get late-stage trials
        with conn.cursor() as cur:
            cur.execute("""
                SELECT t.id as trial_id, t.phase, t.primary_completion_date
                FROM public.trials t
                JOIN public.trial_indications ti ON t.id = ti.trial_id
                WHERE ti.indication_id = %s
                    AND t.phase IN ('2/3', '3')
                    AND t.primary_completion_date >= CURRENT_DATE
                ORDER BY t.primary_completion_date
                LIMIT 10
            """, (indication_id,))
            
            late_stage = cur.fetchall()
        
        conn.close()
        
        return IndicationResponse(
            indication=dict(indication),
            funnel=[TrialFunnelItem(phase=row['phase'], n=row['n']) for row in funnel_data],
            late_stage_trials=[
                LateStageTrialItem(
                    trial_id=row['trial_id'],
                    phase=row['phase'],
                    primary_completion_date=row['primary_completion_date'].isoformat() if row['primary_completion_date'] else None
                )
                for row in late_stage
            ]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Indication endpoint error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch indication data")

@app.post("/api/forecast", response_model=ForecastResponse)
async def calculate_forecast(request: ForecastRequest):
    """Calculate rNPV forecast with transparent assumptions"""
    try:
        # Simple rNPV calculation
        peak_sales = (
            request.patients * 
            request.treatment_rate * 
            request.price_per_year * 
            request.duration_years * 
            request.competition_factor
        )
        
        rnpv = peak_sales * request.pos / ((1 + request.wacc) ** request.years_to_launch)
        
        assumptions = {
            "inputs": request.dict(),
            "calculations": {
                "peak_sales_formula": "patients × treatment_rate × price_per_year × duration_years × competition_factor",
                "rnpv_formula": "peak_sales × pos / (1 + wacc)^years_to_launch"
            },
            "timestamp": datetime.now().isoformat()
        }
        
        return ForecastResponse(
            peak_sales=round(peak_sales, 2),
            rnpv=round(rnpv, 2),
            assumptions=assumptions
        )
        
    except Exception as e:
        logger.error(f"Forecast calculation error: {str(e)}")
        raise HTTPException(status_code=500, detail="Forecast calculation failed")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)