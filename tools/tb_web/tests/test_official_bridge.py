"""Official target validation only; never post code to public sites in tests."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from official_bridge import submission_target,toolbar_script
class OfficialTargets(unittest.TestCase):
    def test_four_platforms(self):
        examples=[('https://codeforces.com/contest/1003/problem/C1','Codeforces','/contest/1003/submit'),('https://atcoder.jp/contests/abc478/tasks/abc478_d','AtCoder','taskScreenName=abc478_d'),('https://ac.nowcoder.com/acm/contest/126120/F','牛客','/126120/F'),('https://www.luogu.com.cn/problem/P1001','洛谷','#submit')]
        for url,platform,end in examples:
            target=submission_target(url);self.assertEqual(target['platform'],platform);self.assertIn(end,target['url'])
    def test_reject_non_official_or_not_problem(self):
        for url in ['https://evil.test/problem/P1','https://codeforces.com@evil.test/contest/1/problem/A','https://codeforces.com/login','file:///C:/Windows/a','https://atcoder.jp:8443/contests/abc1/tasks/abc1_a']:
            with self.assertRaises(ValueError):submission_target(url)
    def test_own_code_is_data_and_no_auto_submit(self):
        script=toolbar_script('int main(){/* </script> */}\n','A')
        self.assertIn('const ctx=',script);self.assertNotIn('.submit()',script);self.assertNotIn('fetch(',script);self.assertNotIn('document.cookie',script)
if __name__=='__main__':unittest.main()
