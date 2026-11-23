"""Disabled-by-default provider adapter; no generation or billing without explicit gates."""
import json
from pathlib import Path

def generate(prompt, destination, settings=None):
    settings=settings or json.loads((Path(__file__).resolve().parents[1]/'config/settings.json').read_text(encoding='utf-8'))
    cfg=settings.get('ai_image_provider',{})
    if not settings.get('billing_enabled',False) or not settings.get('paid_services_enabled',False) or not cfg.get('enabled',False):
        return {"status":"disabled","generated":False,"reason":"AI görsel sağlayıcısı varsayılan olarak kapalıdır."}
    # This adapter intentionally fails closed until a provider-specific, cost-capped implementation is reviewed.
    raise RuntimeError('AI görsel adaptörü etkinleştirilmiş ancak sağlayıcı uygulaması henüz tanımlı değil; çağrı/faturalandırma yapılmadı.')
