"""Sentence-level estimated subtitle timing; does not falsely claim forced alignment."""
from pathlib import Path
import re

def stamp(v):
    ms=max(0,round(v*1000));h,ms=divmod(ms,3600000);m,ms=divmod(ms,60000);s,ms=divmod(ms,1000)
    return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'

def create(text,duration,path):
    clauses=[x.strip() for x in re.split(r'(?<=[.!?])\s+',text) if x.strip()]
    if not clauses:raise ValueError('empty narration')
    weight=[max(1,len(re.findall(r'\w+',s))) for s in clauses];total=sum(weight);p=0
    out=[]
    for i,(s,n) in enumerate(zip(clauses,weight),1):
        end=duration if i==len(clauses) else duration*(sum(weight[:i]))/total
        out.append(f'{i}\n{stamp(p)} --> {stamp(end)}\n{s}\n')
        p=end
    path=Path(path);path.write_text('\n'.join(out)+'\n',encoding='utf-8');return path
