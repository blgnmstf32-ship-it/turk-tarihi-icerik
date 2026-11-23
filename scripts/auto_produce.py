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
from scripts.commons_media import fetch_visuals,write_attribution
from scripts.voice_provider import select_provider
from scripts.task_observer import record


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
    """Build a 60-75s sourced documentary script with marked performance beats."""
    if topic['id']=='malazgirt-1071':
        lines=[
          ('Bir tarih düşünün... Ve Anadolu tarihinin akışında iz bırakan bir karşılaşma.','Bir tarih. Bir karşılaşma.',0.98,0.38),
          ("1071'de Anadolu'nun tarihinde ne değişti? Önce kesin bilgilere bakalım.",'1071’de Anadolu’da ne değişti?',0.97,0.30),
          ('Yirmi altı Ağustos, bin yetmiş bir. Malazgirt’te Selçuklu ve Bizans orduları karşı karşıya geldi.','26 AĞUSTOS 1071 • MALAZGİRT',0.95,0.34),
          ('Bir tarafta Sultan Alp Arslan’ın ordusu vardı. Diğer tarafta, Bizans İmparatoru Dördüncü Romanos’un kuvvetleri.','Alp Arslan ve IV. Romanos',1.00,0.28),
          ('Bu karşılaşmanın sonucu açıktı: Sultan Alp Arslan’ın ordusu, Bizans kuvvetlerini mağlup etti.','Sonuç: Selçuklu zaferi',0.94,0.42),
          ('Malazgirt’i önemli kılan, savaşın sonucunun Anadolu tarihi içindeki yeridir.','Zaferin Anadolu tarihindeki yeri',1.02,0.25),
          ('Zafer, Türklerin Anadolu’ya yerleşme sürecinde önemli bir dönüm noktası kabul edilir.','Önemli bir dönüm noktası',0.96,0.35),
          ('Malazgirt, uzun bir dönüşümün kritik aşamalarından biridir. Anadolu’nun tarihi tek bir savaşla başlamadı.','Dönüm noktası… ama uzun bir süreç',0.99,0.36),
          ('Bu nedenle savaşın sonucunu, bütün değişimin bir günde tamamlanması gibi anlatmamak gerekir.','Bir günde tamamlanmadı',0.96,0.30),
          ("Baştaki soruya dönelim: 1071'de Anadolu'nun tarihinde ne değişti? Bir zafer ve uzun bir dönüşüm.",'1071: zafer ve tarihî dönüşüm',0.95,0.30),
          ('Yirmi altı Ağustos 1071. Malazgirt. Bir dönüm noktası ve uzun bir tarihî süreç.','26 AĞUSTOS 1071 • MALAZGİRT',0.93,0.0),
        ]
    else:
        f1,f2,f3=topic['facts']
        lines=[
          (f"{topic['hook']} Bugün yanıtı kaynaklara bağlı kalarak arıyoruz.",topic['hook'],0.98,0.36),
          ('Önce tarih ve yer: '+f1,f1,0.96,0.35),
          ('İkinci önemli nokta, olayın taraflarını gösteriyor: '+f2,f2,1.00,0.30),
          ('Üçüncü bilgi ise tarihî anlamı açıklıyor: '+f3,f3,0.95,0.38),
          ('Bu bilgiler olayın temel çizgisini verir. Tarihi anlamak için dönemin bağlamını da görmek gerekir.','Temel olgular ve tarihî bağlam',1.02,0.30),
          (topic.get('context',''),'Dönemin bağlamı',0.98,0.36),
          ('Bilgiyle yorumu ayıralım; kesin olmayan ayrıntıları kesinmiş gibi aktarmayalım.','Bilgi ve yorum ayrı tutulmalı',0.97,0.32),
          ('Bu nedenle tarihi, dönemi ve sonucu birlikte akılda tutalım.','Tarih • dönem • sonuç',1.00,0.28),
          (f"Baştaki soruya dönelim. {topic['title']} başlığını tarih, taraflar ve sonuçla birlikte değerlendirelim.",topic['title'],0.95,0.0),
        ]
    return [{'spoken':spoken,'caption':caption,'pace':pace,'pause_after':pause}
            for spoken,caption,pace,pause in lines]


def audio_mix_command(rendered_video,narration,music,final):
    """Mux narration explicitly; Remotion renders visuals/captions without audio."""
    return ['ffmpeg','-v','error','-y','-i',str(rendered_video),'-i',str(narration),'-i',str(music),
        '-filter_complex','[1:a]volume=1.0[voice];[2:a]volume=0.12[music];[voice][music]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,alimiter=limit=0.98[a]',
        '-map','0:v:0','-map','[a]','-c:v','copy','-c:a','aac','-b:a','160k','-movflags','+faststart',str(final)]


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


def production(topic,out,model_cache,skip_narration=False,recordings_dir=None,voice_provider_override=None):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    settings=load_json(ROOT/'config'/'settings.json')
    record('production_started',{'topic':topic.get('id'),'out':str(out)})
    if settings.get('ai_paid_services_enabled',True) or settings.get('instagram_auto_publish_enabled',True) or not settings.get('human_approval_required',False):
        raise RuntimeError('Zero-cost mode and manual approval gate must remain enabled')
    # 20 actual functional roles perform their tasks in the existing trusted pipeline.
    provider=select_provider(settings,voice_provider_override)
    prev=build(topic,out,video=False)
    segments=performance_script(topic)
    script='\n'.join(item['spoken'] for item in segments)
    (out/'NARRATION_TR.txt').write_text(script,encoding='utf-8')
    ai_result=run_agents(topic,load_json(ROOT/'config'/'agents.json'),out) if os.getenv('ENABLE_20_LLM_AGENTS')=='1' else optional_free_ai_suggestion(topic,out)
    scenes=out/'scenes';generate(topic,scenes)
    licensed_visuals=[]
    if not skip_narration:
        commons_dir=out/'commons_visuals'
        licensed_visuals=fetch_visuals(topic,commons_dir,limit=10)
        if len(licensed_visuals)>=10:
            import shutil
            shutil.rmtree(scenes,ignore_errors=True);scenes.mkdir(parents=True,exist_ok=True)
            for item in licensed_visuals:shutil.copy2(commons_dir/item['file'],scenes/item['file'])
        else:
            import shutil
            shutil.rmtree(commons_dir,ignore_errors=True)
        write_attribution(licensed_visuals if len(licensed_visuals)>=10 else [],out/'MEDIA_ATTRIBUTION.md')
    visual_kind='OPEN_LICENSED_DOCUMENTARY_MEDIA' if len(licensed_visuals)>=10 else 'LABELED_STYLIZED_RECONSTRUCTION_FALLBACK'
    manifest={'topic':topic['id'],'utc':datetime.now(timezone.utc).isoformat(),'roles':prev['n_roles'],
        'target_duration_seconds':{'min':60,'max':75},
        'external_licensed_media':bool(len(licensed_visuals)>=10),'visual_kind':visual_kind,
        'licensed_visual_count':len(licensed_visuals),'realistic_visuals_gate':'passed' if len(licensed_visuals)>=10 else 'not_met_fallback_requires_manual_visual_upgrade',
        'historical_facts_manual_verified':False,'instagram_published':False,
        'human_approval_required':True,'paid_api_services_enabled':False,'ai_editor':ai_result,
        'voice_generated':False,'video_generated':False,'subtitle_alignment':'estimated_sentence_timing',
        'ready_for_instagram':False}
    if skip_narration:
        manifest['status']='awaiting_local_tts';(out/'AUTO_REPORT.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
        return manifest
    voice_path=out/'narration.wav'
    if recordings_dir:
        voice_mode='human_recordings'
    else:
        voice_mode='free_offline_piper_synthetic' if provider=='piper' else provider
    guide='İnsan seslendirmesi için her satırı ayrı kaydedin; 01.wav, 02.wav, ... adlarını kullanın.\n\n'
    guide+='\n'.join(f"{i+1:02d}.wav — {item['spoken']}" for i,item in enumerate(segments))+'\n'
    (out/'VOICE_RECORDING_GUIDE.txt').write_text(guide,encoding='utf-8')
    cues=narrate_segments(segments,voice_path,model_cache,recordings_dir,provider,settings)
    duration=media_duration(voice_path)
    if not 60<=duration<=75:raise ValueError(f'Voice length {duration:.1f}s outside 60-75s; expand/rewrite narration, never time-stretch')
    create_subtitles(cues,out/'subtitles.srt')
    create_bed(duration,out/'original_soundtrack.wav')
    rendered=out/'reel_with_voice.mp4'
    render_reel(scenes,voice_path,out/'subtitles.srt',rendered)
    final=out/'REVIEW_REQUIRED_REEL.mp4'
    subprocess.run(audio_mix_command(rendered,voice_path,out/'original_soundtrack.wav',final),check=True,capture_output=True,text=True)
    technical=check(final,voice_path,out/'subtitles.srt',scenes)
    optional_audits={}
    if settings.get('speech_audit_enabled',False):
        from scripts.speech_audit import compare_subtitles
        optional_audits['speech']=compare_subtitles(voice_path,out/'subtitles.srt')
    if settings.get('scene_audit_enabled',False):
        from scripts.scene_audit import audit
        optional_audits['scenes']=audit(final)
    visual_review=('Lisanslı tarihî görselin anlatıdaki dönem/olayla eşleşmesini ve her atfı doğrula' if len(licensed_visuals)>=10
                   else 'Temsilî çizimleri tarih bağlamı ve etiketleri açısından incele; fotoğraf diye sunma')
    manifest.update({'status':'technical_draft_complete_review_required','video_generated':True,'voice_generated':True,
      'video_file':final.name,'seconds':round(duration,2),'technical_review':technical,'ready_for_instagram':False,
      'visual_scene_count':len(list(scenes.glob('*.jpg'))),'subtitle_alignment':'actual_phrase_audio_timing',
      'renderer':'Remotion scenes and animated captions; FFmpeg narration/music mux and H.264/AAC encoding',
      'fps':30,'resolution':'1080x1920','narration_style':'Turkish documentary direction; short phrases, planned pauses, varied pace, rising/falling emphasis; Piper fallback remains synthetic',
      'voice_source':voice_mode,'voice_provider':provider,'natural_voice_human_review_required':voice_mode!='human_recordings','optional_audits':optional_audits,
      'target_duration_seconds':{'min':60,'max':75},
      'human_review_checklist':['Tarihî olguları birincil/akademik kaynakta doğrula',visual_review,
        'Türkçe sesin anlaşılır olup olmadığını dinle','Altyazı zamanını gözle kontrol et','Instagram yayın onayını ayrıca ver']})
    (out/'AUTO_REPORT.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    record('production_finished',{'topic':topic.get('id'),'status':manifest.get('status'),'technical_gate':technical.get('technical_gate'),'duration':duration,'voice_provider':provider})
    return manifest


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--topic',default='')
    p.add_argument('--out',default='output/auto')
    p.add_argument('--model-cache',default='.cache/piper')
    p.add_argument('--voice-recordings',default='',help='Optional folder with one human-recorded phrase per file: 01.wav, 02.wav, ...')
    p.add_argument('--skip-narration',action='store_true',help='Offline dry-run of 20 roles and ten illustrated visuals')
    p.add_argument('--voice-provider',default='',help='piper, google_chirp3_hd or azure_speech; paid cloud providers fail closed by default')
    a=p.parse_args()
    topics=load_json(ROOT/'data'/'topics.json');topic=select_topic(topics,a.topic)
    if topic is None:p.error('Unknown topic')
    try:
        result=production(topic,a.out,a.model_cache,a.skip_narration,a.voice_recordings or None,a.voice_provider or None)
    except Exception as exc:
        record('production_failed',{'topic':topic.get('id'),'error':f'{type(exc).__name__}: {exc}'})
        raise
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
