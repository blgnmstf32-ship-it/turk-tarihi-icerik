"""Optional 20 real LLM role executions, using the *free* OpenRouter router only.

Disabled unless OPENROUTER_API_KEY and ENABLE_20_LLM_AGENTS=1 are both present.
Crucially these outputs NEVER replace curated historical facts without review.
"""
from __future__ import annotations
import json,os,time
from pathlib import Path
import requests

FREE_MODEL='openrouter/free'

def run_agents(topic,agents,output,requester=None):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    key=os.getenv('OPENROUTER_API_KEY')
    if not key or os.getenv('ENABLE_20_LLM_AGENTS')!='1':
        result={'enabled':False,'reason':'missing key or explicit opt-in','calls':0,'separate_llm_roles_completed':0}
        (output/'AI_AGENTS_STATUS.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        return result
    request=requester or requests.post
    facts=json.dumps({'title':topic['title'],'date':topic['date'],'facts':topic['facts'],'context':topic['context'],'sources':topic['sources']},ensure_ascii=False)
    summaries=[];success=0
    for role in agents:
        prompt=(f'Role: {role["name"]}. Task: {role["job"]}. '+
                'Produce only a brief DRAFT suggestion, no invented history, no new dates, quotes or counts. '
                'Never state a source has been examined. No publishing. Data: '+facts)
        try:
            res=request('https://openrouter.ai/api/v1/chat/completions',timeout=35,
                        headers={'Authorization':f'Bearer {key}','X-Title':'Turk Tarihi 20 AI Roles'},
                        json={'model':FREE_MODEL,'messages':[{'role':'user','content':prompt}],
                              'max_tokens':180,'temperature':0.3})
            res.raise_for_status()
            suggestion=str(res.json()['choices'][0]['message']['content'])[:2500]
            summaries.append({'role_id':role['id'],'role':role['name'],'status':'suggestion_review_required','text':suggestion})
            success+=1
        except Exception as ex:
            summaries.append({'role_id':role['id'],'role':role['name'],'status':'error','error':str(ex)[:150]})
        # Cost controlled and no retry or paid fallback. Don't hammer free providers.
        if role['id']!=20:time.sleep(0.4)
    result={'enabled':True,'requested_model':FREE_MODEL,'calls':len(agents),'separate_llm_roles_completed':success,
            'verified_historical_sources':False,'human_review_required':True,
            'paid_fallback_allowed':False,'roles':summaries}
    (output/'AI_AGENTS_STATUS.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result
