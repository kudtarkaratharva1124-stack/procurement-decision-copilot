from __future__ import annotations
import json
from pathlib import Path

class VoiceProfileService:
    def __init__(self, path='data/voice_profiles.json'):
        self.path=Path(path)
    def get(self, user='default'):
        if not self.path.exists(): return {'user':user,'style':'professional, concise, evidence-led','avoid':['unsupported claims','overconfident decisions']}
        try:
            data=json.loads(self.path.read_text())
            return data.get(user,data.get('default',{}))
        except Exception: return {'user':user,'style':'professional, concise, evidence-led'}
