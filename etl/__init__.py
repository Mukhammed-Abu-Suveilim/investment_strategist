"""ETL package for downloading, transforming, and loading market data."""

from etl.pipeline.master_pipeline import run_full_etl

__all__ = ["run_full_etl"]
