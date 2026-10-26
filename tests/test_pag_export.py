from scanner.pag_export import parse_export


def entry(ref, scope='AUTONÓMICO', level='3', free=2, end='30/10/2026', start='01/10/2026'):
    return f'''<convocatorias><id>{ref}</id><referencia>{ref}</referencia>
    <titulo>TÉCNICO/A SUPERIOR</titulo><descripcion>Informática</descripcion>
    <idniveltitulacion>{level}</idniveltitulacion><viagrupoid>2</viagrupoid>
    <plazaslibres>{free}</plazaslibres><plazasconvocadas>3</plazasconvocadas>
    <ambito>{scope}</ambito><administracionconvocanteid>{'1' if scope=='NACIONAL' else '2'}</administracionconvocanteid>
    <organo>Servicio de Salud</organo><titulacion>FP DAM</titulacion>
    <plazos><fechainicio>01/01/2025</fechainicio><fechafin>30/01/2025</fechafin></plazos>
    <plazos><fechainicio>{start}</fechainicio><fechafin>{end}</fechafin></plazos>
    </convocatorias>'''


def test_export_handles_extended_deadlines_and_administration_independent_of_geography():
    xml='<convocatorias>'+entry('1')+entry('2','NACIONAL')+entry('expired',end='20/10/2026')+entry('university',level='1')+entry('reserved',free=0)+entry('future',start='01/11/2026',end='30/11/2026')+'</convocatorias>'
    rows,total=parse_export(xml,'2026-10-26T12:00:00Z')
    assert total==6 and len(rows)==2
    assert rows[0]['closingDate']=='2026-10-30'
    assert rows[0]['adminScope']=='autonomous'
    assert rows[1]['adminScope']=='state' and rows[1]['area']=='national'


def test_export_is_not_an_html_error_page():
    import pytest
    with pytest.raises(ValueError):parse_export('<html></html>','2026-10-26')
