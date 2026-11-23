"""Optional local faster-whisper subtitle/audio review; no network transcription."""
from pathlib import Path
import re

def transcribe_local(audio, model_size='tiny'):
    try: from faster_whisper import WhisperModel
    except ImportError as exc: raise RuntimeError('İsteğe bağlı faster-whisper kurulmalı: pip install -r requirements-audio-audit.txt') from exc
    model=WhisperModel(model_size,device='cpu',compute_type='int8',local_files_only=True)
    segments,info=model.transcribe(str(audio),language='tr',vad_filter=True,word_timestamps=True)
    return {'language':info.language,'segments':[{'start':s.start,'end':s.end,'text':s.text.strip()} for s in segments]}

def compare_subtitles(audio, srt, model_size='tiny'):
    from scripts.create_reel import subtitle_cues
    heard=transcribe_local(audio,model_size); expected=subtitle_cues(srt)
    transcript=' '.join(x['text'] for x in heard['segments'])
    expected_text=' '.join(x['text'] for x in expected)
    words=lambda text:re.findall(r"[\wçğıöşüÇĞİÖŞÜ]+",text.lower())
    ref,hyp=words(expected_text),words(transcript)
    row=[0]*(len(hyp)+1)
    for i,word in enumerate(ref,1):
        col=[i]+[0]*len(hyp)
        for j,heard_word in enumerate(hyp,1):col[j]=min(row[j]+1,col[j-1]+1,row[j-1]+(word!=heard_word))
        row=col
    wer=row[-1]/max(1,len(ref))
    return {'status':'passed' if wer<=0.25 else 'review_required','recognized_segments':len(heard['segments']),'subtitle_cues':len(expected),
            'word_error_rate':round(wer,4),'transcript':transcript,'expected':expected_text}
