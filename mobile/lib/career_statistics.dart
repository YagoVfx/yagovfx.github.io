import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'career_categories.dart';

String careerPlatform(Map<String, dynamic> row) {
  final text = '${row['source']} ${row['company']}'.toLowerCase();
  for (final ats in [
    'Workable',
    'Recruitee',
    'SuccessFactors',
    'SmartRecruiters',
  ]) {
    if (text.contains(ats.toLowerCase())) return ats;
  }
  if (text.contains('indra')) return 'SuccessFactors';
  return 'Web / portal público';
}

class CareerStatistics extends StatefulWidget {
  const CareerStatistics({super.key});
  @override
  State<CareerStatistics> createState() => _CareerStatisticsState();
}

class _CareerStatisticsState extends State<CareerStatistics> {
  Map<String, dynamic>? feed, catalog;
  String category = 'programming';
  @override
  void initState() {
    super.initState();
    load();
  }

  Future<void> load() async {
    final prefs = await SharedPreferences.getInstance();
    final repository = CareerFeedRepository();
    var data = repository.decode(
      await rootBundle.loadString('assets/mobile-careers.json'),
    );
    try {
      data = repository.decode(prefs.getString('career.feed') ?? '');
    } catch (_) {}
    final resources = jsonDecode(
      await rootBundle.loadString('assets/career-resources.json'),
    ) as Map<String, dynamic>;
    if (mounted) {
      setState(() {
        feed = data;
        catalog = resources;
      });
    }
    try {
      data = await repository.refresh(prefs);
      if (mounted) setState(() => feed = data);
    } catch (_) {
    } finally {
      repository.close();
    }
  }

  List<Widget> distribution(String title, Iterable<dynamic> values) {
    final counts = <String, int>{};
    for (final value in values) {
      final key =
          const {
            'beginner': 'Inicial',
            'intermediate': 'Intermedio',
            'advanced': 'Avanzado',
            'review': 'Revisión de conocimientos',
            'unknown': 'Sin confirmar',
            'experienced': 'Experiencia alta',
            'junior': 'Inicial / junior',
            'online': 'Online',
            'onsite': 'Presencial',
            'course': 'Curso',
            'tutorial': 'Tutorial práctico',
            'guide': 'Guía',
          }[value] ??
          '${value ?? 'Sin confirmar'}';
      counts[key] = (counts[key] ?? 0) + 1;
    }
    final rows = counts.entries.toList()
      ..sort((a, b) => b.value.compareTo(a.value));
    final total = rows.fold<int>(0, (n, r) => n + r.value);
    return [
      ExpansionTile(
        title: Text(title),
        children: [
          for (final row in rows)
            ListTile(
              dense: true,
              title: Text(row.key),
              trailing: Text(
                '${row.value} · ${total == 0 ? 0 : (100 * row.value / total).round()}%',
              ),
            ),
        ],
      ),
    ];
  }

  @override
  Widget build(BuildContext context) {
    if (feed == null) return const Center(child: CircularProgressIndicator());
    final courses = category == 'courses';
    final rows = courses
        ? [
            ...feed!['courses'],
            ...catalog!['courses'],
          ].cast<Map<String, dynamic>>()
        : (feed!['offers'] as List)
              .cast<Map<String, dynamic>>()
              .where((r) => r['category'] == category)
              .toList();
    final valid = courses
        ? rows
        : rows.where((r) => !expiredCareerOffer(r, DateTime.now())).toList();
    final connected = <String, int>{
      for (final s in (feed!['sources'] as List).where(
        (s) =>
            (s['categories'] as List? ?? []).contains(category) &&
            s['sourceKind'] == 'ats',
      ))
        '${s['platform']}': 0,
    };
    for (final row in valid) {
      final platform = careerPlatform(row);
      if (connected.containsKey(platform)) {
        connected[platform] = connected[platform]! + 1;
      }
    }
    return RefreshIndicator(
      onRefresh: load,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          DropdownButtonFormField<String>(
            initialValue: category,
            decoration: const InputDecoration(labelText: 'Estadísticas'),
            items: [
              for (final e in careerCategories.entries)
                DropdownMenuItem(value: e.key, child: Text(e.value)),
            ],
            onChanged: (v) => setState(() => category = v!),
          ),
          const SizedBox(height: 16),
          Text(
            '${valid.length} ${courses ? 'recursos de formación' : 'ofertas de portales complementarios'}',
          ),
          const Text(
            'Catálogo sin filtros personales. Importado no significa compatible. El scanner VFX directo tiene su gráfica propia.',
          ),
          if (courses) ...[
            Text(
              '${(feed!['courses'] as List).length} automáticos · ${(catalog!['courses'] as List).length} seleccionados',
            ),
            ...distribution(
              'Proveedor',
              rows.map((r) => r['source'] ?? r['provider']),
            ),
            ...distribution(
              'Especialidad',
              rows.map((r) => careerCategories[r['topic']]),
            ),
            ...distribution('Nivel', rows.map((r) => r['level'])),
            ...distribution('Modalidad', rows.map((r) => r['modality'])),
            ...distribution(
              'Coste',
              rows.map(
                (r) => r['price'] == 0
                    ? 'Gratis / subvencionado'
                    : 'De pago o por confirmar',
              ),
            ),
            ...distribution('Tipo de recurso', rows.map((r) => r['kind'])),
          ] else ...[
            Text(
              'ATS conectados',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            if (connected.isEmpty)
              const Text(
                'Este catálogo usa webs o portales; el scanner VFX directo se consulta por separado.',
              ),
            for (final ats in connected.entries)
              ListTile(
                dense: true,
                title: Text(ats.key),
                trailing: Text('${ats.value} ofertas'),
              ),
            ...distribution('Procedencia y ATS', valid.map((r) => r['source'])),
            ...distribution('Experiencia', valid.map((r) => r['experience'])),
          ],
          ExpansionTile(
            title: const Text('Conectores y último estado'),
            children: [
              const ListTile(
                subtitle: Text(
                  'Consulta correcta con cero coincidencias no significa que no existan vacantes. Estas consultas son parciales.',
                ),
              ),
              for (final source in (feed!['sources'] as List).where(
                (s) => (s['categories'] as List? ?? []).contains(category),
              ))
                ListTile(
                  title: Text(source['name']),
                  subtitle: Text(
                    source['status'] == 'ok'
                        ? '${source['matched'] ?? source['examined'] ?? 0} ${source['matched'] != null ? 'incorporadas' : 'examinadas'}'
                        : '${source['reason']}',
                  ),
                  leading: Icon(
                    source['status'] == 'ok'
                        ? Icons.check_circle_outline
                        : Icons.warning_amber,
                  ),
                ),
            ],
          ),
          Text('Datos: ${feed!['updatedAt']}'),
        ],
      ),
    );
  }
}
