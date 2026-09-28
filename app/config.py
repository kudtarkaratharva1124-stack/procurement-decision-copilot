from __future__ import annotations
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


def csv_env(name: str, default: str) -> list[str]:
    return [x.strip() for x in os.getenv(name, default).split(',') if x.strip()]

@dataclass(frozen=True)
class Settings:
    app_env: str = os.getenv('APP_ENV', 'development')
    host: str = os.getenv('APP_HOST', '127.0.0.1')
    port: int = int(os.getenv('APP_PORT', '8000'))
    secret_key: str = os.getenv('SECRET_KEY', 'dev-only-change-me')
    database_url: str = os.getenv('DATABASE_URL', 'sqlite:///./data/copilot.db')
    demo_mode: bool = os.getenv('DEMO_MODE', 'true').lower() == 'true'
    tenant_id: str = os.getenv('TENANT_ID', '')
    client_id: str = os.getenv('CLIENT_ID', '')
    client_secret: str = os.getenv('CLIENT_SECRET', '')
    graph_user_id: str = os.getenv('GRAPH_USER_ID', 'me')
    graph_scopes: str = os.getenv('GRAPH_SCOPES', 'https://graph.microsoft.com/.default')
    azure_openai_endpoint: str = os.getenv('AZURE_OPENAI_ENDPOINT', '')
    azure_openai_api_key: str = os.getenv('AZURE_OPENAI_API_KEY', '')
    azure_openai_api_version: str = os.getenv('AZURE_OPENAI_API_VERSION', '2025-04-01-preview')
    azure_openai_deployment: str = os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME', os.getenv('AZURE_OPENAI_DEPLOYMENT', ''))
    rfa_reference_dir: str = os.getenv('RFA_REFERENCE_DIR', './data/rfa_reference')
    sharepoint_site_id: str = os.getenv('SHAREPOINT_SITE_ID', '')
    sharepoint_drive_id: str = os.getenv('SHAREPOINT_DRIVE_ID', '')
    sharepoint_search_root: str = os.getenv('SHAREPOINT_SEARCH_ROOT', '')
    pega_base_url: str = os.getenv('PEGA_BASE_URL', '')
    pega_api_token: str = os.getenv('PEGA_API_TOKEN', '')
    pega_rfa_path: str = os.getenv('PEGA_RFA_PATH', '/prweb/api/rfa/v1/requests')
    servicenow_base_url: str = os.getenv('SERVICENOW_BASE_URL', '')
    servicenow_client_id: str = os.getenv('SERVICENOW_CLIENT_ID', '')
    servicenow_client_secret: str = os.getenv('SERVICENOW_CLIENT_SECRET', '')
    servicenow_table: str = os.getenv('SERVICENOW_TABLE', 'change_request')
    monday_api_url: str = os.getenv('MONDAY_API_URL', 'https://api.monday.com/v2')
    monday_api_token: str = os.getenv('MONDAY_API_TOKEN', '')
    rfa_prefixes: tuple[str, ...] = tuple(csv_env('RFA_PREFIXES', 'RFA,RFAWO,RFACU,RFAMW,RFAPN,RFASTND,RFASP,MOU,RFAFN'))
    schedule_interval_minutes: int = int(os.getenv('SCHEDULE_INTERVAL_MINUTES', '3'))
    outlook_local_enabled: bool = os.getenv('OUTLOOK_LOCAL_ENABLED', 'true').lower() == 'true'
    outlook_poll_top: int = int(os.getenv('OUTLOOK_POLL_TOP', '50'))
    outlook_attachment_dir: str = os.getenv('OUTLOOK_ATTACHMENT_DIR', './data/attachments')

settings = Settings()
