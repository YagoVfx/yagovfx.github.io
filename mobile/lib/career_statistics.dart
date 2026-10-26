import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'career_categories.dart';
import 'jobs.dart';
import 'presentation.dart';

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
  final String initialCategory;
  final List<Job> directJobs;
  final List<dynamic> employers;
  final bool sourcesOnly;
  final VoidCallback? onDirectGraph;
  const CareerStatistics({
    super.key,
    this.initialCategory = 'programming',
    this.directJobs = const [],
    this.employers = const [],
    this.sourcesOnly = false,
    this.onDirectGraph,
  });
  @override
  State<CareerStatistics> createState() => _CareerStatisticsState();
}

class _CareerStatisticsState extends State<CareerStatistics> {
  Map<String, dynamic>? feed, catalog;
  String category = 'programming';
  SharedPreferences? personal;
  @override
  void initState() {
    super.initState();
    category = widget.initialCategory;
    load();
  }

  Future<void> load() async {
    final prefs = await SharedPreferences.getInstance();
    personal = prefs;
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
    final imported = courses
        ? [
            ...feed!['courses'],
            ...catalog!['courses'],
          ].cast<Map<String, dynamic>>()
        : (feed!['offers'] as List)
              .cast<Map<String, dynamic>>()
              .where((r) => r['category'] == category)
              .toList();
    final byId = {for (final row in imported) '${row['id']}': row};
    if (category == 'vfx') {
      for (final job in widget.directJobs.where(
        (j) => j.status == 'active' && j.isDirectSource,
      )) {
        byId[job.id] = {...?byId[job.id], ...job.data, 'category': 'vfx'};
      }
    }
    final rows = byId.values.toList();
    final valid = courses
        ? rows
        : rows.where((r) => !expiredCareerOffer(r, DateTime.now())).toList();
    final selected = filterCareerItems(
      rows,
      category: category,
      query: personal?.getString('career.$category.query') ?? '',
      includeAdvanced:
          personal?.getBool('career.$category.advancedV3') ?? category == 'vfx',
      profileView: category == 'programming'
          ? personal?.getString('career.programming.profileView') ?? 'entry'
          : 'all',
      days: personal?.getInt('career.$category.days') ?? 0,
      scope: personal?.getString('career.$category.scope') ?? 'all',
      topic: courses
          ? personal?.getString('career.courses.topicV2') ?? 'programming'
          : 'all',
      goal: personal?.getString('career.courses.goal') ?? 'review',
      freeOnly: personal?.getBool('career.courses.freeOnly') ?? false,
      includeUnknownPrice:
          personal?.getBool('career.courses.unknownPrice') ?? false,
      modality: personal?.getString('career.courses.modality') ?? 'all',
    );
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
          if (!widget.sourcesOnly) ...[
            const SizedBox(height: 16),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Text(
                  category == 'vfx'
                      ? '${valid.length} vacantes únicas entre empresas y portales'
                      : '${rows.length} ${courses ? 'recursos recopilados' : 'vacantes recopiladas'} · ${selected.length} en tu vista',
                  style: TextStyle(
                    fontSize: 21,
                    fontWeight: FontWeight.w700,
                    color: Theme.of(context).colorScheme.primary,
                  ),
                ),
              ),
            ),
            Text(
              category == 'vfx'
                  ? 'Las copias con el mismo enlace original comparten una identidad. Una vacante puede tener varias procedencias.'
                  : 'El primer número es el catálogo; el segundo aplica tus filtros guardados. La procedencia no confirma que cumplas todos los requisitos.',
            ),
            if (courses) ...[
              Text(
                '${(feed!['courses'] as List).length} con consulta automática · ${(catalog!['courses'] as List).length} de selección fija',
              ),
              ...distribution(
                'Dónde los encontramos',
                rows.map((r) => r['source'] ?? r['provider']),
              ),
              ...distribution(
                'Quién los imparte / publica',
                rows.map((r) => r['provider'] ?? 'Por confirmar'),
              ),
              ...distribution(
                'Especialidad',
                rows.map((r) => courseTopics[r['topic']] ?? 'Sin clasificar'),
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
                  'Consulta el desglose por procedencia. Las plataformas de empresas VFX tienen su gráfica propia.',
                ),
              for (final ats in connected.entries)
                ListTile(
                  dense: true,
                  title: Text(ats.key),
                  trailing: Text('${ats.value} ofertas'),
                ),
              ...distribution(
                'Procedencia y ATS',
                valid.map((r) => r['source']),
              ),
              ...distribution('Experiencia', valid.map((r) => r['experience'])),
            ],
            if (category == 'vfx' && widget.onDirectGraph != null)
              TextButton.icon(
                onPressed: widget.onDirectGraph,
                icon: const Icon(Icons.donut_large),
                label: const Text('Gráfica de plataformas de empresas'),
              ),
          ],
          ExpansionTile(
            initiallyExpanded: widget.sourcesOnly,
            title: const Text('Fuentes consultadas'),
            children: [
              if (category == 'vfx')
                ExpansionTile(
                  title: Text(
                    '${widget.employers.where((c) => c['enabled'] != false).length} empresas configuradas',
                  ),
                  subtitle: const Text(
                    'No son todas las empresas de cada ATS. Su configuración no garantiza una consulta reciente correcta.',
                  ),
                  children: [
                    for (final company in widget.employers.where(
                      (c) => c['enabled'] != false,
                    ))
                      ListTile(
                        title: Text('${company['name']}'),
                        subtitle: Text('${company['type'] ?? 'Web propia'}'),
                      ),
                  ],
                ),
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
                        ? '${source['matched'] ?? source['examined'] ?? 0} ${source['matched'] != null ? 'anuncios importados antes de unificar' : 'fichas examinadas'} · ${readableDate(source['lastSuccessAt'] ?? source['checkedAt'] ?? feed!['updatedAt'])}'
                        : source['status'] == 'pending'
                        ? 'Integración pendiente · no es una fuente automática operativa'
                        : 'No se pudo renovar la consulta. Revisa la página original; no significa que no haya oportunidades.',
                  ),
                  leading: Icon(
                    source['status'] == 'ok'
                        ? Icons.check_circle_outline
                        : Icons.warning_amber,
                    color: source['status'] == 'ok'
                        ? confirmedColor
                        : reviewColor,
                  ),
                ),
            ],
          ),
          Text(
            'Última actualización parcial del catálogo: ${readableDate(feed!['lastPartialUpdate'] ?? feed!['updatedAt'])}. Cada ficha conserva su propia fecha.',
            style: const TextStyle(color: mutedColor, fontSize: 12),
          ),
        ],
      ),
    );
  }
}
