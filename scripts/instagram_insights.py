"""Read-only future Instagram Insights scaffolding. No posting endpoint exists here."""
import json, os
from pathlib import Path

def get_insights(*_args, **_kwargs):
    settings=json.loads((Path(__file__).resolve().parents[1]/'config/settings.json').read_text(encoding='utf-8'))
    if not settings.get('instagram_insights_enabled',False) or os.getenv('INSTAGRAM_INSIGHTS_ENABLED')!='1' or os.getenv('IG_INSIGHTS_ACCESS_TOKEN','')=='':
        return {'status':'disabled','read_only':True,'published':False}
    raise RuntimeError('Insights adapter is a placeholder; credentials and read-only scope must be reviewed before use.')
