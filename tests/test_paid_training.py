from scanner import paid_training as module


def test_foreign_prices_are_not_labelled_as_euros(monkeypatch):
    class Response:
        def __init__(self, content):self.content=content
    def get(url):
        if 'ecb.europa.eu' in url:return Response(b'<Cube><Cube time="2026-10-23"><Cube currency="USD" rate="1.12"/></Cube></Cube>')
        return Response(b'<h1>Bringing Artistic Game Effects to Life with Niagara Unlocking the Magic Mastering the Mechanics of Advanced Niagara</h1><p>PriceUSD 260.00</p>')
    monkeypatch.setattr(module,'get',get)
    rows=module.coloso('2026-10-25T12:00:00Z')
    assert len(rows)==3
    assert rows[0]['sourcePrice']==260 and rows[0]['sourceCurrency']=='USD'
    assert rows[0]['price']==232.14 and rows[0]['priceIsEstimate']
    # Stale exchange rates do not turn a USD price into a budget-confirmed EUR price.
    assert module.coloso('2026-11-25T12:00:00Z')[0]['price'] is None
