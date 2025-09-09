# PharmaIntel Makefile
# Commands for data ingestion and ETL operations

.PHONY: help seed etl-ctgov-day etl-fda etl-edgar etl-all setup-env install-deps

# Default target
help:
	@echo "PharmaIntel Data Ingestion Commands"
	@echo "==================================="
	@echo ""
	@echo "Setup:"
	@echo "  setup-env        Set up environment variables"
	@echo "  install-deps     Install Python dependencies"
	@echo ""
	@echo "Data Loading:"
	@echo "  seed            Load seed data into database"
	@echo ""
	@echo "ETL Operations:"
	@echo "  etl-ctgov-day   Fetch ClinicalTrials.gov data from last day"
	@echo "  etl-fda         Fetch FDA approvals from last 30 days"
	@echo "  etl-edgar       Fetch SEC EDGAR filings"
	@echo "  etl-all         Run all ETL scripts"
	@echo ""
	@echo "Environment variables required:"
	@echo "  DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD"

# Setup environment
setup-env:
	@echo "Setting up environment..."
	@if [ ! -f .env ]; then \
		echo "Creating .env file template..."; \
		echo "# Database connection" > .env; \
		echo "DB_HOST=db.wahqfdgybivndsplphro.supabase.co" >> .env; \
		echo "DB_PORT=5432" >> .env; \
		echo "DB_NAME=postgres" >> .env; \
		echo "DB_USER=postgres" >> .env; \
		echo "DB_PASSWORD=your_password_here" >> .env; \
		echo ""; \
		echo "# ETL Configuration" >> .env; \
		echo "CTGOV_DAYS_BACK=1" >> .env; \
		echo "FDA_DAYS_BACK=30" >> .env; \
		echo ""; \
		echo "Please edit .env file with your database credentials"; \
	else \
		echo ".env file already exists"; \
	fi

# Install Python dependencies
install-deps:
	@echo "Installing Python dependencies..."
	pip install -r etl/requirements.txt

# Load seed data
seed: install-deps
	@echo "Loading seed data..."
	cd etl && python seed_loader.py

# ETL: ClinicalTrials.gov (daily)
etl-ctgov-day: install-deps
	@echo "Running ClinicalTrials.gov ETL (last day)..."
	cd etl && python ctgov_ingest.py

# ETL: FDA approvals
etl-fda: install-deps
	@echo "Running FDA approvals ETL..."
	cd etl && python approvals_fda.py

# ETL: SEC EDGAR filings
etl-edgar: install-deps
	@echo "Running EDGAR filings ETL..."
	cd etl && python edgar_filings.py

# Run all ETL scripts
etl-all: etl-ctgov-day etl-fda etl-edgar
	@echo "All ETL scripts completed"

# Clean up
clean:
	@echo "Cleaning up..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete