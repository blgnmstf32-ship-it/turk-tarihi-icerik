"""Render the four outstanding 15G reels as source-linked, offline review media."""
from __future__ import annotations

import argparse
from difflib import SequenceMatcher
from functools import lru_cache
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import wave

import numpy as np

from scripts import audio_bed, capacity_15b as batch, gemini_tts, scene_director as director
from scripts import pilot_media_measure as measure, pilot_scene_repair as repair, video_quality_lab as lab
from scripts.approved_pilot_replay import _timeline
from scripts.auto_produce import audio_mix_command
from scripts.editorial_state import EditorialState
from scripts.final_media_qa import Measurements, checked_frame_video, metrics
from scripts.reels_editorial import review
from scripts.subtitles import create_timed

FPS = 30
VISUALS = {
    'kultepe-kil-borc-kaydi': {0: 'kultepe-kapanis.jpg', 1: 'kultepe-kapanis.jpg', 6: 'kultepe-borc.jpg'},
    'ife-heykel-mum-kalip': {1: 'ife-bas.jpg', 7: 'ife-bas.jpg'},
    'firca-kurutma-duzeni': {2: 'firca-durulama.mp4'},
    'goz-makyaji-aplikatoru': {0: 'makyaj-fircalari.mp4', 2: 'makyaj-fircalari.mp4'},
}
PROOF = {
    'kultepe-kil-borc-kaydi': ['Kil tablet|Gümüş borcu','Katalogdaki ölçek|Avuç içi','Gümüş|Ödeme|Borç kaydı',
        'Kil zarf|İç tablet','Tanık adı|Mühür izi','Tüccar|İşlem|Yazı','Borç senedi|Ayrı belge',
        'Tüccar evi|Kil arşivi','Tek işlem|Genelleme sınırı','The Met|Tablet ve zarf'],
    'ife-heykel-mum-kalip': ['Mum model|Metal örnek','Ife|Nijerya','Pişmiş toprak|Bakır alaşımı',
        'Geçici mum model|Yüz ayrıntısı','Kil kabuk|Yüzey izi','Mum çıkar|Kalıp boşluğu kalır',
        'Metal|Kalıp boşluğu|Soğuma','Yüz çizgileri|Modelin izi','Biçim|Kimlik belirsiz','The Met|Teknik inceleme'],
    'firca-kurutma-duzeni': ['Fırçanı düz yatır|Ucu dışarıda','Ürün kalıntısı|Temizlik günü','Ilık akan su|Yalnız fırça ucu',
        'Nazik yıkama|Ucu temizle','Durula|Berrak su','Kuru kâğıt havlu|Nazikçe tampon',
        'Düz havlu|Uç tezgâh dışında','Sap birleşimi|Dik kurutmadan kaçın','Fırçanı paylaşma|Süren tahrişte dermatolog',
        'AAD|Makyaj fırçası bakımı'],
    'goz-makyaji-aplikatoru': ['Aplikatörün temiz mi?','Göz çevresine uygun|Etiketi oku','Elini yıka|Temiz uç kullan',
        'Kişisel aplikatör|Paylaşma','Tester|Tek kullanımlık uç','Sabit bir yer|Araç hareket etmiyor',
        'Kapağı kapat|Saklama koşulu','Ürün|Eller|Aplikatör','Tahrişte kullanımı bırak','FDA|Göz kozmetiği güvenliği'],
}
HINTS = {
    'kultepe-kil-borc-kaydi': 'Kültepe, Aşur-taklaku, The Met, gümüş borcu, tablet zarfı ve mühür.',
    'ife-heykel-mum-kalip': 'Ife, Nijerya, Yoruba, pişmiş toprak, bakır, kayıp mum dökümü, The Met.',
    'firca-kurutma-duzeni': 'Makyaj fırçası, Amerikan Dermatoloji Akademisi, nazik kurutma.',
    'goz-makyaji-aplikatoru': 'Göz kozmetiği, aplikatör, tester, FDA ve tahriş.',
}
ASR_SPELLINGS = {'66':'altmış altı','245':'iki yüz kırk beş','16':'on altı','16a':'on altı a',
                 '7':'yedi','10':'on','fırçağın':'fırçan','mazörneyi':'mağaza örneği'}
FOLD = str.maketrans('çğıöşü', 'cgiosu')


def tokens(text):
    return [word.translate(FOLD) for token in gemini_tts._tokens(text)
            for word in ASR_SPELLINGS.get(token, token).split()]


def transcribe(path, model, key):
    segments, _ = model.transcribe(str(path), language='tr', vad_filter=False, beam_size=5,
                                   word_timestamps=True, initial_prompt=HINTS[key])
    heard = list(segments)
    return {'language':'tr', 'segments':[{'text':s.text,'start':s.start,'end':s.end} for s in heard],
            'words':[{'text':w.word,'start':w.start,'end':w.end} for s in heard for w in s.words]}


def matches(expected, transcript):
    heard = [(word,w['start'],w['end']) for w in transcript['words']
             for word in tokens(w['text']) if word != 'tire']
    actual = [w[0] for w in heard]
    found = {}
    for tag,a,b,c,d in SequenceMatcher(None,expected,actual,autojunk=False).get_opcodes():
        if tag == 'equal':
            found.update({i:heard[c+i-a][1:] for i in range(a,b)})
        if tag == 'replace' and b-a == 1 and 1 <= d-c <= 2 and a and b < len(expected) and c and d < len(heard):
            joined = ''.join(actual[c:d])
            if expected[a] == joined or (len(expected[a]) >= 6 and SequenceMatcher(None,expected[a],joined).ratio() >= .83):
                found[a] = heard[c][1], heard[d-1][2]
        if tag == 'replace' and b-a == 2 and d-c == 1 and ''.join(expected[a:b]) == actual[c]:
            found.update({i:heard[c][1:] for i in range(a,b)})
    return found


def align(lines, speech, duration):
    clean=tokens(' '.join(lines))
    mapped=matches(clean,speech)
    if len(mapped) < .7*len(clean):
        raise ValueError('The recorded Turkish script has insufficient matching words')
    cues,cuts,offset=[],[],0
    for line in lines:
        words=line.split()
        indices=[]
        for word in words:
            indices.append(offset)
            offset+=len(tokens(word))
        hits=[mapped[i] for i in indices if i in mapped]
        if indices[0] not in mapped or len(hits) < .60*len(words):
            raise ValueError(f'Scene {len(cuts)+1} lacks a measured speech anchor')

        @lru_cache(maxsize=None)
        def split(at):
            if at==len(words):
                return ()
            for size in (5,6,4,7,3,8,2,1):
                next_index=at+size
                if next_index>len(words) or len(' '.join(words[at:next_index]))>48:
                    continue
                if next_index<len(words) and (indices[next_index] not in mapped or
                    mapped[indices[next_index]][0] < mapped[indices[at]][0]+.36):
                    continue
                rest=split(next_index)
                if rest is not None:
                    return (next_index,*rest)
            return None

        divisions=split(0)
        if not divisions:
            raise ValueError('No in-bounds subtitle division matches the recorded speech')
        start=0
        for end in divisions:
            cues.append({'start':mapped[indices[start]][0],
                         'end':min(duration,max(x[1] for x in hits)) if end==len(words) else mapped[indices[end]][0],
                         'text':' '.join(words[start:end]), 'wordStarts':[mapped.get(x,(duration+1,))[0] for x in indices[start:end]]})
            start=end
        cuts.append(round(mapped[indices[0]][0]*FPS))
    return cues,[min(cuts[1],90),*cuts[2:],math.ceil(duration*FPS)]


def load_assets(key, out):
    rows=director._read(batch.ROOT/'data/capacity_15g_input.json')['assets']
    selected={row['file']:row for row in rows if row['topic']==key}
    if selected.keys() != set(VISUALS[key].values()):
        raise ValueError('The reviewed archive inventory changed')
    out.mkdir(parents=True,exist_ok=True)
    for name,row in selected.items():
        if Path(name).name != name or not row['preview_frame_reviewed']:
            raise ValueError('The asset lacks a reviewed receipt')
        destination=out/name
        subprocess.run(['curl','-fsSL','--proto','=https','--retry','2','--max-time','45','--max-filesize','20000000',
                        '--user-agent','TurkHistoryEditorial/1.0 (archival attribution)',row['media_url'],'-o',str(destination)],check=True)
        actual=batch.digest(destination)
        if actual != row['sha256']:
            if name != 'kultepe-kapanis.jpg':
                raise ValueError(f'Asset checksum changed: {name}')
            from PIL import Image
            with Image.open(destination) as pic:
                if pic.format!='JPEG' or list(pic.size)!=row['size']:
                    raise ValueError('Met asset delivery is outside its reviewed format')
                pic.verify()
        row['delivered_sha256']=actual
    batch.write(out/'ATTRIBUTION.json', selected)


def adopted_plan(key, lines, cuts):
    plan=director._read(batch.ROOT/'data/capacity_15g_input.json')['plans'][key]
    if lines!=[s['narration']['text'] for s in plan['scenes']] or len(cuts)!=len(plan['scenes']) or len(cuts)!=10:
        raise ValueError('Approved planned scenes and narration diverged')
    for index,(scene,start,end) in enumerate(zip(plan['scenes'],[0,*cuts],cuts)):
        if end<=start:
            raise ValueError('The measured scene boundaries are not ordered')
        scene.update(start_frame=start,end_frame=end,start_seconds=round(start/FPS,4),end_seconds=round(end/FPS,4),
                     approved_visual={'archive_index':index,'shot':index})
        scene['captions']['timing']='measured_recording'
        scene['render']['illustration_frames']=min(scene['render']['illustration_frames'],end-start)
    plan.update(duration_frames=cuts[-1], transitions=director._cuts(plan['scenes']))
    return plan


def render(props, assets, browser, output, log, span=None):
    prop_file=output.parent/'props.json'
    batch.write(prop_file,props)
    cmd=[str(batch.ROOT/'node_modules/.bin/remotion'),'render','remotion/daily15g_index.tsx','DailyReel15G',str(output),
         '--props',str(prop_file),'--public-dir',str(assets),f'--browser-executable={browser}',
         '--codec=h264','--muted','--concurrency=2','--gl=swangle','--log=error','--license-key=free-license']
    if span:
        cmd.append(f'--frames={span[0]}-{span[1]-1}')
    env={name:os.environ[name] for name in ('PATH','HOME','LANG','TMPDIR','DO_NOT_TRACK') if name in os.environ}
    env.update(NODE_OPTIONS=f"--require={batch.ROOT/'scripts/remotion_node_compat.cjs'}",REMOTION_FORCE_LOOPBACK_NETWORK='1')
    with log.open('a') as stream:
        subprocess.run(cmd,cwd=batch.ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT,check=True,timeout=1000)


def evidence(video, plan, captions, voice, state, model, speech=None):
    speech=transcribe(video,model,plan['topic']['id']) if speech is None else speech
    raw=metrics(video,captions,model,timeline=True,transcript=speech)
    starts=matches(tokens(' '.join(cue['text'] for cue in captions)),speech)
    index=0
    offsets=[]
    for cue,item in zip(captions,raw['cue_matches']):
        onset=starts[index][0] if index in starts else None
        offset=None if onset is None else abs(onset-cue['start'])*1000
        if offset is not None:
            offsets.append(offset)
        item.update(spoken_start=onset,offset_ms=offset)
        index+=len(tokens(cue['text']))
    report,samples=measure.collect(video,plan,captions,raw,voice,
        caption_measure=lambda frame,_brand,cv2: repair.caption_panel_pixels(frame,'tarih',cv2))
    observations=report['observations']
    for row in observations.get('mobile_readability',[]):
        row['values'].pop('glyph_bounds_phone_px',None)
    mobile=[sample['sampled_phone_pixels'] for sample in samples['mobile_subtitle_samples'] if sample['sampled_phone_pixels']]
    if len(mobile)==len(captions):
        observations['mobile_readability'].append(measure._observation('mobile_readability',{
            'safe_area_violations':sum(x['safe_area_violations'] for x in mobile),
            'min_contrast_ratio':min(x['min_contrast_ratio'] for x in mobile)},collector='opencv-caption-pixels'))
    if offsets:
        observations.setdefault('subtitle_sync',[]).append(measure._observation('subtitle_sync',{
            'matched_fraction':len(offsets)/len(captions),'p95_offset_ms':float(np.percentile(offsets,95))}))
    observed={round(s*FPS) for s in raw['scenes']['starts_s'] if s>0}
    cuts=[]
    for boundary in plan['transitions']:
        target=boundary['frame']
        nearby=[frame for frame in observed if abs(frame-target)<=6]
        chosen=min(nearby,key=lambda f:abs(f-target)) if nearby else None
        observed.discard(chosen)
        cuts.append({'id':boundary['id'],'planned_frame':target,'observed_frame':chosen,
                     'error_frames':7 if chosen is None else abs(chosen-target)})
    observations['transitions']=[measure._observation('transitions',{'max_boundary_error_frames':max(c['error_frames'] for c in cuts),
                                                                       'unexpected_cuts':len(observed)})]
    result,_=lab.evaluate(plan,evidence=report,state=state)
    result['actual']={'subtitle_max_ms':max(offsets,default=None),'subtitle_measured':len(offsets),'caption_count':len(captions),
                      'mobile_measured':len(mobile),'cut_details':cuts,'unplanned_cuts':sorted(observed),'samples':samples,
                      'cue_matches':raw['cue_matches'],'speech':raw['asr']}
    return result,speech


def passes(report):
    observed=report['actual']
    return (report['technical']['status']=='pass' and observed['subtitle_max_ms'] is not None
            and observed['subtitle_max_ms']<=350 and observed['subtitle_measured']==observed['mobile_measured']==observed['caption_count'])


def animate(video, clip, start, end):
    filter_graph=(f"[0:v]split[base][card];[card]crop=900:784:90:500,zoompan=z='1+.16*on/{max(end-start-1,1)}':"
                  "x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=1:s=900x784:fps=30[moving];"
                  "[base][moving]overlay=90:500:shortest=1[out]")
    subprocess.run(['ffmpeg','-nostdin','-v','error','-threads','2','-ss',f'{start/FPS:.9f}','-i',str(video),
                    '-filter_complex_threads','2','-filter_complex',filter_graph,'-map','[out]','-frames:v',str(end-start),
                    '-an','-c:v','libx264','-preset','ultrafast','-threads','2','-qp','0',str(clip)],check=True,timeout=90)


def recover(video, plan, props, prior, result, speech, state, voice, model, assets, browser, work, log):
    cues=props['captions']
    measured=result['actual']
    indices=[i for i,cue in enumerate(measured['cue_matches']) if cue['offset_ms'] is not None and cue['offset_ms']>350]
    new_cues,timing_spans=repair.retime(cues,measured['cue_matches'],indices)
    freezes=[i['frames'] for i in result['issues'] if i['check']=='frozen_frames' and i['frames']]
    changes={}
    for s in props['shots']:
        intersects=lambda spans:any(s['start']<end and start<s['end'] for start,end in spans)
        if intersects(timing_spans) or intersects(freezes):
            changes[s['id']]=(intersects(timing_spans),intersects(freezes))
    if not changes:
        return result,cues,{'status':'no_supported_local_repair','before':result}
    check=director.preflight(plan,state,previous_id=prior['report_sha256'],failures={s:'quality_failed' for s in changes})
    clips=[]
    for s in props['shots']:
        if s['id'] not in check['evaluated_scene_ids']:
            continue
        start,end=s['start'],s['end']
        redraw,move=changes[s['id']]
        clip=work/f'repair-{start}.mp4'
        rendered=work/f'caption-{start}.mp4' if move else clip
        if redraw:
            render({**props,'captions':new_cues},assets,browser,rendered,log,(start,end))
        if move:
            animate(rendered if redraw else video,clip,0 if redraw else start,end-start if redraw else end)
        clips.append((start,end,clip))
    trial=work/'candidate.mp4'
    repair.compose(video,clips,(0,1920),trial)
    old,new=repair.frame_hashes(video),repair.frame_hashes(trial)
    preserved=[i for i in range(len(old)) if not any(a<=i<b for a,b,_ in clips)]
    if len(old)!=len(new) or any(old[i]!=new[i] for i in preserved) or repair.audio_hash(video)!=repair.audio_hash(trial):
        raise ValueError('Repair changed audio or frames outside the defect scope')
    after,_=evidence(trial,plan,new_cues,voice,state,model,speech)
    accepted=passes(after)
    if accepted:
        trial.replace(video)
    return after if accepted else result,new_cues if accepted else cues,{
        'status':'accepted' if accepted else 'original_retained','touched':list(changes),'identical_frames':len(preserved),
        'aac_identical':True,'rechecked_transitions':check['evaluated_transition_ids'],'before':result,'after':after}


def run(opts):
    from faster_whisper import WhisperModel

    out=opts.out.resolve()
    out.mkdir(parents=True,exist_ok=True)
    assets=opts.assets.resolve()
    key=opts.topic
    catalog=batch.load()
    topic=next(row for row in catalog['reels'] if row['id']==key)
    lines=[beat['text'] for beat in topic['beats']]
    receipt=director._read(opts.voices/'TTS_REPORT.json')
    if receipt['free_project_confirmation']!='owner_verified_and_runner_matched':
        raise ValueError('Free project receipt is missing')
    take=next(r for r in receipt['takes'] if r['id']==key and r['status']=='recorded')
    voice=(opts.voices/f'{key}.wav').resolve()
    if (take['voice']!=director.VOICES[topic['brand']] or take['model']!=gemini_tts.MODEL or
        sha256('\n'.join(lines).encode()).hexdigest()!=take['script_sha256'] or batch.digest(voice)!=take['audio_sha256']):
        raise ValueError('Source, script, narrator or WAV fingerprint changed')
    with wave.open(str(voice),'rb') as stream:
        duration=stream.getnframes()/stream.getframerate()
    if not 60<=duration<=75:
        raise ValueError('The exact recorded WAV is outside the accepted duration')
    meter=Measurements(out/'PERFORMANCE.json')
    model=WhisperModel(str(opts.model.resolve()),device='cpu',compute_type='int8',cpu_threads=3,local_files_only=True)
    cues,cuts=meter.measure('align_from_recording',lambda:align(lines,transcribe(voice,model,key),duration))
    plan=adopted_plan(key,lines,cuts)
    verdict=review({**topic,'sources':plan['sources'],'evidence_boundary':topic['boundary']},topic['brand'],lines,fixed_recording=True)
    if verdict['status']!='passes_edit_index' or verdict['best']['total']<85:
        raise ValueError('The editorial score gate failed')
    licenses=director._read(assets/'ATTRIBUTION.json')
    shots=[]
    for i,(scene,beat,proof) in enumerate(zip(plan['scenes'],topic['beats'],PROOF[key])):
        name=VISUALS[key].get(i)
        item=licenses.get(name)
        if name and (not item or batch.digest(assets/name)!=item['delivered_sha256']):
            raise ValueError('Local media has diverged from its reviewed receipt')
        duration_frames=scene['end_frame']-scene['start_frame']
        video=bool(item and name.endswith('.mp4'))
        rate=min(1,max(.05,(float(item['probe']['format']['duration'])-.16)*FPS/duration_frames)) if video else 1
        shots.append({'id':scene['id'],'start':scene['start_frame'],'end':scene['end_frame'],'title':beat['heading'],
            'proof':proof.split('|'),'image':name if not video else None,'footage':name if video else None,'layout':i,'rate':rate,
            'label':'STOK · TEMSİLÎ UYGULAMA' if video else 'ARŞİV GÖRÜNTÜSÜ' if item else 'TEMSİLÎ ŞEMA',
            'credit':item['attribution'] if item else 'Özgün çizim · Kaynaklar ekte'})
    props={'brand':topic['brand'],'frames':cuts[-1],'shots':shots,'captions':cues}
    state=EditorialState(out/'.state.sqlite3')
    prior=director.preflight(plan,state)
    for name,value in [('SCENE_PLAN',plan),('SCENE_PREFLIGHT',prior),('EDITORIAL_REVIEW',verdict),('ATTRIBUTION',licenses),
                       ('SOURCE_RECEIPTS',{'boundary':topic['boundary'],'sources':plan['sources'],'beats':topic['beats']}),('TTS_TAKE',take)]:
        batch.write(out/(name+'.json'),value)
    _timeline(plan,out)
    final=out/'INSPECTION_REQUIRED.mp4'
    log=out/'REMOTION.log'
    with TemporaryDirectory(dir=out) as temporary:
        work=Path(temporary)
        visual=work/'visual.mp4'
        meter.measure('remotion',render,props,assets,opts.browser.resolve(),visual,log)
        dry=work/'normalized.wav'
        bed=work/'bed.wav'

        def mix():
            audio_bed.create(duration,bed)
            subprocess.run(['ffmpeg','-nostdin','-v','error','-i',str(voice),'-af','loudnorm=I=-16:TP=-2:LRA=7',
                            '-ar','48000','-c:a','pcm_s16le',str(dry)],check=True,timeout=90)
            subprocess.run(audio_mix_command(visual,dry,bed,final),check=True,timeout=120)

        meter.measure('ffmpeg_mix',mix)
        qa,speech=meter.measure('actual_video_qa',evidence,final,plan,cues,dry,state,model)
        repair_report={'status':'unnecessary'}
        if not passes(qa):
            try:
                qa,cues,repair_report=meter.measure('bounded_scene_repair',recover,final,plan,props,prior,qa,speech,state,dry,
                                                   model,assets,opts.browser.resolve(),work,log)
            except (ValueError,RuntimeError,subprocess.SubprocessError) as error:
                repair_report={'status':'original_retained','reason':str(error)}
    create_timed(cues,out/'TR.srt')
    batch.write(out/'CAPTION_ALIGNMENT.json',cues)
    batch.write(out/'VIDEO_QUALITY_LAB.json',qa)
    batch.write(out/'SCENE_REPAIR.json',repair_report)
    media=checked_frame_video(final,length=duration)
    checked=passes(qa) and media['audio_codec']=='aac' and media['video_frames']==cuts[-1]
    if checked:
        final.rename(out/'REVIEW_REQUIRED_REEL.mp4')
    outcome={'topic':key,'voice':take['voice'],'seconds':media['seconds'],'video_sha256':media['sha256'],'passed':checked,
             'editorial_score':verdict['best']['total'],'renderers_executed':['Remotion','FFmpeg'],'api_calls_in_render':0,
             'instagram_published':False,'human_approval_required':True,'repair_status':repair_report['status']}
    batch.write(out/'STATUS.json',outcome)
    print(json.dumps(outcome,ensure_ascii=False))
    return checked


def main():
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--topic',choices=VISUALS,required=True)
    cli.add_argument('--assets',type=Path,required=True)
    cli.add_argument('--fetch-assets',action='store_true')
    for arg in ('model','voices','browser','out'):
        cli.add_argument('--'+arg,type=Path)
    opt=cli.parse_args()
    if opt.fetch_assets:
        load_assets(opt.topic,opt.assets)
    else:
        if not all((opt.model,opt.voices,opt.browser,opt.out)):
            cli.error('offline production requires --model, --voices, --browser and --out')
        if not run(opt):
            raise SystemExit(1)


if __name__=='__main__':
    main()
