from __future__ import annotations
import platform, socket
from .local_outlook import LocalOutlookClient
from ..config import settings

def discover_local():
    result={
        'machine':socket.gethostname(),
        'platform':platform.platform(),
        'outlook':{'installed':False},
        'sharepoint':{'configured':bool(settings.sharepoint_site_id)},
        'pega':{'configured':bool(settings.pega_base_url)},
        'servicenow':{'configured':bool(settings.servicenow_base_url)},
        'monday':{'configured':bool(settings.monday_api_token)},
        'azure_openai':{'configured':bool(settings.azure_openai_endpoint and settings.azure_openai_deployment)},
        'graph':{'configured':bool(settings.tenant_id and settings.client_id and settings.client_secret)},
    }
    if platform.system() == 'Windows':
        result['outlook']=LocalOutlookClient().status()
    return result
