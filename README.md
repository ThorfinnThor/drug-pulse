# PharmaIntel

A comprehensive pharmaceutical strategy intelligence platform that provides insights into clinical trials, drug approvals, SEC filings, and market analysis.

## Features

- **Global Search**: Search across trials, companies, drugs, and indications
- **Trial Intelligence**: Track clinical trial phases and upcoming readouts
- **Market Forecasting**: rNPV calculations with transparent assumptions
- **ETL Pipeline**: Automated data ingestion from public APIs
- **Admin Dashboard**: Owner-only access to ETL management

## Architecture

- **Frontend**: React + TypeScript + Tailwind CSS
- **Backend**: Supabase (PostgreSQL) + FastAPI
- **ETL**: Python scripts for data ingestion
- **Analytics**: dbt models for data transformation

## Getting Started

### Prerequisites

- Node.js & npm
- Python 3.11+
- Access to Supabase project

### Installation

```sh
# Clone the repository
git clone <YOUR_GIT_URL>
cd <YOUR_PROJECT_NAME>

# Install frontend dependencies
npm install

# Install ETL dependencies
pip install -r etl/requirements.txt

# Start development server
npm run dev
```

### Environment Setup

Create a `.env` file with your database credentials:

```env
# Database connection
DB_HOST=db.wahqfdgybivndsplphro.supabase.co
DB_PORT=5432
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=your_password_here

# ETL Configuration
CTGOV_DAYS_BACK=1
FDA_DAYS_BACK=30
```

## ETL Operations

### Running ETL Locally

Load initial seed data:
```sh
make seed
```

Run individual ETL scripts:
```sh
make etl-ctgov-day    # ClinicalTrials.gov data (last day)
make etl-fda          # FDA approvals (last 30 days)
make etl-edgar        # SEC EDGAR filings
```

Run all ETL scripts:
```sh
make etl-all
```

### ETL Scripts

- **`etl/ctgov_ingest.py`**: Fetches clinical trials from ClinicalTrials.gov API v2
- **`etl/approvals_fda.py`**: Fetches drug approvals from openFDA API
- **`etl/edgar_filings.py`**: Fetches SEC filings from EDGAR RSS feed

### Admin Dashboard

Access `/admin` with owner privileges to:
- Manually trigger ETL scripts
- View execution history and status
- Monitor data pipeline health

### Automated ETL

GitHub Actions runs nightly at 2 AM UTC:
- Executes all ETL scripts in sequence
- Refreshes search materialized view
- Sends notifications on failure

## API Endpoints

### Public Endpoints
- `GET /api/search?q={query}` - Global search
- `GET /api/indications/{id}` - Indication details with trial funnel
- `POST /api/forecast` - rNPV calculation

### Admin Endpoints (Owner Only)
- `POST /api/admin/run/{etl}` - Run ETL script (ctgov|fda|edgar)
- `GET /api/admin/etl-history` - View ETL execution history

## Database Schema

### Core Tables
- `companies` - Pharmaceutical companies with CIKs
- `drugs` - Drug information and mechanisms
- `indications` - Medical conditions and classifications
- `trials` - Clinical trials data
- `approvals` - FDA drug approvals
- `filings` - SEC financial filings

### Auth & Admin
- `user_roles` - Role-based access control (owner|admin|user)
- `profiles` - User profile information
- `etl_executions` - ETL run logs and status

## dbt Models

Analytics models in `dbt/models/`:
- `v_trial_funnel_by_indication` - Trial counts by phase
- `v_upcoming_readouts` - Trials completing in next 12 months

## Technologies

- **Frontend**: Vite, React, TypeScript, shadcn-ui, Tailwind CSS
- **Backend**: Supabase, FastAPI, PostgreSQL
- **ETL**: Python, requests, psycopg2, BeautifulSoup
- **Analytics**: dbt, PostgreSQL materialized views
- **CI/CD**: GitHub Actions

## Deployment

Deploy via [Lovable](https://lovable.dev/projects/8555b1f1-6669-48ea-908a-dfd149bad115):
1. Click Share → Publish
2. Optionally connect custom domain in Project → Settings → Domains

## Development

This project supports:
- Real-time collaboration via Lovable
- GitHub integration with bidirectional sync
- Local development with your preferred IDE
- Visual editing of UI components

## License

Built with [Lovable](https://lovable.dev) - AI-powered web app development.
