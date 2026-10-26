import 'package:flutter/material.dart';

import 'jobs.dart';

const confirmedColor = Color(0xff78d8b5);
const reviewColor = Color(0xffffce80);
const mutedColor = Color(0xffb5b6c4);
const surfaceColor = Color(0xff181c28);

Color categoryAccent(String category) =>
    const {
      'vfx': Color(0xffbca3ff),
      'programming': Color(0xff7bd8f5),
      'electricity': Color(0xffffd17a),
      'courses': Color(0xff78dfc0),
      'public': Color(0xffffadce),
    }[category] ??
    const Color(0xffbca3ff);

IconData categoryIcon(String category) =>
    const {
      'vfx': Icons.sports_esports_outlined,
      'programming': Icons.code_rounded,
      'electricity': Icons.bolt_rounded,
      'courses': Icons.school_outlined,
      'public': Icons.account_balance_outlined,
      'applications': Icons.send_outlined,
      'settings': Icons.settings_outlined,
    }[category] ??
    Icons.radar;

class RadarHeader extends StatelessWidget {
  final String title, subtitle, category;
  const RadarHeader({
    super.key,
    required this.title,
    required this.subtitle,
    required this.category,
  });
  @override
  Widget build(BuildContext context) {
    final accent = categoryAccent(category);
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [accent.withValues(alpha: .16), surfaceColor],
        ),
        borderRadius: BorderRadius.circular(22),
        border: Border.all(color: accent.withValues(alpha: .25)),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: accent.withValues(alpha: .12),
              borderRadius: BorderRadius.circular(16),
            ),
            child: Icon(categoryIcon(category), color: accent, size: 28),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: const TextStyle(
                    fontSize: 24,
                    fontWeight: FontWeight.w800,
                    letterSpacing: -.5,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  subtitle,
                  style: const TextStyle(
                    color: mutedColor,
                    fontSize: 12,
                    height: 1.4,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

Color applicationTone(String state) =>
    const {
      'applied': Color(0xffbca3ff),
      'interview': Color(0xff7bd8f5),
      'offer': confirmedColor,
      'rejected': Color(0xffffa4ad),
      'withdrawn': mutedColor,
    }[state] ??
    mutedColor;

Widget statusTag(
  String text, {
  bool confirmed = false,
  bool review = true,
  Color? tone,
}) {
  final color =
      tone ??
      (confirmed
          ? confirmedColor
          : review
          ? reviewColor
          : const Color(0xffbca8ff));
  return Container(
    margin: const EdgeInsets.only(top: 8),
    padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
    decoration: BoxDecoration(
      color: color.withValues(alpha: .10),
      borderRadius: BorderRadius.circular(8),
    ),
    child: Text(
      text,
      style: TextStyle(color: color, fontSize: 12, fontWeight: FontWeight.w600),
    ),
  );
}

String readableDate(Object? raw) {
  final date = DateTime.tryParse('$raw')?.toLocal();
  if (date == null) return 'Sin fecha confirmada';
  if (RegExp(r'^\d{4}-\d{2}-\d{2}$').hasMatch('$raw')) {
    return '${date.day}/${date.month}/${date.year}';
  }
  return '${date.day}/${date.month}/${date.year} · ${date.hour.toString().padLeft(2, '0')}:${date.minute.toString().padLeft(2, '0')}';
}

String? deadlineNotice(Object? raw, {DateTime? now}) {
  final deadline = DateTime.tryParse('$raw');
  if (deadline == null) return null;
  final today = now ?? DateTime.now();
  final days = DateTime.utc(
    deadline.year,
    deadline.month,
    deadline.day,
  ).difference(DateTime.utc(today.year, today.month, today.day)).inDays;
  if (days < 0 || days > 7) return null;
  return days == 0
      ? 'Último día publicado · confirmar plazo'
      : 'Plazo publicado: $days días · confirmar';
}

String durationLabel(Object? value) {
  if (value is! num) return 'Duración por confirmar';
  final minutes = (value * 60).round();
  return '${minutes ~/ 60 > 0 ? '${minutes ~/ 60} h ' : ''}${minutes % 60 > 0 ? '${minutes % 60} min' : ''}'
      .trim();
}

String coursePrice(Map<String, dynamic> item) {
  if (item['sourcePrice'] is num && item['sourceCurrency'] is String) {
    return '${item['sourcePrice']} ${item['sourceCurrency']}${item['price'] is num ? ' (≈${(item['price'] as num).round()} €)' : ' · cambio por consultar'}';
  }
  return item['price'] == 0
      ? 'Gratis'
      : item['price'] is num
      ? '${item['price']} €'
      : 'Precio por consultar';
}

Future<void> showProvenance(
  BuildContext context,
  Map<String, dynamic> item,
  Future<void> Function(Object?) open,
) => showModalBottomSheet<void>(
  context: context,
  isScrollControlled: true,
  useSafeArea: true,
  showDragHandle: true,
  builder: (context) => SingleChildScrollView(
    padding: const EdgeInsets.all(24),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Text('De dónde sale', style: Theme.of(context).textTheme.headlineSmall),
        const SizedBox(height: 16),
        Text(
          'Encontrada en: ${(item['foundIn'] as List? ?? [item['source'] ?? item['provider'] ?? item['ats'] ?? 'Empresa']).join(', ')}',
        ),
        Text(
          'Publicado por: ${item['company'] ?? item['provider'] ?? 'Por confirmar'}',
        ),
        Text(
          'Método: ${('${item['id']}'.startsWith('course-sidefx-') && item['source'] == 'SideFX') || item['source'] == 'Adecco'
              ? 'Ficha seleccionada con comprobación automática'
              : item['provider'] != null && !['eFundae', 'SideFX', 'Xunta / DIPLOS', 'CNTG'].contains(item['source'] ?? item['provider']) && !'${item['id']}'.startsWith('course-diplos-') && !'${item['id']}'.startsWith('course-cntg-')
              ? 'Selección fija de recursos; consultar vigencia en el proveedor'
              : 'Recogida automática de una fuente pública'}',
        ),
        Text(
          'Última comprobación guardada: ${readableDate(item['checkedAt'] ?? item['lastSeen'])}',
        ),
        if (item['retainedAfterFailure'] == true)
          statusTag('No se pudo renovar. Se conserva la revisión anterior.'),
        const SizedBox(height: 12),
        const Text(
          'Una consulta correcta no garantiza contratación, plaza disponible ni que cumplas todos los requisitos.',
        ),
        if (safeUrl(item['originalUrl'] ?? item['url']) != null)
          Padding(
            padding: const EdgeInsets.only(top: 16),
            child: FilledButton.icon(
              onPressed: () => open(item['originalUrl'] ?? item['url']),
              icon: const Icon(Icons.open_in_new),
              label: const Text('Abrir página original'),
            ),
          ),
      ],
    ),
  ),
);
