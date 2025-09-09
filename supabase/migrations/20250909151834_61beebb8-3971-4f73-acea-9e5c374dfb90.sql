-- Core Postgres schema for PharmaIntel
-- Companies
CREATE TABLE public.companies (
  id SERIAL PRIMARY KEY,
  canonical_name TEXT NOT NULL,
  cik TEXT UNIQUE,
  country TEXT,
  website TEXT,
  ticker TEXT,
  market_cap BIGINT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indications (diseases/conditions)
CREATE TABLE public.indications (
  id SERIAL PRIMARY KEY,
  label TEXT NOT NULL,
  mesh_id TEXT,
  icd10 TEXT,
  description TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Targets (proteins, genes)
CREATE TABLE public.targets (
  id SERIAL PRIMARY KEY,
  gene_symbol TEXT,
  uniprot_id TEXT,
  name TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Drugs/Assets
CREATE TABLE public.drugs (
  id SERIAL PRIMARY KEY,
  preferred_name TEXT NOT NULL,
  active_ingredient TEXT,
  mechanism TEXT,
  company_id INTEGER REFERENCES public.companies(id),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Clinical Trials
CREATE TABLE public.trials (
  id TEXT PRIMARY KEY, -- NCT/EUCTR id
  title TEXT,
  phase TEXT CHECK (phase IN ('1','1/2','2','2/3','3','4','N/A')),
  status TEXT,
  start_date DATE,
  primary_completion_date DATE,
  sponsor_company_id INTEGER REFERENCES public.companies(id),
  source TEXT DEFAULT 'clinicaltrials.gov',
  last_updated TIMESTAMPTZ,
  fetched_at TIMESTAMPTZ DEFAULT NOW()
);

-- Drug Approvals
CREATE TABLE public.approvals (
  id SERIAL PRIMARY KEY,
  agency TEXT CHECK (agency IN ('FDA','EMA')),
  approval_date DATE,
  drug_id INTEGER REFERENCES public.drugs(id),
  indication_id INTEGER REFERENCES public.indications(id),
  document_url TEXT,
  application_number TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- SEC Filings
CREATE TABLE public.filings (
  id SERIAL PRIMARY KEY,
  company_id INTEGER REFERENCES public.companies(id),
  cik TEXT,
  form_type TEXT,
  filing_date DATE,
  url TEXT,
  cash_usd NUMERIC,
  rnd_expense_usd NUMERIC,
  revenue_usd NUMERIC,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Epidemiology estimates
CREATE TABLE public.epi_estimates (
  id SERIAL PRIMARY KEY,
  indication_id INTEGER REFERENCES public.indications(id),
  geography TEXT,
  year INTEGER,
  metric TEXT CHECK (metric IN ('incidence','prevalence')),
  value NUMERIC,
  source TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Many-to-many relationships
CREATE TABLE public.trial_indications (
  trial_id TEXT REFERENCES public.trials(id) ON DELETE CASCADE,
  indication_id INTEGER REFERENCES public.indications(id) ON DELETE CASCADE,
  PRIMARY KEY (trial_id, indication_id)
);

CREATE TABLE public.drug_indications (
  drug_id INTEGER REFERENCES public.drugs(id) ON DELETE CASCADE,
  indication_id INTEGER REFERENCES public.indications(id) ON DELETE CASCADE,
  PRIMARY KEY (drug_id, indication_id)
);

CREATE TABLE public.drug_targets (
  drug_id INTEGER REFERENCES public.drugs(id) ON DELETE CASCADE,
  target_id INTEGER REFERENCES public.targets(id) ON DELETE CASCADE,
  PRIMARY KEY (drug_id, target_id)
);

-- Synonyms for entity resolution
CREATE TABLE public.synonyms (
  id SERIAL PRIMARY KEY,
  entity_type TEXT CHECK (entity_type IN ('company','drug','indication','target')),
  canonical_id INTEGER NOT NULL,
  name TEXT NOT NULL,
  source TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(entity_type, name)
);

-- Search materialized view with GIN index
CREATE MATERIALIZED VIEW public.search_mv AS
SELECT 
  'company' as entity_type,
  c.id::text as entity_id,
  c.canonical_name as title,
  COALESCE(c.country || ' pharmaceutical company', 'Pharmaceutical company') as description,
  setweight(to_tsvector('english', c.canonical_name), 'A') ||
  setweight(to_tsvector('english', COALESCE(c.ticker, '')), 'B') ||
  setweight(to_tsvector('english', COALESCE(c.country, '')), 'C') as search_vector
FROM public.companies c
UNION ALL
SELECT 
  'drug' as entity_type,
  d.id::text as entity_id,
  d.preferred_name as title,
  COALESCE(d.mechanism, 'Drug candidate') as description,
  setweight(to_tsvector('english', d.preferred_name), 'A') ||
  setweight(to_tsvector('english', COALESCE(d.active_ingredient, '')), 'B') ||
  setweight(to_tsvector('english', COALESCE(d.mechanism, '')), 'C') as search_vector
FROM public.drugs d
UNION ALL
SELECT 
  'indication' as entity_type,
  i.id::text as entity_id,
  i.label as title,
  COALESCE(i.description, 'Medical condition') as description,
  setweight(to_tsvector('english', i.label), 'A') ||
  setweight(to_tsvector('english', COALESCE(i.description, '')), 'B') ||
  setweight(to_tsvector('english', COALESCE(i.mesh_id, '')), 'C') as search_vector
FROM public.indications i
UNION ALL
SELECT 
  'trial' as entity_type,
  t.id as entity_id,
  t.title as title,
  'Phase ' || COALESCE(t.phase, 'N/A') || ' clinical trial' as description,
  setweight(to_tsvector('english', COALESCE(t.title, '')), 'A') ||
  setweight(to_tsvector('english', COALESCE(t.phase, '')), 'B') ||
  setweight(to_tsvector('english', COALESCE(t.status, '')), 'C') as search_vector
FROM public.trials t;

-- Create GIN index on search vector
CREATE INDEX idx_search_mv_vector ON public.search_mv USING GIN(search_vector);

-- Create other useful indexes
CREATE INDEX idx_trials_completion_date ON public.trials(primary_completion_date);
CREATE INDEX idx_trials_phase ON public.trials(phase);
CREATE INDEX idx_trials_sponsor ON public.trials(sponsor_company_id);
CREATE INDEX idx_approvals_date ON public.approvals(approval_date);
CREATE INDEX idx_filings_date ON public.filings(filing_date);
CREATE INDEX idx_filings_company ON public.filings(company_id);

-- Enable RLS on all tables
ALTER TABLE public.companies ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.indications ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.targets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.drugs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.trials ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.approvals ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.filings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.epi_estimates ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.trial_indications ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.drug_indications ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.drug_targets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.synonyms ENABLE ROW LEVEL SECURITY;

-- Create RLS policies for public read access
CREATE POLICY "Allow public read access" ON public.companies FOR SELECT USING (true);
CREATE POLICY "Allow public read access" ON public.indications FOR SELECT USING (true);
CREATE POLICY "Allow public read access" ON public.targets FOR SELECT USING (true);
CREATE POLICY "Allow public read access" ON public.drugs FOR SELECT USING (true);
CREATE POLICY "Allow public read access" ON public.trials FOR SELECT USING (true);
CREATE POLICY "Allow public read access" ON public.approvals FOR SELECT USING (true);
CREATE POLICY "Allow public read access" ON public.filings FOR SELECT USING (true);
CREATE POLICY "Allow public read access" ON public.epi_estimates FOR SELECT USING (true);
CREATE POLICY "Allow public read access" ON public.trial_indications FOR SELECT USING (true);
CREATE POLICY "Allow public read access" ON public.drug_indications FOR SELECT USING (true);
CREATE POLICY "Allow public read access" ON public.drug_targets FOR SELECT USING (true);
CREATE POLICY "Allow public read access" ON public.synonyms FOR SELECT USING (true);

-- Function to refresh search materialized view
CREATE OR REPLACE FUNCTION refresh_search_mv()
RETURNS void AS $$
BEGIN
  REFRESH MATERIALIZED VIEW CONCURRENTLY public.search_mv;
END;
$$ LANGUAGE plpgsql;

-- Function to update timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for companies updated_at
CREATE TRIGGER update_companies_updated_at
  BEFORE UPDATE ON public.companies
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();