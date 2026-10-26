from scanner import local_employers as sources


class Response:
    def __init__(self, data): self.data=data
    def json(self): return self.data


def test_sopra_only_accepts_spain_remote_or_verified_municipal_locations(monkeypatch):
    jobs=[dict(id='1',name='Junior Developer',location=dict(city='Madrid',country='es',remote=True),ref='detail1'),
          dict(id='2',name='Junior Developer',location=dict(city='Madrid',country='es',remote=False,hybrid=True),ref='detail2')]
    detail=dict(active=True,jobAd=dict(sections=dict(description=dict(text='FP DAM. Desarrollo Java en remoto.'))),applyUrl='https://jobs.smartrecruiters.com/SopraSteria1/1')
    monkeypatch.setattr(sources,'get',lambda url:Response(detail if url=='detail1' else dict(content=jobs,totalFound=2)))
    rows=sources.sopra('2026-10-26T12:00:00Z')
    assert len(rows)==1 and rows[0]['workplace']=='remote'
    assert rows[0]['category']=='programming'
