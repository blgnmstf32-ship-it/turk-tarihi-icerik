"""Fail-closed Turkish narration provider selector. Paid clouds are opt-in per run."""
from __future__ import annotations
import json, os, subprocess, sys, urllib.request
from pathlib import Path

def select_provider(settings=None, requested=None):
    settings=settings or json.loads((Path(__file__).resolve().parents[1]/'config/settings.json').read_text(encoding='utf-8'))
    provider=(requested or os.getenv('TURK_TARIHI_VOICE_PROVIDER') or settings.get('voice_provider','piper')).lower()
    if provider in ('piper','human_recording'): return provider
    if provider == 'gemini_tts':
        raise RuntimeError('Gemini yalnız açık --voice-provider gemini_tts seçimiyle çağrılır.')
    cloud=settings.get('cloud_voice',{}).get(provider,{})
    if not settings.get('billing_enabled',False) or not settings.get('paid_services_enabled',False) or not settings.get('cloud_voice_enabled',False) or not cloud.get('enabled',False) or float(settings.get('monthly_spend_limit_try',0))<=0:
        raise RuntimeError(f'{provider} kapalı; ücretsiz Piper/insan kaydı seçin. Ücretli sağlayıcıya otomatik geçiş yok.')
    if provider=='google_chirp3_hd' and not os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
        raise RuntimeError('Google Chirp için açıkça sağlanmış ADC kimlik bilgisi yok; ücretli yedek kullanılmadı.')
    if provider=='azure_speech' and not os.getenv('AZURE_SPEECH_KEY'):
        raise RuntimeError('Azure Speech anahtarı yok; ücretli yedek kullanılmadı.')
    return provider

def synthesize(text, output, provider, settings=None):
    """Synthesize when explicitly configured. Never fallback to another cloud."""
    output=Path(output); output.parent.mkdir(parents=True,exist_ok=True)
    if provider=='piper':
        from scripts.speech import narrate
        return narrate(text,output,settings.get('piper_model_cache','.cache/piper') if settings else '.cache/piper')
    if provider=='human_recording': raise ValueError('İnsan kaydı sağlayıcısı cümle WAV dosyalarıyla scripts.speech.narrate_segments üzerinden çalışır.')
    if provider=='google_chirp3_hd':
        import google.auth
        from google.auth.transport.requests import AuthorizedSession
        creds,_=google.auth.default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
        endpoint='https://texttospeech.googleapis.com/v1/text:synthesize'
        voice=(settings or {}).get('cloud_voice',{}).get(provider,{}).get('voice','tr-TR-Chirp3-HD-Achird')
        payload={"input":{"text":text},"voice":{"languageCode":"tr-TR","name":voice},"audioConfig":{"audioEncoding":"LINEAR16","speakingRate":0.96}}
        response=AuthorizedSession(creds).post(endpoint,json=payload,timeout=60); response.raise_for_status()
        import base64
        output.write_bytes(base64.b64decode(response.json()['audioContent']))
        return output
    if provider=='azure_speech':
        region=os.getenv('AZURE_SPEECH_REGION','')
        if not region: raise RuntimeError('AZURE_SPEECH_REGION belirtilmedi; başka sağlayıcıya geçilmedi.')
        voice=(settings or {}).get('cloud_voice',{}).get(provider,{}).get('voice','tr-TR-AhmetNeural')
        ssml=f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="tr-TR"><voice name="{voice}"><mstts:express-as style="excited" styledegree="1.15"><prosody rate="-4%">{text}</prosody></mstts:express-as></voice></speak>'
        req=urllib.request.Request(f'https://{region}.tts.speech.microsoft.com/cognitiveservices/v1',data=ssml.encode(),headers={
            'Ocp-Apim-Subscription-Key':os.environ['AZURE_SPEECH_KEY'],'Content-Type':'application/ssml+xml','X-Microsoft-OutputFormat':'riff-24khz-16bit-mono-pcm'})
        with urllib.request.urlopen(req,timeout=60) as res: output.write_bytes(res.read())
        return output
    raise ValueError('Bilinmeyen ses sağlayıcısı: '+provider)
