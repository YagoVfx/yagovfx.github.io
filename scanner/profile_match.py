"""Conservative specialty checks for DAM entry roles and electrical installations."""
import re
from scanner.mobile_careers import fold


def profile_match(row):
    category=row.get('category')
    title=fold(row.get('title',''));body=fold(row.get('description',''))
    text=title+' '+body
    if category not in ('programming','electricity'):return {}
    def result(state,reason):return dict(profileMatch=state,profileReason=reason)
    if category=='electricity':
        if re.search(r'frigor|refriger|climatiz|electromecanic|mecatronic|motores industriales|diesel',title):
            return result('outside','Especialidad de electromecánica o refrigeración, distinta de instalaciones eléctricas')
        if re.search(r'oficina tecnica|disen[oa].{0,20}electric|ingenier',title):
            if re.search(r'grado superior|formacion profesional|\bfp\b',body):
                return result('retrain','Acepta FP, pero pide oficina técnica, diseño o herramientas que no constan en tu experiencia')
            return result('outside','Puesto de ingeniería o diseño; no es instalación o mantenimiento eléctrico')
        other_fp=re.search(r'(?:formacion|grado superior|grado medio|ciclo).{0,120}(?:electromecanic|mecatronic|instalaciones frigorificas)',body)
        electrical_fp=re.search(r'(?:formacion|grado superior|grado medio|ciclo).{0,160}(?:electricidad|electrotecn|electronica)',body)
        if other_fp and not electrical_fp:
            return result('outside','Solicita FP de electromecánica, mecatrónica o frío; no se confirma que acepte tu especialidad')
        if not re.search(r'electric|electrotecn|alumbrado|cablead|fotovoltaic|cuadros electric',text):
            return result('outside','No se confirma una función de electricidad relacionada con tu experiencia')
        if re.search(r'frigor|gases fluorados|motores diesel|mecanica industrial',body) and not re.search(r'instalaciones electric|electricista|alumbrado|cablead',title):
            return result('retrain','Mantenimiento mixto con requisitos de otra especialidad; revisar antes de solicitar')
        if re.search(r'\bsenior\b|\bplc\b|automatizacion',title) or re.search(r'dominio.{0,45}(?:plc|tia portal)|(?:minim[oa]|al menos).{0,25}[3-9].{0,8}anos',body):
            return result('retrain','Exige especialización o autonomía avanzada que requiere repaso y experiencia específica')
        return result('current','Instalaciones o mantenimiento eléctrico; comprobar PRL, permisos y experiencia concreta')
    if re.search(r'analytics|data (?:engineer|analyst|scientist)|machine learning|devops|\bsre\b|arquitect|architect|\bsap\b|consultor|security engineer',title):
        return result('outside','Especialización de datos, sistemas, consultoría o arquitectura; no es desarrollo DAM de entrada')
    if not re.search(r'programad|desarrollad|developer|software|backend|frontend|full.?stack|tester|\bqa\b',title):
        return result('outside','El título no identifica desarrollo de aplicaciones o pruebas de software de entrada')
    if re.search(r'\bsenior\b|\blead\b|\bstaff\b|\bprincipal\b|\bmid\b|\bsdet\b',title) or row.get('experience')=='experienced':
        return result('outside','Requiere experiencia profesional de desarrollo que todavía no tienes')
    alternative=bool(re.search(r'o (?:fp|grado superior|formacion profesional)|or equivalent (?:practical )?experience',body))
    if not alternative and re.search(r'formacion universitaria|estudios universitarios|titulacion universitaria|master.{0,20}(?:phd|degree)|bachelor.{0,25}(?:degree|required)|\bb\.s\.|\bm\.s\b',body):
        return result('outside','Exige formación universitaria y no se ha identificado una alternativa de FP')
    required_years=re.search(r'(?:minim[oa]|al menos|at least|minimum|experiencia de|experiencia:).{0,30}[1-9](?:\s*[-–]\s*[1-9])?\+?\s*(?:ano|year)|\b[1-9]\+?\s*(?:anos|years).{0,25}experien',body)
    if required_years:
        context=body[max(0,required_years.start()-140):required_years.start()]
        if not re.search(r'valorable|se valorara|deseable|bonus|impression|impresionara',context):
            return result('retrain','Pide experiencia profesional previa; revisar como opción de reciclaje, no como primer empleo')
    if re.search(r'junior|trainee|sin experiencia|no experience|entry.level|fresh graduate',title+' '+body[:250]):
        return result('current','Desarrollo de entrada; repasar tecnologías y confirmar condiciones de acceso')
    if re.search(r'experiencia (?:trabajando|en desarrollo|en estas tecnologias|full.?stack|previa|profesional)|conocimientos solidos.{0,40}imprescindible',body):
        return result('retrain','Pide dominio práctico o experiencia previa en una tecnología; no se confirma acceso de primer empleo')
    return result('review','Es desarrollo de aplicaciones, pero falta confirmar que admita tu nivel sin experiencia profesional')
