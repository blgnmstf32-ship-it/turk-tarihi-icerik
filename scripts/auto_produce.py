"""Zero-paid-API Turkish history Reels draft generator.

Uses the source-bound script, Gemini Charon alone, aligned captions, and original
sound design for a narrated vertical MP4.
Output is for human approval ONLY. Nothing uploads to Instagram.
"""
from __future__ import annotations
import argparse, json, shutil, subprocess
from datetime import datetime, timezone
from pathlib import Path
from scripts.run import ROOT, load_json, select_topic, build
from scripts.illustrate import generate
from scripts.gemini_tts import MODEL, VOICE, narrate
from scripts.subtitles import create_timed as create_subtitles
from scripts.audio_bed import create as create_bed
from scripts.ai_agents import run_agents
from scripts.create_reel import render_reel,media_duration
from scripts.release_check import check
from scripts.commons_media import fetch_visuals,write_attribution
from scripts.voice_provider import select_provider
from scripts.task_observer import record
from scripts.three_scene import plan_3d_scenes, render_with_2d_fallback, save_plan
from scripts.editorial_board import run_board
from scripts.reels_editorial import write_review


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
    if topic.get('narration'):
        return [
            {'spoken': line, 'caption': line, 'pace': 1.0, 'pause_after': 0.22}
            for line in topic['narration']
        ]
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
        '-filter_complex',
        '[1:a]aformat=sample_rates=48000:channel_layouts=mono,asplit=2[voice][key];'
        '[2:a]aformat=sample_rates=48000:channel_layouts=mono,volume=0.18[bed];'
        '[bed][key]sidechaincompress=threshold=0.022:ratio=8:attack=14:release=430[duck];'
        '[voice][duck]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.89:level=0:latency=1[a]',
        '-map','0:v:0','-map','[a]','-c:v','copy','-c:a','aac','-b:a','160k','-movflags','+faststart',str(final)]


def update_3d_role_results(role_modules,status):
    """Record actual 3D render and fallback outcomes for the two downstream roles."""
    result=list(role_modules)
    render_text={
        'rendered':'Three.js sahneleri Remotion çıktısına eklendi',
        'fallback_2d_after_3d_failure':'3D render başarısız; 2D fallback başarıyla seçildi',
        'not_applicable_2d_only':'Bu konu için 3D gerekmedi; 2D akış kullanıldı',
    }.get(status,'3D render henüz çalışmadı')
    qc_text=('3D katmanı ve 2D fallback kontrol edildi; manuel tarih/görsel incelemesi gerekli'
             if status=='rendered' else '2D fallback/konu sınıflandırması kontrol edildi; manuel tarih/görsel incelemesi gerekli')
    for item in result:
        if item.get('id')==23:item['result']=render_text
        if item.get('id')==24:item['result']=qc_text
    return result


def production(topic,out,model_cache=None,skip_narration=False,recordings_dir=None,voice_provider_override=None,
               gemini_free_project=False, use_staged_experts=False, approved_voice=None):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    settings=load_json(ROOT/'config'/'settings.json')
    record('production_started',{'topic':topic.get('id'),'out':str(out)})
    if settings.get('ai_paid_services_enabled',True) or settings.get('instagram_auto_publish_enabled',True) or not settings.get('human_approval_required',False):
        raise RuntimeError('Zero-cost mode and manual approval gate must remain enabled')
    if recordings_dir or model_cache and not skip_narration:
        raise ValueError('Yalnızca Gemini Charon anlatımı kullanılır.')
    provider=select_provider(settings,voice_provider_override)
    segments=performance_script(topic)
    if approved_voice is None and topic['id']=='piri-reis-kayip-kaynak':
        approved_voice=ROOT/'data'
    original_hook = topic.get("hook")
    replaces_plain_hook = bool(original_hook) and segments[0]["spoken"] in {
        original_hook, f"{original_hook} Bugün yanıtı kaynaklara bağlı kalarak arıyoruz.",
    }
    review_script = [item["spoken"] for item in segments]
    if replaces_plain_hook and approved_voice is None:
        review_script[0] = original_hook
    review = write_review(out, topic, "tarih", review_script, fixed_recording=approved_voice is not None)
    selected = review["best"]
    apply_hook = not (skip_narration or approved_voice or topic.get("narration"))
    if apply_hook:
        # Keep authored facts in order and preserve existing performance directions.
        if replaces_plain_hook:
            segments = segments[1:]
        segments = [{"spoken": selected["opening"], "caption": selected["opening"],
                     "pace": 1.0, "pause_after": 0.22}, *segments]
    script='\n'.join(item['spoken'] for item in segments)
    voice_path=out/'narration.wav'
    voice_info={}
    if not skip_narration:
        try:
            cues=narrate(segments,voice_path,gemini_free_project,approved_voice=approved_voice,voice_info=voice_info)
            duration=media_duration(voice_path)
            hook_seconds=round(cues[0]['end'],2)
            if not 60<=duration<=75 or hook_seconds>3:
                raise ValueError(f'Anlatım {duration:.2f} sn, açılış {hook_seconds:.2f} sn; süre koşulu sağlanmadı.')
        except (RuntimeError, ValueError, OSError) as exc:
            failure={'topic':topic['id'],'stage':'narration','status':'stopped','provider':provider,
                     'voice':VOICE,'error':str(exc),'video_generated':False,'instagram_published':False}
            (out/'VOICE_FAILURE.json').write_text(json.dumps(failure,ensure_ascii=False,indent=2),encoding='utf-8')
            raise
    prev=build(topic,out,video=False)
    three_d_plan=plan_3d_scenes(topic,70)
    save_plan(three_d_plan,out/'3D_SCENE_PLAN.json')
    (out/'NARRATION_TR.txt').write_text(script,encoding='utf-8')
    # The coordinator researches and scores options every run. LLM use remains
    # a separate, explicit free-model opt-in; no key alone triggers a request.
    editorial_path=out/'editorial'/'EDITORIAL_DECISION_REPORT.json'
    editorial_report=load_json(editorial_path) if editorial_path.exists() else run_board(out/'editorial')
    agents = load_json(ROOT/'config/agents.json')
    expert_path = out/'AI_AGENTS_STATUS.json'
    staged = load_json(expert_path) if use_staged_experts else {}
    # CI supplies the report from the isolated specialist step. Local opt-in runs it here.
    if use_staged_experts and (staged.get('topic') != topic['id'] or 'dispatch' not in staged):
        raise ValueError('Uzman raporu seçilen konuya ait değil.')
    ai_result = staged if use_staged_experts else run_agents(topic, agents, out, settings=settings,
                                                            editorial=editorial_report, media_review=True)
    editorial_stages = editorial_report.get('coordinator_llm', {}).get('stages', [])
    coordinator_called = any(stage['role']=='AI Genel Yayın Yönetmeni' and stage.get('actual_llm_used')
                             for stage in editorial_stages)
    execution_report={'coordinator':'AI Genel Yayın Yönetmeni','coordinator_actual_llm_used':coordinator_called,
        'editorial_llm_stages':[{key:stage.get(key) for key in ('role','model','status','actual_llm_used','http_status','response_source','error_type','attempts')}
                                for stage in editorial_stages],
        'specialist_calls_including_editor':ai_result['calls'],
        'original_20_llm_calls':sum(len(row['attempts']) for row in ai_result['roles']),
        'original_20_llm_successes':ai_result['separate_llm_roles_completed'],
        'coordinator_dispatch':ai_result['dispatch'], 'coordinator_comparison':ai_result['comparison'],
        'paid_api_calls':0,'paid_fallback':False}

    def write_execution_report(render_status=None):
        suggestions = {row['role_id']: row for row in ai_result['roles']}
        rules = {row['id']: row['result'] for row in prev.get('roles_completed', [])}
        rows = []
        for role in agents:
            role_id = role['id']
            llm = suggestions.get(role_id, {'status': 'not_run', 'reason': 'deterministic_3d_module',
                                           'actual_llm_used': False, 'attempts': []})
            ran_rules = role_id in rules and (role_id <= 22 or
                (role_id == 23 and render_status in {'rendered','fallback_2d_after_3d_failure'}) or
                (role_id == 24 and render_status is not None))
            kind = ('real_llm' if llm['actual_llm_used'] else
                    'deterministic_automation' if ran_rules else 'not_run')
            rows.append({'id': role_id, 'name': role['name'], 'actual_llm_used': llm['actual_llm_used'],
                         'execution': kind, 'status': llm['status'] if llm['status'] != 'not_run' else
                         ('automation_completed' if ran_rules else 'not_run'),
                         'automation': {'status': 'completed', 'result': rules[role_id]} if ran_rules else {'status': 'not_run'},
                         'llm': llm})
        execution_report['roles'] = rows
        (out/'AI_AGENT_EXECUTION_REPORT.json').write_text(json.dumps(execution_report,ensure_ascii=False,indent=2),encoding='utf-8')

    write_execution_report()
    scenes=out/'scenes';generate(topic,scenes)
    licensed_visuals=[]
    if not skip_narration:
        commons_dir=out/'commons_visuals'
        licensed_visuals=fetch_visuals(topic,commons_dir,limit=10)
        for i, item in enumerate(licensed_visuals, 1):
            placeholder = scenes / f"{i:02d}_scene.jpg"
            placeholder.unlink()
            shutil.copy2(commons_dir/item["file"], scenes/item["file"])
        write_attribution(licensed_visuals, out/"MEDIA_ATTRIBUTION.md")
    visual_kind = ("OPEN_LICENSED_DOCUMENTARY_MEDIA" if len(licensed_visuals) >= 10 else
        "MIXED_LICENSED_MEDIA_AND_LABELED_GRAPHICS" if licensed_visuals else "LABELED_STYLIZED_RECONSTRUCTION_FALLBACK")
    manifest={'topic':topic['id'],'utc':datetime.now(timezone.utc).isoformat(),'roles':prev['n_roles'],
        'target_duration_seconds':{'min':60,'max':75},
        'first_hook_seconds':None,
        'external_licensed_media':bool(licensed_visuals),'visual_kind':visual_kind,
        'licensed_visual_count':len(licensed_visuals),'realistic_visuals_gate':'passed' if len(licensed_visuals)>=10 else 'not_met_fallback_requires_manual_visual_upgrade',
        'historical_facts_manual_verified':False,'instagram_published':False,
        'human_approval_required':True,'paid_api_services_enabled':False,'ai_editor':ai_result,
        'voice_generated':False,'video_generated':False,'subtitle_alignment':'estimated_sentence_timing',
        'ready_for_instagram':False,'editorial_decision_report':'editorial/EDITORIAL_DECISION_REPORT.md',
        'ai_agent_execution_report':'AI_AGENT_EXECUTION_REPORT.json',
        'reels_editorial_review':'REELS_EDITORIAL_REVIEW.json',
        'editorial_index':review['best']['total'],
        'applied_hook_family':selected['hook_family'] if apply_hook else None,
        'editorial_coordinator_llm':editorial_report['coordinator_llm'],
        'three_d':{**three_d_plan,'status':'planned_not_rendered' if three_d_plan.get('scenes') else 'not_applicable_2d_only'}}
    if skip_narration:
        manifest['status']='awaiting_local_tts';(out/'AUTO_REPORT.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
        return manifest
    voice_mode=voice_info['source']
    manifest['voice_generation'] = {**voice_info,'pace_and_pauses':'model',
                                    'billing_guard':'approved_take' if approved_voice is not None else 'operator_confirms_unbilled_project'}
    manifest['first_hook_seconds']=hook_seconds
    create_subtitles(cues,out/'subtitles.srt')
    create_bed(duration,out/'original_soundtrack.wav', maritime=topic['id']=='piri-reis-kayip-kaynak')
    rendered=out/'reel_with_voice.mp4'
    _, three_d_result=render_with_2d_fallback(render_reel,scenes,voice_path,out/'subtitles.srt',rendered,
                                               three_scenes=three_d_plan.get('scenes',[]),
                                               edit={'title':topic['title'],'topic':topic['id'],
                                                     'hook':segments[0]['caption']})
    three_d_render_status=three_d_result['status']
    if three_d_result.get('error'):
        (out/'THREE_D_RENDER_FAILURE.txt').write_text(three_d_result['error']+'\n2D fallback render succeeded.',encoding='utf-8')
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
      'visual_scene_count':len(list(scenes.glob('*.jpg'))),'subtitle_alignment':'local_asr_compact_cues',
      'renderer':'Remotion scenes and animated captions; FFmpeg narration/music mux and H.264/AAC encoding',
      'fps':30,'resolution':'1080x1920','narration_style':'Turkish documentary Charon',
      'voice_source':voice_mode,'voice_provider':provider,'natural_voice_human_review_required':True,'optional_audits':optional_audits,
      'three_d':{**three_d_plan,**three_d_result,'scene_count_rendered':len(three_d_plan.get('scenes',[])) if three_d_render_status=='rendered' else 0},
      'role_modules':update_3d_role_results(prev.get('roles_completed',[]),three_d_render_status),
      'target_duration_seconds':{'min':60,'max':75},
      'human_review_checklist':['Tarihî olguları birincil/akademik kaynakta doğrula',visual_review,
        'Türkçe sesin anlaşılır olup olmadığını dinle','Altyazı zamanını gözle kontrol et','Instagram yayın onayını ayrıca ver']})
    write_execution_report(three_d_render_status)
    (out/'AUTO_REPORT.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    record('production_finished',{'topic':topic.get('id'),'status':manifest.get('status'),'technical_gate':technical.get('technical_gate'),'duration':duration,'voice_provider':provider})
    return manifest


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--topic',default='')
    p.add_argument('--out',default='output/auto')
    p.add_argument('--approved-voice',type=Path,help='Onaylı Charon WAV dosyası ve üretim kaydının bulunduğu klasör')
    p.add_argument('--skip-narration',action='store_true',help='Offline dry-run of 24 task modules, ten illustrations and the 3D scene plan')
    p.add_argument('--voice-provider',choices=['gemini_tts'],default='gemini_tts')
    p.add_argument('--confirm-gemini-free-project', action='store_true',
                   help='Confirm this Gemini API key belongs to an AI Studio project without billing')
    p.add_argument('--use-staged-experts', action='store_true', help='Read the report produced by scripts.ai_agents')
    a=p.parse_args()
    editorial_path = Path(a.out)/"editorial"/"EDITORIAL_DECISION_REPORT.json"
    report = load_json(editorial_path) if editorial_path.exists() else run_board(editorial_path.parent)
    topics=load_json(ROOT/'data'/'topics.json')
    topic=select_topic(topics,a.topic,report)
    if topic is None:p.error('Unknown topic')
    try:
        result=production(topic,a.out,skip_narration=a.skip_narration,voice_provider_override=a.voice_provider,
                          gemini_free_project=a.confirm_gemini_free_project,use_staged_experts=a.use_staged_experts,
                          approved_voice=a.approved_voice)
    except Exception as exc:
        record('production_failed',{'topic':topic.get('id'),'error':f'{type(exc).__name__}: {exc}'})
        raise
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
