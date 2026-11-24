"""Optional local faster-whisper subtitle/audio review; no network transcription."""
from pathlib import Path
import re

def load_local_model(model_size):
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError('Yerel konuşma kontrolü için faster-whisper kurulmalı: pip install -r requirements-audio-audit.txt') from exc
    return WhisperModel(model_size, device='cpu', compute_type='int8', local_files_only=True)


def transcribe_local(audio, model_size='tiny', *, model=None):
    model = model if model is not None else load_local_model(model_size)
    segments, info = model.transcribe(str(audio), language='tr', vad_filter=True, word_timestamps=True)
    segments = list(segments)
    return {
        'language': info.language,
        'segments': [{'start': s.start, 'end': s.end, 'text': s.text.strip()} for s in segments],
        'words': [{'start': w.start, 'end': w.end, 'text': w.word}
                  for s in segments for w in (s.words or [])],
    }


def compare_reference(audio, reference, model_size='tiny', max_word_error_rate=0.25):
    heard = transcribe_local(audio, model_size)
    transcript = ' '.join(segment['text'] for segment in heard['segments'])
    words = lambda text: re.findall(r"[^\W_]+", text.translate(str.maketrans("Iİ", "ıi")).lower())
    ref, hyp = words(reference), words(transcript)
    row = list(range(len(hyp)+1))
    for i, word in enumerate(ref, 1):
        col = [i] + [0]*len(hyp)
        for j, heard_word in enumerate(hyp, 1):
            col[j] = min(row[j]+1, col[j-1]+1, row[j-1]+(word!=heard_word))
        row = col
    wer = row[-1]/max(1,len(ref))
    passed = bool(ref and hyp and heard['language'] == 'tr' and wer <= max_word_error_rate)
    return {'status':'passed' if passed else 'review_required', 'detected_language':heard['language'],
            'recognized_segments':len(heard['segments']), 'word_error_rate':round(wer,4),
            'transcript':transcript, 'expected':reference}


def compare_subtitles(audio, srt, model_size='tiny'):
    from scripts.create_reel import subtitle_cues
    cues = subtitle_cues(srt)
    reference = ' '.join(cue['text'] for cue in cues)
    return {**compare_reference(audio, reference, model_size), 'subtitle_cues':len(cues)}
