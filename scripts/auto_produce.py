"""Zero-paid-API Turkish history Reels draft generator.

Produces source-controlled claims, 5 original historical illustrations, offline
Turkish Piper narration, estimated SRT, original music, and a narrated vertical MP4.
Output is for human approval ONLY. Nothing uploads to Instagram.
"""
from __future__ import annotations
import argparse, json, os, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path
from scripts.run import ROOT, load_json, select_topic, build
from scripts.illustrate import generate
from scripts.speech import narrate_segments
from scripts.subtitles import create_timed as create_subtitles
from scripts.audio_bed import create as create_bed
from scripts.ai_agents import run_agents
from scripts.create_reel import render_reel,media_duration
from scripts.release_check import check


def verified_facts_only(topic):
    """Source-bound editorial draft: avoid hallucinating details or fake quotes."""
    return ' '.join([
        topic['hook'],
        topic['facts'][0],topic['facts'][1],topic['facts'][2],
        'Bu olayın önemini anlamak için dönemin şartlarını da düşünmek gerekir.',
        topic.get('context','').strip(),
        'Daha fazla bilgi ve kaynaklar için gönderinin açıklamasına bakabilirsin.'
    ]).replace('  ',' ').strip()

def performance_script(topic):
    """Short, spoken Turkish lines with varied pace and clear dramatic beats."""
    if topic['id']=='malazgirt-1071':
        return [
          {'spoken':'Bir meydan... İki ordu... Ve tarihe damga vuran bir gün.','caption':'Bir meydan. İki ordu. Tarihe damga vuran bir gün.','pace':1.00,'pause_after':0.30},
          {'spoken':'Yirmi altı Ağustos, bin yetmiş bir.','caption':'26 AĞUSTOS 1071','pace':0.93,'pause_after':0.28},
          {'spoken':"Malazgirt'te Selçuklu ve Bizans orduları karşı karşıya geldi.",'caption':'Malazgirt’te Selçuklu ve Bizans orduları karşılaştı.','pace':0.99,'pause_after':0.20},
          {'spoken':"Bir tarafta Sultan Alp Arslan'ın ordusu.",'caption':'Sultan Alp Arslan’ın ordusu','pace':0.94,'pause_after':0.20},
          {'spoken':"Diğer tarafta, Bizans İmparatoru Dördüncü Romanos'un kuvvetleri.",'caption':'Bizans İmparatoru IV. Romanos’un kuvvetleri','pace':1.00,'pause_after':0.28},
          {'spoken':'Ve sonuç... Selçuklu ordusu, Bizans kuvvetlerini mağlup etti!','caption':'Sonuç: Selçuklu zaferi','pace':0.92,'pause_after':0.34},
          {'spoken':"Peki, Türklerin Anadolu'ya yerleşmesi bir günde mi tamamlandı? Hayır; bu, uzun bir tarihî süreçti.",'caption':'Türklerin Anadolu’ya yerleşmesi uzun bir süreçti.','pace':1.00,'pause_after':0.25},
          {'spoken':'Malazgirt, bu büyük dönüşümün önemli dönüm noktalarından biriydi.','caption':'Malazgirt: önemli bir dönüm noktası','pace':0.97,'pause_after':0.24},
          {'spoken':'Bir zafer... Ve Anadolu tarihinde yeni bir sayfa.','caption':'Bir zafer. Yeni bir sayfa.','pace':0.92,'pause_after':0.0},
        ]
    # Other topics keep the existing source-bound wording but receive phrase
    # boundaries for readable cadence until a dedicated editorial script exists.
    import re
    clauses=[x.strip() for x in re.split(r'(?<=[.!?])\s+',verified_facts_only(topic)) if x.strip()]
    return [{'spoken':x,'caption':x,'pace':0.98 if i%2==0 else 1.02,'pause_after':0.22} for i,x in enumerate(clauses)]


def optional_free_ai_suggestion(topic,out):
    """Use exactly one free OpenRouter request if a key is supplied; no paid fallback."""
    key=os.getenv('OPENROUTER_API_KEY')
    if not key:return {'status':'not_configured','api_calls':0}
    import requests
    prompt=('Türk tarihi Instagram Reels için yalnız aşağıdaki OL GULARA dayanarak yaratıcı açılış ve ' 
            'en fazla 100 sözcüklük Türkçe konuşma metni öner. Tarih, isim, alıntı, rakam ekleme. ' 
            'Bir iddia belirsizse belirsiz olduğunu açıkla. Çıktıda teklif metnini ver; yayınlama.\n' +
            json.dumps({'hook':topic['hook'],'facts':topic['facts'],'context':topic.get('context')},ensure_ascii=False))
    try:
        r=requests.post('https://openrouter.ai/api/v1/chat/completions',timeout=35,
            headers={'Authorization':f'Bearer {key}','Content-Type':'application/json','X-Title':'Turk Tarihi Draft'},
            json={'model':'openrouter/free','messages':[{'role':'system','content':'You must NOT invent historical facts. Only suggest edits for human review.'},{'role':'user','content':prompt}], 'temperature':.55,'max_tokens':400})
        r.raise_for_status()
        answer=r.json()['choices'][0]['message']['content']
        (out/'AI_SCRIPT_SUGGESTION_REVIEW_REQUIRED.txt').write_text(str(answer),encoding='utf-8')
        return {'status':'suggestion_only_review_required','api_calls':1,'model':'openrouter/free','paid_api_accepted':False}
    except Exception as ex:
        (out/'AI_EDITOR_ERROR.txt').write_text(type(ex).__name__+': '+str(ex)[:150],encoding='utf-8')
        return {'status':'failed_no_fallback','api_calls':1}


def production(topic,out,model_cache,skip_narration=False):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    settings=load_json(ROOT/'config'/'settings.json')
    if settings.get('ai_paid_services_enabled',True) or settings.get('instagram_auto_publish_enabled',True) or not settings.get('human_approval_required',False):
        raise RuntimeError('Zero-cost mode and manual approval gate must remain enabled')
    # 20 actual functional roles perform their tasks in the existing trusted pipeline.
    prev=build(topic,out,video=False)
    segments=performance_script(topic)
    script='\n'.join(item['spoken'] for item in segments)
    (out/'NARRATION_TR.txt').write_text(script,encoding='utf-8')
    ai_result=run_agents(topic,load_json(ROOT/'config'/'agents.json'),out) if os.getenv('ENABLE_20_LLM_AGENTS')=='1' else optional_free_ai_suggestion(topic,out)
    scenes=out/'scenes';generate(topic,scenes)
    manifest={'topic':topic['id'],'utc':datetime.now(timezone.utc).isoformat(),'roles':prev['n_roles'],
        'external_licensed_media':False,'visual_kind':'ORIGINAL_STYLIZED_HISTORICAL_RECONSTRUCTION',
        'historical_facts_manual_verified':False,'instagram_published':False,
        'human_approval_required':True,'paid_api_services_enabled':False,'ai_editor':ai_result,
        'voice_generated':False,'video_generated':False,'subtitle_alignment':'estimated_sentence_timing',
        'ready_for_instagram':False}
    if skip_narration:
        manifest['status']='awaiting_local_tts';(out/'AUTO_REPORT.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
        return manifest
    voice_path=out/'narration.wav'
    cues=narrate_segments(segments,voice_path,model_cache)
    duration=media_duration(voice_path)
    if not 20<=duration<=60:raise ValueError(f'Voice length {duration:.1f}s outside 20-60s, edit script not distort speech')
    create_subtitles(cues,out/'subtitles.srt')
    create_bed(duration,out/'original_soundtrack.wav')
    rendered=out/'reel_with_voice.mp4'
    render_reel(scenes,voice_path,out/'subtitles.srt',rendered)
    final=out/'REVIEW_REQUIRED_REEL.mp4'
    subprocess.run(['ffmpeg','-v','error','-y','-i',str(rendered),'-i',str(out/'original_soundtrack.wav'),
        '-filter_complex','[0:a]volume=1.0[voice];[1:a]volume=0.17[music];[voice][music]amix=inputs=2:duration=first:dropout_transition=0[a]',
        '-map','0:v:0','-map','[a]','-c:v','copy','-c:a','aac','-b:a','160k','-movflags','+faststart',str(final)],check=True,capture_output=True,text=True)
    technical=check(final,voice_path,out/'subtitles.srt',scenes)
    manifest.update({'status':'technical_draft_complete_review_required','video_generated':True,'voice_generated':True,
      'video_file':final.name,'seconds':round(duration,2),'technical_review':technical,'ready_for_instagram':False,
      'visual_scene_count':len(list(scenes.glob('*_scene.jpg'))),'subtitle_alignment':'actual_phrase_audio_timing',
      'narration_style':'phrase-by-phrase delivery; punctuation, planned pauses, modest speed variation; synthetic Piper voice',
      'human_review_checklist':['Tarihî olguları birincil/akademik kaynakta doğrula','Temsili çizimlerin tarih bağlamına uygunluğunu gözden geçir',
        'Türkçe sesin anlaşılır olup olmadığını dinle','Altyazı zamanını gözle kontrol et','Instagram yayın onayını ayrıca ver']})
    (out/'AUTO_REPORT.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    return manifest


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--topic',default='')
    p.add_argument('--out',default='output/auto')
    p.add_argument('--model-cache',default='.cache/piper')
    p.add_argument('--skip-narration',action='store_true',help='Offline dry-run of 20 roles and five illustrated visuals')
    a=p.parse_args()
    topics=load_json(ROOT/'data'/'topics.json');topic=select_topic(topics,a.topic)
    if topic is None:p.error('Unknown topic')
    result=production(topic,a.out,a.model_cache,a.skip_narration)
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
