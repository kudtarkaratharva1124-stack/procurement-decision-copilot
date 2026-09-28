from __future__ import annotations
import requests
from ..config import settings

class PegaConnector:
    def search(self, case_key: str):
        if not settings.pega_base_url: return []
        h={'Authorization':f'Bearer {settings.pega_api_token}'} if settings.pega_api_token else {}
        r=requests.get(settings.pega_base_url.rstrip('/')+settings.pega_rfa_path, params={'caseKey':case_key}, headers=h, timeout=20)
        r.raise_for_status(); return r.json() if isinstance(r.json(), list) else r.json().get('items',[])

class ServiceNowConnector:
    def search(self, case_key: str):
        if not settings.servicenow_base_url: return []
        url=f"{settings.servicenow_base_url.rstrip('/')}/api/now/table/{settings.servicenow_table}"
        r=requests.get(url, params={'sysparm_query':f'number={case_key}','sysparm_limit':10}, auth=(settings.servicenow_client_id,settings.servicenow_client_secret), timeout=20)
        r.raise_for_status(); return r.json().get('result',[])

class MondayConnector:
    def search(self, case_key: str):
        if not settings.monday_api_token: return []
        q='query ($query: String!) { items_page(query_params: {rules: [{column_id: "name", compare_value: [$query], operator: contains_text}]}) { items { id name } } }'
        r=requests.post(settings.monday_api_url, headers={'Authorization':settings.monday_api_token}, json={'query':q,'variables':{'query':case_key}}, timeout=20)
        r.raise_for_status(); return r.json().get('data',{}).get('items_page',{}).get('items',[])
