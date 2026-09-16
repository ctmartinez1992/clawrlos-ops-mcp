import os

# Settings() validates required fields at import time; unit tests that only
# exercise scrapers/ranking (no real Supabase calls) still trigger that import
# chain, so provide harmless placeholders before anything under test is imported.
os.environ.setdefault("SUPABASE_URL", "https://unit-test.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "unit-test-key")
