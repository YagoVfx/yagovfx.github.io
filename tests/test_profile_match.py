from scanner.profile_match import profile_match
from scanner.mobile_careers import classify_offer


def match(category,title,description='',**extra):
    return profile_match(dict(category=category,title=title,description=description,**extra))['profileMatch']


def test_data_engineering_is_not_entry_dam_development():
    assert match('programming','Analytics Engineer, Data','Production dbt models and data pipelines')=='outside'
    assert match('programming','Junior Software Engineer','FP DAM, no professional experience required')=='current'


def test_electrical_fp_does_not_mean_electromechanics_or_refrigeration():
    assert match('electricity','Electromecánico de motores industriales','FP electromecánica. Motores diésel')=='outside'
    assert match('electricity','Frigorista industrial NH3','Averías eléctricas')=='outside'
    assert match('electricity','Electricista junior','FP Electricidad. Cableado e instalaciones eléctricas')=='current'
    assert match('electricity','Técnico oficina técnica (Ingeniería Eléctrica)','Ingeniería o Grado Superior equivalente. AutoCAD')=='retrain'


def test_programming_experience_and_mandatory_university_are_checked():
    assert match('programming','Developer','Formación universitaria requerida')=='outside'
    assert match('programming','Java Developer','Experiencia mínima de 2 años')=='retrain'
    assert match('programming','Junior Developer','Se valorará experiencia de al menos 2 años')=='current'


def test_mentoring_by_senior_staff_is_not_seniority_of_the_candidate():
    row=classify_offer('Junior Developer','Trabajarás con senior developers. Sin experiencia profesional.','Vigo')
    assert row['experience']=='junior'
