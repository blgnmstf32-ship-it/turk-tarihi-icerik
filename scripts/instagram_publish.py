"""Meta Reels publishing scaffold. NOT used in the automatic workflow.

Manual approval, explicit --execute, environment opt-in, and existing public HTTPS
media URL are all required. Never attempt to auto-publish inside production.
"""
from __future__ import annotations
import argparse, json, os, time
from pathlib import Path
from urllib.parse import urlparse
import requests


def safe_public_url(url):
    parsed=urlparse(url)
    return parsed.scheme=='https' and bool(parsed.hostname) and parsed.hostname not in ('localhost','127.0.0.1') and not parsed.hostname.endswith('.local')

def publish(video_url,caption,approval_file,execute=False,session=None,base=None):
    if not safe_public_url(video_url):raise ValueError('Public HTTPS media URL required')
    approval=json.loads(Path(approval_file).read_text(encoding='utf-8'))
    if approval.get('approved_by_owner') is not True or approval.get('content_reviewed') is not True:
        raise PermissionError('Explicit OWNER human content approval missing')
    if not execute:return {'would_publish':True,'published':False,'reason':'dry_run'}
    if os.getenv('IG_ALLOW_PUBLISH')!='I_APPROVE_THIS_POST':raise PermissionError('GitHub manual publish opt-in missing')
    token=os.getenv('IG_ACCESS_TOKEN');ig=os.getenv('IG_USER_ID')
    if not token or not ig:raise RuntimeError('IG_ACCESS_TOKEN and IG_USER_ID secrets required')
    api=base or 'https://graph.facebook.com/v25.0'
    client=session or requests.Session()
    create=client.post(f'{api}/{ig}/media',data={'media_type':'REELS','video_url':video_url,'caption':caption,'access_token':token},timeout=35)
    create.raise_for_status();container=create.json().get('id')
    if not container:raise RuntimeError('Missing upload container id')
    for _ in range(16):
        state=client.get(f'{api}/{container}',params={'fields':'status_code,status','access_token':token},timeout=20)
        state.raise_for_status();info=state.json()
        if info.get('status_code')=='FINISHED':break
        if info.get('status_code') in ('ERROR','EXPIRED'):raise RuntimeError('Meta container processing error')
        time.sleep(15)
    else:raise TimeoutError('Meta reel container not finished; check status before retrying; do NOT re-post blindly')
    pub=client.post(f'{api}/{ig}/media_publish',data={'creation_id':container,'access_token':token},timeout=35)
    pub.raise_for_status()
    return {'published':True,'instagram_media_id':pub.json().get('id'),'container_id':container}


def main():
    p=argparse.ArgumentParser();p.add_argument('--url',required=True);p.add_argument('--caption-file',required=True);p.add_argument('--approval-file',required=True);p.add_argument('--execute',action='store_true');a=p.parse_args()
    caption=Path(a.caption_file).read_text(encoding='utf-8')
    print(json.dumps(publish(a.url,caption,a.approval_file,a.execute),ensure_ascii=False))
if __name__=='__main__':main()
