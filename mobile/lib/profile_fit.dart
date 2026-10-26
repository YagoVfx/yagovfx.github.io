import 'jobs.dart';

/// A job title is not evidence of a mandatory university qualification.
String educationFit(Map<String, dynamic> item) {
  final text = fold('${item['description'] ?? ''}');
  final fp = RegExp(
    r'formacion profesional|ciclo.{0,20}superior|grado (?:medio|superior|medio/superior)|\bfp2?\b|\bdam\b',
  ).hasMatch(text);
  final alternative = RegExp(
    r'(?:degree|bachelor|universitari|ingenieria).{0,100}(?:or equivalent|equivalent experience|o experiencia equivalente|o fp|o formacion profesional)',
  ).hasMatch(text);
  final university = RegExp(
    r'(?:required|must have|mandatory|looking for).{0,60}(?:bachelor|degree|b\.s\.)|(?:bachelor|university degree).{0,35}(?:required|mandatory)|(?:imprescindible|obligatori[oa]|requisito).{0,60}(?:ingenieria|grado universitario)|(?:ingenieria|grado universitario).{0,35}(?:obligatori|imprescindible)',
  ).hasMatch(text);
  final universityTraining = RegExp(
    r'formacion universitaria|estudios universitarios|titulacion universitaria',
  ).hasMatch(text);
  final preferred = RegExp(
    r'(?:valorable|preferible|preferentemente|se valorara).{0,60}(?:universitari|ingenieria)|(?:universitari\w*|ingenieria).{0,30}(?:valorable|preferible)',
  ).hasMatch(text);
  if ((university || universityTraining && !preferred) && !alternative) {
    return 'university';
  }
  if (fp) return 'fp';
  if (alternative) return 'experience';
  return 'unknown';
}

bool entryProfile(Map<String, dynamic> item) =>
    item['experience'] != 'experienced' &&
    educationFit(item) != 'university' &&
    (educationFit(item) == 'fp' ||
        item['experience'] == 'junior' ||
        RegExp(
          r'junior|fresh graduate|entry.level|trainee|\bbeca|internship|sin experiencia',
        ).hasMatch(fold('${item['title']}')));

String fitLabel(Map<String, dynamic> item) {
  if (item['profileMatch'] == 'outside') {
    return 'Fuera de tu especialidad o nivel';
  }
  if (item['profileMatch'] == 'retrain') {
    return 'Requiere reciclaje o experiencia previa';
  }
  if (item['profileMatch'] == 'review') {
    return 'Confirmar acceso sin experiencia';
  }
  if (item['profileMatch'] == 'current') {
    return item['category'] == 'electricity'
        ? 'Instalaciones y mantenimiento eléctrico'
        : 'Desarrollo de entrada · revisar requisitos';
  }
  if (educationFit(item) == 'university') return 'Exige universidad';
  if (item['experience'] == 'experienced') return 'Experiencia alta';
  if (RegExp(r'\bbeca|internship|practicas')
      .hasMatch(fold('${item['title']}'))) {
    return 'Prácticas: comprobar acceso';
  }
  if (educationFit(item) == 'fp') return 'FP mencionada; revisar requisitos';
  if (educationFit(item) == 'experience') return 'Pide experiencia equivalente';
  return 'Requisitos por confirmar';
}
