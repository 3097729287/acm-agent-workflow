"""Semantic and portable corpus checks; no real personal database is opened."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

_test_common = Path(__file__).resolve().parent / "common"
sys.path.insert(0,str(_test_common if _test_common.is_dir() else Path(__file__).resolve().parent.parent))
import knowledge as K
import lecture_curation as C
from lecture_library import LectureLibrary


class AnalysisTests(unittest.TestCase):
    def test_reviewed_archive_corrections_keep_source_and_distinguish_algorithms(self):
        cases=[('月赛 303::C',['线性 DP','KMP'],'Z 函数','KMP'),
               ('练习赛 152::G',['字典树','结论与计数'],'后缀自动机','字典树'),
               ('挑战赛 87::D',['字典树','DFS 序'],'虚树','字典树'),
               ('Div.2 1115::F',['字典树','树状数组'],'虚树','字典树')]
        for identity,tags,expected,removed in cases:
            row={'id':identity,'tags':tags,'solutionAvailable':True}
            value=K.enrich_row(row)
            self.assertIn(expected,value['tags'])
            self.assertNotIn(removed,value['tags'])
            self.assertEqual(value['sourceTags'],tags)
            self.assertEqual(value['knowledgeAnalysis']['source'],'archive-lesson')
            self.assertTrue(value['solutionAvailable'])
            value['knowledgeAnalysis']['tags'].append(removed)
            self.assertNotIn(removed,K.enrich_row(value)['tags'])
        remote=K.enrich_row({'id':'remote:codeforces:2252::F','tags':['trees'],'source':'remote','solutionAvailable':False})
        self.assertIn('虚树',remote['tags'])
        self.assertFalse(remote['solutionAvailable'])
        unrelated=K.enrich_row({'id':'unreviewed::A','tags':['字典树']})
        self.assertEqual(unrelated['tags'],['字典树'])

    def test_official_broad_tags_do_not_invent_specific_algorithms(self):
        row={'id':'remote:codeforces:1::A','source':'remote','tags':['dp','trees','strings','math'],
             'solutionAvailable':False,'solutionState':'missing'}
        result=K.enrich_row(row)
        self.assertEqual(result['tags'],[])
        self.assertEqual(result['knowledgeAnalysis']['confidence'],'pending')
        self.assertEqual(set(result['knowledgeCategories']),{'动态规划','图论 / 树','字符串','数学'})
        self.assertFalse(result['solutionAvailable'])
        self.assertEqual(result['solutionState'],'missing')
        self.assertEqual(row['tags'],['dp','trees','strings','math'])

    def test_named_technique_and_model_have_provenance(self):
        row={'id':'remote:fixture::B','source':'remote','tags':[],'solutionAvailable':False}
        result=K.enrich_row(row,statement='Given an unweighted graph, find the shortest distance between two vertices.')
        self.assertIn('BFS',result['tags'])
        self.assertIn('最短路',result['tags'])
        self.assertEqual(result['knowledgeAnalysis']['source'],'statement-analysis')
        self.assertFalse(result['solutionAvailable'])
        again=K.enrich_row(result)
        self.assertIn('BFS',again['tags'])
        self.assertEqual(again['knowledgeAnalysis']['confidence'],'medium')
        weighted=K.enrich_row(row,statement='Given a directed graph with positive weights, find the shortest distance.')
        self.assertNotIn('BFS',weighted['tags'])

    def test_samples_are_not_algorithm_evidence(self):
        result=K.analyze_problem({'source':'remote'},statement='Input example:\n```text\nBFS segment tree NTT\n```\nFind the answer.')
        self.assertEqual(result['tags'],[])
        prime=K.analyze_problem({'source':'remote'},statement='Compute gcd(x,y) for two integers.')
        self.assertIn('数学 / 数论',prime['categories'])
        self.assertNotIn('素数',prime['tags'])

    def test_aliases_and_parent_chain(self):
        self.assertEqual(K.canonical_tag('Z-function'),'Z 函数')
        self.assertEqual(K.canonical_tag('状态压缩DP'),'状压 DP')
        self.assertEqual(K.canonical_tag('suffix automaton'),'后缀自动机')
        self.assertIn('动态规划',K.category_path('分治优化 DP'))
        self.assertEqual(K.category_path('Z 函数'),'字符串')

    def test_frozen_asset_path_uses_application_directory(self):
        with patch.object(sys,'frozen',True,create=True),patch.object(sys,'executable','C:/portable/TB.exe'):
            self.assertEqual(K.asset_path('curated_lectures.json'),Path('C:/portable/curated_lectures.json'))


class CurationTests(unittest.TestCase):
    def test_fenced_fake_headings_are_not_lessons(self):
        text='# Fixture\n\n## A. Real\n\n````cpp\n// ### 从零讲：错误\n## B. Fake\n```\n````\n\n### 从零讲：构造\n\n真实正文\n'
        parsed=C.parse_document(text)
        self.assertEqual(set(parsed['problems']),{'A'})
        self.assertEqual([h['title'] for h in parsed['headings']],['Fixture','A. Real','从零讲：构造'])

    def test_curated_lesson_retains_source_and_canonical_structure(self):
        source='### 从零讲：能怎么拼\n\n原有例子 $x^2$。\n\n```cpp\nint answer=42;\n```\n'
        entry={'id':'fixture','title':'从零讲：能怎么拼','sourceContest':'ABC 473','sourceProblem':'F',
               'sourceTitle':'A/AB Insertion','tags':['线段树','前缀和']}
        result=C.curate(entry,source)
        self.assertEqual(result['knowledgeName'],'前缀和')
        self.assertEqual(result['sourceMarkdown'],source)
        for section in ('定义','作用','手算例子','本题应用','为何可行','易错点','本题完整推导与原有例子'):
            self.assertIn('## '+section+'\n',result['markdown'])
        self.assertTrue(set(C.code_hashes(source)).issubset(C.code_hashes(result['markdown'])))
        self.assertIn('`BA`',result['markdown'])
        self.assertEqual(result['sourceHash'],hashlib.sha256(source.encode()).hexdigest())

    def test_portable_export_has_canonical_titles_and_unabridged_code(self):
        path=K.asset_path('curated_lectures.json')
        payload=json.loads(path.read_text(encoding='utf-8'))
        self.assertGreater(payload['audit']['contestDocumentCount'],100)
        self.assertGreater(payload['audit']['sourceProblemCount'],700)
        self.assertEqual(payload['audit']['unreadSourceCount'],0)
        self.assertEqual(payload['audit']['sourceMutations'],0)
        self.assertFalse(payload['audit']['sourceAlgorithmReverified'])
        self.assertEqual(len(payload['lectures']),payload['audit']['lectureCount'])
        for entry in payload['lectures']:
            self.assertEqual(K.canonical_tag(entry['knowledgeName']),entry['knowledgeName'],entry['id'])
            self.assertEqual(entry['displayTitle'],entry['knowledgeName']+'：'+entry['topic'])
            self.assertNotRegex(entry['displayTitle'],r'[$\\]')
            self.assertTrue(entry['category'],entry['id'])
            self.assertEqual(hashlib.sha256(entry['sourceMarkdown'].encode()).hexdigest(),entry['sourceHash'])
            self.assertRegex(entry['originalSourceHash'],r'^[0-9a-f]{64}$')
            self.assertNotRegex(entry['sourceMarkdown'],r'`[A-Za-z]:[\\/]')
            self.assertNotRegex(entry['markdown'],r'`[A-Za-z]:[\\/]')
            self.assertTrue(set(entry['sourceCodeHashes']).issubset(C.code_hashes(entry['markdown'])),entry['id'])
            self.assertTrue(all(K.canonical_tag(t)==t for t in entry['tags']),entry['id'])
            self.assertFalse(Path(entry['sourcePath']).is_absolute())
        topics={e['sourceContest']+'::'+e['sourceProblem']:e['knowledgeName'] for e in payload['lectures']}
        self.assertEqual(topics['月赛 303::C'],'Z 函数')
        self.assertEqual(topics['练习赛 152::G'],'后缀自动机')
        self.assertEqual(topics['Div.2 1115::F'],'虚树')
        self.assertIn('周赛 163::C',topics)

    def test_fresh_install_can_load_corpus_without_archive_or_memory(self):
        with tempfile.TemporaryDirectory(prefix='tb-v5-lecture-bundle-') as folder:
            store=SimpleNamespace(data_root=Path(folder),raw_rows=lambda:[])
            library=LectureLibrary(store,registry_path=Path(folder)/'missing-registry.md')
            data=library.snapshot()
            self.assertGreater(len(data['lectures']),350)
            self.assertTrue(data['audit']['usingBundledCorpus'])
            first=data['lectures'][0]
            self.assertEqual(library.get(first['id'])['id'],first['id'])
            self.assertNotIn('sourceMarkdown',first)
            self.assertFalse((Path(folder)/'lecture-audit.json').exists())


if __name__=='__main__':unittest.main()
