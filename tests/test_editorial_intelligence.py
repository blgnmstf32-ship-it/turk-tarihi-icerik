import json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from scripts.editorial_research import collect_public_research
from scripts.content_strategy import score_ideas, build_debate, load_learning
from scripts.performance_learning import record_outcome
from scripts.editorial_board import run_board
from scripts.editorial_llm import _answer, review
from scripts.run import select_topic
from scripts.instagram_insights import fetch_read_only_insights

class Response:
    def __init__(self,content=None,data=None):
        self.content=content;self.data=data
        self.status_code=200
        self.headers={}
    def raise_for_status(self): pass
    def json(self): return self.data

class EditorialIntelligenceTests(unittest.TestCase):
    def test_portfolio_needs_a_source_from_the_same_candidate(self):
        ideas = score_ideas({}, [])
        sources = {idea["id"]: idea["sources"][0]["url"] for idea in ideas}
        rows = [{"idea_id": idea, "source_url": url, "rationale": "Özgün bir anlatım açısı.",
                 "open_question": "Hangi kanıtı incelemeli?"} for idea, url in sources.items()]
        mismatched = {**rows[0], "idea_id": rows[1]["idea_id"]}
        self.assertNotEqual(rows[0]["source_url"], rows[1]["source_url"])
        answer, error = _answer(json.dumps({"rationale": "Katalog", "idea_reviews": [mismatched, *rows]}),
                                set(sources), set(sources.values()), "test-key", ideas)
        self.assertIsNone(error)
        self.assertEqual(answer["idea_reviews"], rows)
        self.assertEqual(_answer(json.dumps({"rationale": "Katalog", "idea_reviews": rows[:-1]}),
                                 set(sources), set(sources.values()), "test-key", ideas)[1],
                         "incomplete_portfolio_review")

    def test_live_portfolio_requests_partition_ten_ideas_without_extra_calls(self):
        ideas = score_ideas({}, [])
        requested = []
        def post(url, **kwargs):
            payload = kwargs["json"]
            data = json.loads(payload["messages"][1]["content"])
            assigned = data.get("ranked_candidates", [])
            requested.append([candidate["id"] for candidate in assigned])
            answer = {"rationale": "Kaynakları incele"}
            message = {"content": json.dumps(answer)}
            if assigned:
                schema = payload["tools"][0]["function"]["parameters"]["properties"]["idea_reviews"]
                self.assertEqual(schema["required"], requested[-1])
                answer["idea_reviews"] = {idea_id: {"rationale": "Bir ayrıntıyı büyüt.",
                    "open_question": "Nasıl doğrulanır?"} for idea_id in requested[-1]}
                message = {"content": None, "tool_calls":[{"function":{
                    "name":"submit_idea_reviews", "arguments":json.dumps(answer)}}]}
            return Response(data={"model":"test/free","choices":[{"message":message}]})
        with tempfile.TemporaryDirectory() as tmp, patch.dict("os.environ", {
                "ENABLE_FREE_LLM":"1", "OPENROUTER_API_KEY":"test-key"}, clear=True):
            result = review({"editorial_intelligence":{"free_llm_enabled":True}}, ideas, {}, post,
                            state_path=Path(tmp)/"state.db", quota_reader=lambda *_a, **_kw: Response(data={}))
        self.assertTrue(result["completed_discussion"])
        self.assertEqual([len(batch) for batch in requested], [5, 5, 0, 0])
        self.assertEqual(requested[0] + requested[1], [idea["id"] for idea in ideas])

    def test_public_trends_and_competitor_feeds_are_parsed_with_provenance(self):
        trend='<rss><channel><item><title>Türk tarihi harita</title><link>https://trends.example/item</link></item></channel></rss>'.encode()
        atom='''<feed xmlns="http://www.w3.org/2005/Atom" xmlns:media="http://search.yahoo.com/mrss/" xmlns:yt="http://www.youtube.com/xml/schemas/2015"><entry><yt:videoId>abc</yt:videoId><media:group><media:community><media:statistics views="1234"/></media:community></media:group><title>Harita ve tarih</title>
            <link href="https://youtube.example/video"/><published>2026-11-20T12:00:00Z</published></entry></feed>'''.encode()
        def get(url,**kwargs): return Response(content=trend if 'trends.google.com' in url else atom)
        config={'google_trends_rss':'https://trends.google.com/trending/rss?geo=TR',
            'competitor_youtube_channels':[{'name':'Rakip','channel_id':'UCtest'}],'research_timeout_seconds':2}
        result=collect_public_research(config,get)
        self.assertEqual(result['evidence_counts'],{'trend_items':1,'competitor_channels':1,'competitor_videos':1})
        self.assertEqual(result['competitors'][0]['videos'][0]['title'],'Harita ve tarih')
        self.assertIn('public RSS',result['method'])
        self.assertEqual(result['competitors'][0]['videos'][0]['views'], 1234)
        self.assertIsNone(result['competitors'][0]['videos'][0]['shares'])

    def test_relative_scores_use_trends_competitor_coverage_and_past_metrics(self):
        research={'trends':[{'title':'Rosetta Stone discovery'}],
            'competitors':[{'videos':[{'title':'The Rosetta Stone', 'views':100000,
                'likes':4000,'comments':20,'metrics_source':'https://example.com'}]}]}
        ranked=score_ideas(research, [])
        by_id={item['id']:item for item in ranked}
        rosetta=by_id['rosetta-tasinin-metni']
        record=rosetta['evidence']['comparable_videos'][0]
        self.assertEqual(record['known_like_comment_rate'],0.0402)
        self.assertIsNone(record['shares'])
        self.assertEqual(rosetta['estimated_cost_try'],0)
        self.assertGreater(rosetta['potential_index'],next(
            item['potential_index'] for item in score_ideas({},[]) if item['id']==rosetta['id']))
        self.assertFalse(build_debate(ranked,research,[])['actual_llm_used'])

    def test_official_youtube_api_keeps_share_null_and_preserves_zero(self):
        feed=b'<feed xmlns="http://www.w3.org/2005/Atom" xmlns:yt="http://www.youtube.com/xml/schemas/2015"><entry><yt:videoId>video</yt:videoId><title>Rosetta Stone</title></entry></feed>'
        def get(url, **kwargs):
            if 'googleapis.com' in url:
                return Response(data={'items':[{'id':'video','statistics':{'viewCount':'1200','likeCount':'0','commentCount':'10'}}]})
            if 'youtube' in url:
                return Response(content=feed)
            return Response(content=b'<rss/>')
        with patch.dict('os.environ', {'YOUTUBE_DATA_API_KEY':'private'},clear=True):
            data=collect_public_research({'google_trends_rss':'https://trends.example',
                  'competitor_youtube_channels':[{'channel_id':'UCtest'}]}, get)
        video=data['competitors'][0]['videos'][0]
        self.assertEqual((video['views'],video['likes'],video['comments'],video['shares']), (1200,0,10,None))
        self.assertNotIn('private',json.dumps(data))

    def test_coordinator_writes_weekly_reviewable_decision_report(self):
        research={'collected_at_utc':'2026-11-24T00:00:00Z','method':'fixture','trends':[],
            'competitors':[],'errors':[],'evidence_counts':{'trend_items':0,'competitor_channels':0,'competitor_videos':0}}
        with tempfile.TemporaryDirectory() as d:
            report=run_board(d,{'research_timeout_seconds':1,'historical_data_file':'unused'},Path(d)/'none.jsonl',
                research_fn=lambda _:research,llm_fn=lambda *_:{'status':'disabled','calls':0,'actual_llm_used':False},
                insights_fn=lambda:{'status':'disabled','read_only':True,'published':False,'records':[]})
            self.assertEqual(len(report['recommendations']),10)
            self.assertEqual(len(report['strategy']['categories_compared']),6)
            self.assertTrue((Path(d)/'EDITORIAL_DECISION_REPORT.md').exists())
            self.assertEqual(report['status'], 'preliminary_only')
            self.assertFalse(report['coordinator_llm']['actual_llm_used'])
            self.assertFalse(report['instagram_publish_enabled'])

    def test_editorial_llm_calls_real_roles_only_with_explicit_gate(self):
        settings={'editorial_intelligence':{'free_llm_enabled':True}}
        inputs=[{'id':'example','sources':[{'url':'https://example.org/archive'}]}]
        requests=[]
        def post(url, **kwargs):
            payload=kwargs['json']
            requests.append(payload)
            self.assertEqual(payload['model'], 'nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free')
            self.assertEqual(payload['reasoning'], {'effort': 'none'})
            self.assertEqual(payload['provider']['max_price'], {'prompt':0, 'completion':0, 'request':0})
            self.assertFalse(kwargs['allow_redirects'])
            return Response(data={'model':'test/free','choices':[{'message':{'content':json.dumps({
                'selected_idea_id':'example','rationale':'Kaynak var',
                'research_queue':[{'title':'Arşiv','source_url':'https://example.org/archive'}, {'title':'Uydurma','source_url':'https://invented.example'}]
            })}}]})
        with tempfile.TemporaryDirectory() as tmp, patch.dict('os.environ',{'ENABLE_FREE_LLM':'1','OPENROUTER_API_KEY':'mock'},clear=True):
            result=review(settings, inputs, {}, post, state_path=Path(tmp)/'state.db',
                          quota_reader=lambda *_args, **_kwargs: Response(data={'data': {}}))
        self.assertTrue(result['actual_llm_used'])
        self.assertTrue(result['completed_discussion'])
        self.assertEqual(result['calls'],4)
        self.assertEqual(len(result['decision']['research_queue']),1)
        self.assertEqual(len(json.loads(requests[-1]['messages'][1]['content'])['previous_roles']),3)
        with patch.dict('os.environ',{'ENABLE_FREE_LLM':'1'},clear=True):
            result=review(settings, inputs, {}, post)
        self.assertFalse(result['actual_llm_used'])
        self.assertIn('OPENROUTER_API_KEY',result['requirements_missing'])

    def test_editorial_review_stops_on_unexpected_cost(self):
        from unittest.mock import Mock
        mock = Mock(return_value=Response(data={'usage':{'cost':0.01}}))
        with tempfile.TemporaryDirectory() as tmp, patch.dict('os.environ', {'ENABLE_FREE_LLM':'1','OPENROUTER_API_KEY':'test-key'}, clear=True):
            result = review({'editorial_intelligence':{'free_llm_enabled':True}}, [{'id':'a'}], {}, mock,
                            state_path=Path(tmp)/'state.db', quota_reader=lambda *_args, **_kwargs: Response(data={'data': {}}))
        self.assertEqual(result['calls'],1)
        self.assertFalse(result['completed_discussion'])
        self.assertFalse(result['paid_fallback'])
        self.assertNotIn('test-key', json.dumps(result))

    def test_auto_selection_uses_ready_editorial_candidates_and_keeps_legacy_explicit(self):
        items=[{'id':'legacy'},{'id':'world','narration':['hook'],'category':'kesif'}]
        report={'recommendations':[{'id':'research-only'},{'id':'world'}]}
        self.assertEqual(select_topic(items,'',report)['id'],'world')
        self.assertEqual(select_topic(items,'legacy',report)['id'],'legacy')
        self.assertIsNone(select_topic(items[:1],'',report))

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
        self.assertIn('python -m scripts.verify_production', workflow)
        self.assertIn('--require-llm', workflow)
        self.assertIn("github.event_name == 'workflow_dispatch' && inputs.confirm_gemini_free_project == true", workflow)
        self.assertIn('--voice-provider gemini_tts --confirm-gemini-free-project', workflow)
        self.assertIn('python -m scripts.ai_agents', workflow)
        self.assertIn('--require-specialists', workflow)
        self.assertNotIn('instagram_publish.py',workflow)
        self.assertIn("ENABLE_20_LLM_AGENTS: '0'",workflow)

if __name__=='__main__': unittest.main()
