"""Transparent content portfolio scoring, idea debate, and learning from outcomes."""
from __future__ import annotations
from collections import defaultdict
import json, re
from pathlib import Path

CATEGORIES={
 "tarih": {"terms":["tarih","savaş","fetih","osmanlı","selçuklu","cumhuriyet"],"promise":"tarihi dönüm noktasını kaynaklarla anlat"},
 "tarihi_gizem": {"terms":["gizem","kayıp","sır","nerede","neden"],"promise":"kanıt ve belirsizliği ayırarak bir tarih sorusunu çözümle"},
 "az_bilinen_olay": {"terms":["az bilinen","unutulan","bilinmeyen"],"promise":"daha az işlenen bir olayı güçlü birincil/akademik kaynakla görünür kıl"},
 "kesif": {"terms":["keşif","eser","harita","kitabe","arkeoloji"],"promise":"bir eser, kitabe veya haritanın anlattıklarını incele"},
}
CATEGORY_HYPOTHESES={
 "tarih":{"points":12,"reason":"geniş konu tanınırlığı varsayımı; yoğun rekabet riski"},
 "tarihi_gizem":{"points":19,"reason":"soru/merak çerçevesi izlemeyi destekleyebilir; kaynak belirsizliği riski"},
 "az_bilinen_olay":{"points":18,"reason":"özgünlük varsayımı güçlü; izleyici talebi henüz kanıtlanmış değil"},
 "kesif":{"points":16,"reason":"eser/harita görseli anlaşılır bir kanca sağlayabilir; lisanslı varlık bulunması gerekir"},
}
IDEA_SEEDS=[
 {"id":"savas-haritasi","category":"tarih","title":"Bir savaş haritası neyi gösterir, neyi göstermez?","hook":"Haritadaki oklar, kaynaklardaki gerçeklerle ne kadar örtüşüyor?","visual":"lisanslı harita + kısa 3D hareket canlandırması","focus_terms":["savaş haritası","ordu hareketi","taktik harita"],"visual_strength":9,"effort_minutes":150},
 {"id":"kaynak-celiski","category":"tarihi_gizem","title":"Tarihî kaynaklar aynı olay için neden farklı anlatır?","hook":"İki kaynak, tek olay ve farklı ayrıntılar: hangisine güvenebiliriz?","visual":"kaynak sayfaları + karşılaştırmalı 2D grafik","focus_terms":["kaynak çelişkisi","iki kaynak","tarihî belge"],"visual_strength":6,"effort_minutes":120},
 {"id":"unutulan-olay","category":"az_bilinen_olay","title":"Büyük dönüşümün arka planındaki az bilinen olay","hook":"Dönüm noktası manşet olur; peki onu hazırlayan küçük olay neydi?","visual":"açık lisanslı arşiv/yer görselleri + harita","focus_terms":["az bilinen olay","unutulan tarih","tarihî arka plan"],"visual_strength":7,"effort_minutes":135},
 {"id":"haritanin-yolculugu","category":"kesif","title":"Eski bir harita Türk tarihinin hangi izlerini saklıyor?","hook":"Bu haritadaki bir çizgi, dönemin dünyasını nasıl değiştiriyor?","visual":"yüksek çözünürlüklü açık lisanslı harita + kamera yakınlaşması","focus_terms":["harita","eski harita","harita keşfi"],"visual_strength":9,"effort_minutes":130},
 {"id":"sehir-katmanlari","category":"kesif","title":"Bir tarihî şehrin üç farklı dönemini aynı kadrajda keşfet","hook":"Bugün gördüğümüz sokakların altında kaç tarihî katman var?","visual":"Wikimedia şehir fotoğrafları + isteğe bağlı 3D kamera uçuşu","focus_terms":["tarihî şehir","şehir katmanları","şehir uçuşu"],"visual_strength":10,"effort_minutes":180},
 {"id":"tarihin-kilidi","category":"tarihi_gizem","title":"Bir kitabe, sikke veya belge bir tarih tartışmasını çözebilir mi?","hook":"Küçük bir yazıt, büyük bir iddiayı doğrulamaya yeter mi?","visual":"müze/eser fotoğrafı + açıklamalı makro plan","focus_terms":["kitabe","sikke","yazıt"],"visual_strength":8,"effort_minutes":120},
]

def _norm(s): return re.sub(r"[^a-z0-9çğıöşü]+"," ",str(s).lower()).strip()

def load_learning(path):
    p=Path(path)
    if not p.exists(): return []
    if p.suffix.lower()==".json":
        data=json.loads(p.read_text(encoding="utf-8")); return data if isinstance(data,list) else data.get("records",[])
    rows=[]
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try: rows.append(json.loads(line))
            except json.JSONDecodeError: continue
    return rows

def score_ideas(research, outcomes):
    category_perf=defaultdict(list)
    for row in outcomes:
        category=row.get("category"); reach=row.get("views",row.get("reach")); shares=row.get("shares")
        watch=row.get("avg_watch_seconds",row.get("watch_time_seconds")); followers=row.get("follows",row.get("follower_gain"))
        if not category: continue
        # Normalize per-view, when denominators exist. Missing measurements remain missing.
        rates=[]
        if reach and shares is not None: rates.append(float(shares)/max(1,float(reach)))
        if reach and followers is not None: rates.append(float(followers)/max(1,float(reach)))
        if watch is not None: rates.append(min(1,float(watch)/75))
        if rates: category_perf[category].append(sum(rates)/len(rates))
    candidates=[]
    titles=[_norm(v.get("title","")) for c in research.get("competitors",[]) for v in c.get("videos",[])]
    for seed in IDEA_SEEDS:
        terms=[_norm(term) for term in seed.get("focus_terms",[])]
        competitor_overlap=sum(any(term in title for term in terms) for title in titles)
        trends=[t for t in research.get("trends",[]) if any(term in _norm(t.get("title","")) for term in terms)]
        history=category_perf.get(seed["category"],[])
        profile=CATEGORY_HYPOTHESES[seed["category"]]
        curiosity=8 if "?" in seed["hook"] else 4
        efficiency=max(0,8-round((seed["effort_minutes"]-120)/10))
        score=25+profile["points"]+seed["visual_strength"]*2+curiosity+efficiency+min(10,len(trends)*5)
        if titles: score+=8 if competitor_overlap==0 else -min(12,competitor_overlap*2)
        if history: score+=min(10,round(sum(history)/len(history)*100))
        evidence=[]
        if trends: evidence.append({"kind":"trend_match","items":trends[:3]})
        if titles: evidence.append({"kind":"competitor_coverage","overlap_count":competitor_overlap,"sample_size":len(titles)})
        if history: evidence.append({"kind":"historical_performance","sample_size":len(history),"mean_normalized_signal":round(sum(history)/len(history),4)})
        if not evidence: evidence.append({"kind":"editorial_hypothesis","note":"No trend/competitor/performance observations available; score is an unvalidated baseline."})
        score=max(0,min(100,score))
        candidate={**seed,"potential_index":score,"potential_label":"göreli editoryal potansiyel; başarı olasılığı değildir",
            "evidence":evidence,"success_rationale":[],"risks":["Trend ilgisi tarihsel doğruluğun yerine geçmez","Konunun kitle performansı verisi yoksa sonuç tahmindir"],
            "estimated_cost_try":0,"estimated_cost_basis":"paid API/media spend only; labor and local compute excluded",
            "estimated_production_minutes":seed["effort_minutes"],"production_plan":{
                "visual":"Wikimedia Commons open-license search first; verify attribution and historic relevance",
                "3d":"battle map / army movement only when the researched topic is a battle; city flyover/siege only for a city capture; otherwise 2D",
                "voice":"human recording preferred; free local Piper fallback, clearly disclosed as synthetic",
                "edit":"Remotion timeline + FFmpeg finish; 2D fallback if 3D render fails"},"llm_used":False}
        candidate["success_rationale"].append(profile["reason"]+".")
        candidate["success_rationale"].append(f"Soru kancası ve görsel gücü için {curiosity+seed['visual_strength']*2} yapısal puan; tahmini üretim süresi {seed['effort_minutes']} dakika.")
        if trends: candidate["success_rationale"].append("Güncel trend RSS içinde bu fikrin odak terimleriyle eşleşme bulundu.")
        if titles and competitor_overlap==0: candidate["success_rationale"].append("İzlenen rakiplerin son RSS başlıklarında odak terimi görülmedi; örnek yalnız iki kanal ve RSS'teki son başlıklardır.")
        if titles and competitor_overlap: candidate["risks"].append(f"İzlenen rakip RSS başlıklarında {competitor_overlap} odak terimi eşleşmesi var.")
        if history: candidate["success_rationale"].append("Geçmiş içeriklerde bu kategorinin normalize etkileşim/izleme sinyali hesaba katıldı.")
        if not candidate["success_rationale"]: candidate["success_rationale"].append("Kaynakla doğrulanabilir soru ve güçlü görsel önerisi; performans kanıtı bekleniyor.")
        candidates.append(candidate)
    return sorted(candidates,key=lambda x:(x["potential_index"],x["id"]),reverse=True)

def build_debate(candidates,research,outcomes):
    """Three explicit perspectives debate evidence; no pretend autonomous chat."""
    top=candidates[:3]
    data_n=len(outcomes)
    competitor_n=research.get("evidence_counts",{}).get("competitor_videos",0)
    rounds=[]
    for c in top:
        trend_evidence=next((e for e in c.get("evidence",[]) if e.get("kind")=="trend_match"),None)
        competitor_evidence=next((e for e in c.get("evidence",[]) if e.get("kind")=="competitor_coverage"),None)
        coverage=competitor_evidence.get("overlap_count",0) if competitor_evidence else None
        rounds.append({"idea_id":c["id"],"idea":c["title"],"positions":[
          {"role":"Konu Avcısı","position":"Doğrudan trend eşleşmesi var" if trend_evidence else "Trend talebi doğrulanmadı",
           "reason":f"Bu fikir için {len(trend_evidence['items']) if trend_evidence else 0} doğrudan eşleşme; örnekte {competitor_n} rakip video başlığı. RSS başlıkları izlenme/izleyici niyetini kanıtlamaz."},
          {"role":"İçerik Stratejisti","position":"Performans verisiyle karşılaştır" if data_n else "Küçük pilot olarak test et",
           "reason":f"{data_n} performans kaydı var; doğrudan rakip konu eşleşmesi {coverage if coverage is not None else 'ölçülemedi'}. Başarı olasılığı hesaplanmıyor."},
          {"role":"Tarih Doğruluk Denetçisi","position":"Kaynak kapısı şartlı","reason":"Öneri konu açısıdır; senaryoda kullanılmadan önce her olgu birincil/akademik kaynakla eşlenmelidir."}
        ],"counterpoint":"Trend ve rakip başlıkları gerçek izlenme, izlenme süresi veya izleyici niyetini göstermez."})
    return {"method":"kanıtlı rol perspektifleri; bağımsız canlı LLM tartışması değildir","rounds":rounds}
