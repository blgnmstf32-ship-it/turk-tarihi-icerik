"""Optional PySceneDetect shot-cut diversity check; never changes a render."""
from pathlib import Path

def audit(video, threshold=27.0):
    try:
        from scenedetect import open_video, SceneManager
        from scenedetect.detectors import ContentDetector
    except ImportError as exc: raise RuntimeError('İsteğe bağlı PySceneDetect kurulmalı: pip install -r requirements-video-audit.txt') from exc
    manager=SceneManager(); manager.add_detector(ContentDetector(threshold=threshold,min_scene_len=12))
    manager.detect_scenes(open_video(str(video)))
    scenes=manager.get_scene_list()
    return {'detected_shot_count':len(scenes),'diversity_gate':'review_required' if len(scenes)<10 else 'passed','minimum':10}
