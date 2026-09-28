import os
os.environ['APP_ENV']='test'; os.environ['DEMO_MODE']='true'; os.environ['DATABASE_URL']='sqlite:///./data/test.db'
from app.services.cases import classify

def test_classify_rfa():
    assert classify('RFA - Procurement Approval') == 'RFA'

def test_classify_non_rfa():
    assert classify('Weekly update') is None

def test_default_scheduler_interval_is_three_minutes():
    from app.config import settings
    assert settings.schedule_interval_minutes == 3
