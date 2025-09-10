#!/usr/bin/env python3
"""
FastAPI endpoints for PharmaIntel
Provides REST API for search and data access
"""
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime
import subprocess
import asyncio
import jwt
from functools import wraps

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Security
security = HTTPBearer()

app = FastAPI(
    title="PharmaIntel API",
    description="Pharmaceutical strategy intelligence API with admin endpoints",
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

class AdminETLResponse(BaseModel):
    status: str
    message: str
    execution_id: Optional[str] = None

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

# JWT Authentication
def verify_jwt_token(token: str) -> Dict[str, Any]:
    """Verify Supabase JWT token and extract user info"""
    try:
        # Decode without verification for now (Supabase handles verification)
        # In production, you should verify with Supabase's JWT secret
        payload = jwt.decode(token, options={"verify_signature": False})
        return payload
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def check_owner_role(user_id: str) -> bool:
    """Check if user has owner role"""
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT EXISTS(SELECT 1 FROM public.user_roles WHERE user_id = %s AND role = 'owner')",
                (user_id,)
            )
            result = cur.fetchone()
            return result[0] if result else False
    except Exception as e:
        logger.error(f"Role check error: {str(e)}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

async def get_current_owner(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Dependency to get current owner user"""
    try:
        payload = verify_jwt_token(credentials.credentials)
        user_id = payload.get('sub')
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")
            
        if not check_owner_role(user_id):
            raise HTTPException(status_code=403, detail="Owner access required")
            
        return user_id
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(status_code=401, detail="Authentication failed")

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

# Admin Routes
@app.post("/api/admin/run/{etl_type}", response_model=AdminETLResponse)
async def run_etl(etl_type: str, current_user: str = Depends(get_current_owner)):
    """Run ETL script - owner only"""
    
    if etl_type not in ['ctgov', 'fda', 'edgar']:
        raise HTTPException(status_code=400, detail="Invalid ETL type. Must be one of: ctgov, fda, edgar")
    
    # Map ETL type to script filename
    script_map = {
        'ctgov': 'ctgov_ingest.py',
        'fda': 'approvals_fda.py', 
        'edgar': 'edgar_filings.py'
    }
    
    script_name = script_map[etl_type]
    execution_id = None
    
    try:
        # Log ETL execution start
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO public.etl_executions (etl_type, status, executed_by)
                VALUES (%s, 'running', %s)
                RETURNING id
            """, (etl_type, current_user))
            execution_id = cur.fetchone()[0]
            conn.commit()
        conn.close()
        
        # Run ETL script
        script_path = f"etl/{script_name}"
        if not os.path.exists(script_path):
            raise FileNotFoundError(f"ETL script not found: {script_path}")
            
        # Run the ETL script
        process = subprocess.run(
            ['python', script_path],
            cwd='.',
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        # Update execution status
        conn = get_db_connection()
        with conn.cursor() as cur:
            if process.returncode == 0:
                cur.execute("""
                    UPDATE public.etl_executions 
                    SET status = 'success', completed_at = now()
                    WHERE id = %s
                """, (execution_id,))
                status = "success"
                message = f"ETL {etl_type} completed successfully"
            else:
                error_msg = process.stderr or "Unknown error"
                cur.execute("""
                    UPDATE public.etl_executions 
                    SET status = 'failed', completed_at = now(), error_message = %s
                    WHERE id = %s
                """, (error_msg, execution_id))
                status = "failed"
                message = f"ETL {etl_type} failed: {error_msg}"
                raise HTTPException(status_code=500, detail=message)
            
            conn.commit()
        conn.close()
        
        return AdminETLResponse(
            status=status,
            message=message,
            execution_id=str(execution_id)
        )
        
    except subprocess.TimeoutExpired:
        # Update status to failed on timeout
        if execution_id:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE public.etl_executions 
                    SET status = 'failed', completed_at = now(), error_message = 'Timeout'
                    WHERE id = %s
                """, (execution_id,))
                conn.commit()
            conn.close()
        raise HTTPException(status_code=500, detail="ETL script timeout")
        
    except Exception as e:
        # Update status to failed on error
        if execution_id:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE public.etl_executions 
                    SET status = 'failed', completed_at = now(), error_message = %s
                    WHERE id = %s
                """, (str(e), execution_id))
                conn.commit()
            conn.close()
        
        logger.error(f"ETL execution error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"ETL execution failed: {str(e)}")

@app.get("/api/admin/etl-history")
async def get_etl_history(current_user: str = Depends(get_current_owner)):
    """Get ETL execution history - owner only"""
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, etl_type, status, started_at, completed_at, error_message, records_processed
                FROM public.etl_executions
                ORDER BY started_at DESC
                LIMIT 50
            """)
            
            executions = cur.fetchall()
        conn.close()
        
        return {"executions": [dict(row) for row in executions]}
        
    except Exception as e:
        logger.error(f"ETL history error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch ETL history")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)