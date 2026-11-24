import json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from scripts.editorial_research import collect_public_research
from scripts.content_strategy import score_ideas, build_debate, load_learning
from scripts.performance_learning import record_outcome
from scripts.editorial_board import run_board, _llm_review
from scripts.instagram_insights import fetch_read_only_insights

class Response:
    def __init__(self,content=None,data=None): self.content=content;self.data=data
    def raise_for_status(self): pass
    def json(self): return self.data

class EditorialIntelligenceTests(unittest.TestCase):
    def test_public_trends_and_competitor_feeds_are_parsed_with_provenance(self):
        trend='<rss><channel><item><title>Türk tarihi harita</title><link>https://trends.example/item</link></item></channel></rss>'.encode()
        atom='''<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Harita ve tarih</title>
            <link href="https://youtube.example/video"/><published>2026-11-20T12:00:00Z</published></entry></feed>'''.encode()
        def get(url,**kwargs): return Response(content=trend if 'trends.google.com' in url else atom)
        config={'google_trends_rss':'https://trends.google.com/trending/rss?geo=TR',
            'competitor_youtube_channels':[{'name':'Rakip','channel_id':'UCtest'}],'research_timeout_seconds':2}
        result=collect_public_research(config,get)
        self.assertEqual(result['evidence_counts'],{'trend_items':1,'competitor_channels':1,'competitor_videos':1})
        self.assertEqual(result['competitors'][0]['videos'][0]['title'],'Harita ve tarih')
        self.assertIn('public RSS',result['method'])

    def test_relative_scores_use_trends_competitor_coverage_and_past_metrics(self):
        research={'trends':[{'title':'Türk tarihi harita'}],
            'competitors':[{'videos':[{'title':'Osmanlı tarihi'}]}],
            'evidence_counts':{'trend_items':1,'competitor_videos':1}}
        outcomes=[{'category':'kesif','views':500,'reach':400,'shares':40,'avg_watch_seconds':45} for _ in range(4)]
        ranked=score_ideas(research,outcomes)
        by_id={item['id']:item for item in ranked}
        self.assertTrue(by_id['haritanin-yolculugu']['potential_index']>by_id['tarihin-kilidi']['potential_index'])
        self.assertEqual(by_id['haritanin-yolculugu']['estimated_cost_try'],0)
        self.assertIn('değildir',by_id['haritanin-yolculugu']['potential_label'])
        debate=build_debate(ranked,research,outcomes)
        self.assertEqual(len(debate['rounds'][0]['positions']),3)
        self.assertIn('Konu Avcısı',[x['role'] for x in debate['rounds'][0]['positions']])

    def test_coordinator_writes_weekly_reviewable_decision_report(self):
        research={'collected_at_utc':'2026-11-24T00:00:00Z','method':'fixture','trends':[],
            'competitors':[],'errors':[],'evidence_counts':{'trend_items':0,'competitor_channels':0,'competitor_videos':0}}
        with tempfile.TemporaryDirectory() as d:
            report=run_board(d,{'research_timeout_seconds':1,'historical_data_file':'unused'},Path(d)/'none.jsonl',
                research_fn=lambda _:research,llm_fn=lambda *_:{'status':'disabled','calls':0,'actual_llm_used':False},
                insights_fn=lambda:{'status':'disabled','read_only':True,'published':False,'records':[]})
            self.assertEqual(len(report['recommendations']),6)
            self.assertEqual(len(report['strategy']['categories_compared']),4)
            self.assertTrue((Path(d)/'EDITORIAL_DECISION_REPORT.md').exists())
            self.assertFalse(report['coordinator_llm']['actual_llm_used'])
            self.assertFalse(report['instagram_publish_enabled'])

    def test_ai_general_editor_free_route_requires_setting_and_explicit_opt_in(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'config').mkdir()
            (root/'config/settings.json').write_text(json.dumps({'editorial_intelligence':{'free_llm_enabled':True}}))
            from scripts import editorial_board
            with patch.object(editorial_board,'ROOT',root), patch.dict('os.environ',{'ENABLE_FREE_LLM':'1','OPENROUTER_API_KEY':'mock'},clear=False), \
                 patch('scripts.editorial_board.requests.post',return_value=Response(data={'choices':[{'message':{'content':'{"selected_idea_id":"harita"}'}}]})) as post:
                result=_llm_review([{'id':'harita'}],{'rounds':[]})
            self.assertTrue(result['actual_llm_used']);self.assertEqual(result['calls'],1)
            self.assertEqual(result['model'],'openrouter/free');self.assertFalse(result['paid_fallback'])
            self.assertIn('openrouter.ai/api/v1/chat/completions',post.call_args.args[0])
        with patch.dict('os.environ',{'ENABLE_FREE_LLM':'0','OPENROUTER_API_KEY':'mock'},clear=False):
            self.assertFalse(_llm_review([],{}).get('actual_llm_used'))

    def test_outcomes_learn_above_or_below_category_median(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'metrics.jsonl'
            for i,views in enumerate([100,200,300]):record_outcome({'content_id':str(i),'category':'tarih','views':views},path)
            added=record_outcome({'content_id':'next','category':'tarih','views':400,'shares':20,'reach':200},path)
            self.assertEqual(added['learning_outcome'],'above_category_median')
            self.assertEqual(len(load_learning(path)),4)

    def test_read_only_insights_fetches_reel_metrics_without_exposing_token(self):
        settings={'instagram_insights_enabled':True}
        calls=[]
        def get(url,**kwargs):
            calls.append((url,kwargs))
            return Response(data={'data':[{'name':'views','values':[{'value':220}]},{'name':'reach','values':[{'value':180}]},
                {'name':'shares','values':[{'value':12}]},{'name':'ig_reels_avg_watch_time','values':[{'value':31.5}]}]})
        env={'INSTAGRAM_INSIGHTS_ENABLED':'1','IG_INSIGHTS_ACCESS_TOKEN':'secret','INSTAGRAM_MEDIA_MAP':json.dumps([
            {'media_id':'m1','topic_id':'test','category':'kesif'}])}
        with patch.dict('os.environ',env,clear=False): result=fetch_read_only_insights(get,settings)
        self.assertEqual(result['status'],'ok');self.assertEqual(result['records'][0]['views'],220)
        self.assertEqual(result['records'][0]['avg_watch_seconds'],31.5)
        self.assertEqual(result['records'][0]['shares'],12)
        self.assertNotIn('secret',json.dumps(result))
        self.assertEqual(len(calls),1)
        self.assertIn('/m1/insights',calls[0][0])

    def test_workflow_runs_editorial_and_video_pipeline_and_saves_artifacts(self):
        workflow=Path('.github/workflows/produce.yml').read_text(encoding='utf-8')
        self.assertIn('python -m scripts.auto_produce',workflow)
        self.assertIn('python -m unittest discover -s tests -v',workflow)
        self.assertIn('actions/upload-artifact@v4',workflow)
        self.assertIn('TURKCE_SES_KONTROLU.json',workflow)
        self.assertNotIn('instagram_publish.py',workflow)
        self.assertIn("ENABLE_20_LLM_AGENTS: '0'",workflow)

if __name__=='__main__': unittest.main()
