from scanner.vacancy_identity import unify, vacancy_url


def test_smartrecruiters_suffix_variants_share_identity_without_merging_requisitions():
    direct = [dict(id='sr-123', status='active', ats='smartrecruiters', url='https://jobs.smartrecruiters.com/Gameloft/123-lead-vfx-artist')]
    offers = [dict(id='portal-1', category='vfx', source='Portal', originalUrl='https://jobs.smartrecruiters.com/Gameloft/123', url='https://portal.example/1'),
              dict(id='portal-2', category='vfx', source='Portal', url='https://jobs.smartrecruiters.com/Gameloft/124-lead-vfx-artist')]
    rows = unify(offers, direct)
    assert len(rows) == 2
    assert rows[0]['id'] == 'sr-123'
    assert 'portal-1' in rows[0]['sourceIds']
    assert rows[1]['id'] != 'sr-123'


def test_portals_share_employer_id_without_losing_aliases():
    direct = [dict(id='gh-1', url='https://jobs.example/1', status='active', ats='greenhouse')]
    offers = [dict(id='career-hitmarker-3', category='vfx', source='Hitmarker', url='https://board.example/3', originalUrl='https://jobs.example/1?utm_source=board'),
              dict(id='career-other-4', category='vfx', source='Other', url='https://jobs.example/1')]
    rows = unify(offers, direct)
    assert len(rows) == 1 and rows[0]['id'] == 'gh-1'
    assert set(rows[0]['sourceIds']) == {'gh-1', 'career-hitmarker-3', 'career-other-4'}
    assert rows[0]['foundIn'] == ['Hitmarker', 'Other']
    assert direct[0]['sourceIds'] == rows[0]['sourceIds']
    assert unify(rows, direct)[0]['id'] == rows[0]['id']


def test_url_identity_preserves_vacancy_query_not_just_the_landing_path():
    assert vacancy_url('https://example/jobs?id=1&utm_campaign=foo') == vacancy_url('https://example/jobs?id=1')
    assert vacancy_url('https://example/jobs?id=1') != vacancy_url('https://example/jobs?id=2')
    rows = unify([dict(id=str(i), category='vfx', source='Portal', url=f'https://example/jobs?id={i}') for i in [1, 2]], [])
    assert len(rows) == 2
    generic = unify([dict(id=str(i),category='vfx',source='Portal',url='https://example/jobs') for i in [1,2]], [])
    assert len(generic) == 2
