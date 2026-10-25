import 'package:flutter/material.dart';

import 'jobs.dart';

const confirmedColor = Color(0xff78d8b5);
const reviewColor = Color(0xffffce80);
const mutedColor = Color(0xffb5b6c4);

Widget statusTag(String text, {bool confirmed = false, bool review = true}) {
  final color = confirmed
      ? confirmedColor
      : review
      ? reviewColor
      : const Color(0xffbca8ff);
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
