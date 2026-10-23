import unittest
from scanner.filters import classify_job, evaluate_spain_eligibility, detect_workplace, detect_remote_scope
from scanner.scanner import attach_company_careers_links
from unittest.mock import patch

class AuditFixTests(unittest.TestCase):
    def test_restricted_role_stays_indexable(self):
        self.assertEqual(classify_job('Senior VFX Artist', 'must be based in the UK'), 'exactMatch')
    def test_restricted_role_flagged(self):
        self.assertEqual(evaluate_spain_eligibility('VFX Artist', 'Remote US', 'must reside in the United States')[0], 'restricted')
    def test_ambiguous_remains_unknown(self):
        self.assertEqual(evaluate_spain_eligibility('VFX Artist','Remote', '', 'remote')[0], 'unknown')
    def test_hybrid_not_mislabeled_remote(self):
        self.assertEqual(detect_workplace('', 'Remote hybrid', ''), 'hybrid')
    def test_country_over_worldwide(self):
        self.assertEqual(detect_remote_scope('', 'Worldwide, Spain'), 'Spain')
    def test_do_not_replace_vacancy_with_careers_landing(self):
        jobs=[dict(id='a',company='Studio',url='https://aggregator.example/vacancy/123',ats='adzuna',viaAggregator=True)]
        with patch('scanner.scanner.discover_direct_source',return_value={'careersUrl':'https://studio.example/careers','ats':'greenhouse'}):
            res,n=attach_company_careers_links(jobs,{})
        self.assertEqual(res[0]['url'], jobs[0]['url'])
        self.assertEqual(res[0]['companyCareersUrl'],'https://studio.example/careers')
        self.assertEqual(res[0]['ats'], 'adzuna')
        self.assertTrue(res[0]['viaAggregator'])

if __name__ == '__main__': unittest.main()
