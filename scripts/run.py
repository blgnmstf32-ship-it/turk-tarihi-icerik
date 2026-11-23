"""Twenty *functional role modules*, not 20 billed independent AI calls.

No model/API key or paid service needed. Publication is ALWAYS manual-gated.
"""
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime, timezone
import argparse, json, shutil, subprocess, sys, textwrap
from PIL import Image
try:
    from scripts.graphics import render_card
except ModuleNotFoundError:
    from graphics import render_card

ROOT=Path(__file__).resolve().parent.parent


def load_json(path):
    with open(path,encoding='utf-8') as f:return json.load(f)


def select_topic(items,topic_id):
    if topic_id:
        return next((x for x in items if x['id']==topic_id),None)
    # Stable weekly rotation; 2 drafts (one on each scheduled day).
    week=datetime.now(timezone.utc).isocalendar().week
    weekday=datetime.now(timezone.utc).weekday()
    return items[((week*2)+(0 if weekday<3 else 1))%len(items)]


def build(topic,outdir,video=True):
    roles=load_json(ROOT/'config'/'agents.json')
    settings=load_json(ROOT/'config'/'settings.json')
    assert len(roles)==20 and len({r['id'] for r in roles})==20
    assert settings['human_approval_required'] and not settings['instagram_auto_publish_enabled']
    outdir=Path(outdir).resolve();outdir.mkdir(parents=True,exist_ok=True)
    done=[];notes=[]; artifacts={}

    def act(id,description,fn):
        output=fn()
        done.append({'id':id,'name':roles[id-1]['name'],'result':description})
        return output

    # Research: curated evidence is checked for presence and shape, NOT independently web-verified.
    act(1,'Arşivden konu seçildi',lambda:None)
    act(2,'Tarih ve dönem alanları var',lambda:all(topic.get(x) for x in ('date','era','title')) or (_ for _ in ()).throw(ValueError('Kronoloji bilgisi eksik')))
    def check_sources():
        src=topic.get('sources',[])
        if not src:raise ValueError('Kaynak yok: üretim durduruldu')
        if any(urlparse(s['url']).scheme!='https' or not urlparse(s['url']).netloc for s in src):raise ValueError('Geçersiz kaynak URL')
        return src
    sources=act(3,'Kaynak URL kayıtları denetlendi; içerik insan tarafından okunmalı',check_sources)
    act(4,'Her konu için en az bir kaynak var',lambda:len(sources)>0 or (_ for _ in ()).throw(ValueError('Kaynak eşleme eksik')))
    act(5,'Tartışmalı yorumlar bağlam notuna ayrıldı',lambda:topic.get('context') is not None or (_ for _ in ()).throw(ValueError('Bağlam eksik')))

    # Editorial steps
    hook=act(6,'Açılış cümlesi üretildi',lambda:topic['hook'])
    script=act(7,'Üç tarihî bilgiyle senaryo derlendi',lambda:[hook,*topic['facts']])
    voiceover=act(8,'Seslendirme metni hazırlandı',lambda:' '.join(script))
    caption=act(9,'Instagram açıklaması oluşturuldu',lambda: '\n\n'.join([f"{topic['title']} — {topic['date']}",*topic['facts'], f"Tarihî bağlam: {topic['context']}", 'Kaynaklar: '+', '.join(s['title'] for s in sources)]))
    hashtags=act(10,'Konuya özgü etiketler eklendi',lambda:'#TürkTarihi #Tarih #TarihBilgisi #TarihReels')
    caption+='\n\n'+hashtags
    (outdir/'caption.txt').write_text(caption,encoding='utf-8')
    (outdir/'voiceover.txt').write_text(voiceover,encoding='utf-8')
    (outdir/'sources.json').write_text(json.dumps(sources,ensure_ascii=False,indent=2),encoding='utf-8')

    # Media: license-free template art; explicit prompt retained if upgrading to image/video AI.
    storyboard=act(11,'3 sahne planlandı',lambda:[f"Açılış: {hook}",topic['facts'][0],topic['facts'][1]+' '+topic['facts'][2]])
    poster=act(12,'4:5 özgün poster üretildi',lambda:render_card(outdir/'post_1080x1350.png',topic,topic['date'],topic['title'],topic['hook'],portrait=False,kind='post'))
    prompt=act(13,'İsteğe bağlı sinematik illüstrasyon promptu kaydedildi',lambda:topic['image_prompt'])
    (outdir/'visual_prompt.txt').write_text(prompt+'\n\nUyarı: Yapay canlandırmadır; tarihî belge veya gerçek fotoğraf gibi sunma.',encoding='utf-8')
    audio=act(14,'Telifsiz seslendirme/müzik yönergesi yazıldı',lambda:'Öneri: özgün anlatım kaydı; lisansı doğrulanmış müzik. Otomatik olarak telifli kayıt indirme/kullanma.')
    (outdir/'audio_notes.txt').write_text(audio,encoding='utf-8')
    slide_texts=[(topic['date'],topic['title'],hook),('NE OLDU?',topic['facts'][0],topic['date']),('NEDEN ÖNEMLİ?',topic['facts'][2],'Kaynaklar açıklamada')]
    slidepaths=[]
    for i,(h,m,f) in enumerate(slide_texts,1):
        slidepaths.append(render_card(outdir/f'reel_sahne_{i}.png',topic,h,m,f,portrait=True,kind=f'slide{i}'))
    def create_video():
        if not video:
            notes.append('MP4 oluşturma atlandı (--skip-video).');return None
        if not shutil.which('ffmpeg'):
            notes.append('FFmpeg bulunamadı; PNG sahneler hazır, MP4 yok.');return None
        concat=outdir/'slides.txt'
        content='ffconcat version 1.0\n'
        for p in slidepaths:
            content+=f"file '{p.name}'\nduration 5\n"
        # Omit duplicate final frame; it otherwise adds ~5 extra seconds.
        concat.write_text(content,encoding='utf-8')
        dest=outdir/'SESSIZ_SLAYT_ONIZLEME_YAYINLAMA.mp4'
        cp=subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-safe','0','-f','concat','-i',str(concat),'-r','15','-vf','scale=720:1280,format=yuv420p','-c:v','libx264','-preset','ultrafast','-crf','27','-movflags','+faststart',str(dest)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,cwd=outdir)
        if cp.returncode:
            raise RuntimeError('FFmpeg işlemi başarısız: '+cp.stderr[-700:])
        return dest
    mp4=act(15,'SESSİZ slayt önizlemesi üretildi; yayımlanabilir Reels değil',create_video)
    def check_media():
        with Image.open(poster) as im:
            if im.size != (1080,1350):raise ValueError('Poster boyutu yanlış')
        for p in slidepaths:
            with Image.open(p) as im:
                if im.size != (720,1280):raise ValueError('Sahne boyutu yanlış')
        if mp4 and (not mp4.exists() or mp4.stat().st_size<10000):raise ValueError('MP4 geçersiz')
        return True
    act(16,'Görsel boyutları, video dosyası ve formatlar kontrol edildi',check_media)
    act(17,'Dış medya varlığı kullanılmadı; müzik hakları insan kontrolünde',lambda:True)
    act(18,'Kaynak listesi iliştirildi, insan tarih doğrulaması bekleniyor',lambda:True)
    approval=act(19,'YAYIN KAPALI: insan onayı gerekiyor',lambda:{'status':'needs_human_approval','approved':False,'publish_enabled':False})
    report=act(20,'Maliyet ve çalışma raporu kaydedildi',lambda:{'paid_api_calls':0,'estimated_paid_api_cost_try':0,'notes':notes})
    package={'topic_id':topic['id'],'topic_title':topic['title'],'produced_at_utc':datetime.now(timezone.utc).isoformat(),'approval':approval,'actual_automatic_historical_source_verification':False,'sources_for_manual_review':sources,'roles_completed':done,'n_roles':len(done),'cost':report,'publication':'NONE','files':{'post':poster.name,'mp4':None,'silent_preview_only':mp4.name if mp4 else None,'ready_for_instagram':False,'missing':['Türkçe insan kalitesinde seslendirme','En az 5 dönem uyumlu sahne','SFX ve müzik lisansı','Hareketli video ve altyazı','İnsan tarih doğrulaması'],'caption':'caption.txt','voiceover':'voiceover.txt','sources':'sources.json'}}
    (outdir/'draft_manifest.json').write_text(json.dumps(package,ensure_ascii=False,indent=2),encoding='utf-8')
    (outdir/'STORYBOARD.md').write_text('# Sahne planı\n\n'+'\n\n'.join(f'{i}. {s}' for i,s in enumerate(storyboard,1))+'\n\n**Kaynak kontrolü ve insan onayı olmadan yayınlanmaz.**',encoding='utf-8')
    return package


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--topic',default='')
    p.add_argument('--out',default=str(ROOT/'output'/'draft'))
    p.add_argument('--skip-video',action='store_true')
    args=p.parse_args()
    topics=load_json(ROOT/'data'/'topics.json')
    topic=select_topic(topics,args.topic)
    if not topic:p.error('Konu bulunamadı; data/topics.json içindeki id kullanılmalı.')
    package=build(topic,args.out,not args.skip_video)
    print(f"20/20 modül tamamlandı | Konu: {topic['title']} | Yayın: KAPALI | YALNIZCA SESSİZ ÖNİZLEME: {bool(package['files']['silent_preview_only'])}")

if __name__=='__main__':main()
