import 'dart:convert';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:url_launcher/url_launcher.dart';

import 'jobs.dart';
import 'company_map.dart';

String platformName(String type) =>
    const {
      'custom': 'Web propia',
      'greenhouse': 'Greenhouse',
      'teamtailor': 'Teamtailor',
      'workday': 'Workday',
      'workable': 'Workable',
      'lever': 'Lever',
      'smartrecruiters': 'SmartRecruiters',
      'ashby': 'Ashby',
      'personio': 'Personio',
      'recruitee': 'Recruitee',
      'massive-wp': 'WordPress',
      'room8': 'WordPress',
      'epic': 'Greenhouse',
      'ea': 'Portal EA',
      'bamboo': 'BambooHR',
      'pinpoint': 'Pinpoint',
      'infiniteplus': 'Web propia',
      'mercurysteam': 'Web propia',
      'mundfish': 'Web propia',
      'axiomvfx': 'Web propia',
    }[type] ??
    type;

List<MapEntry<String, int>> platformCounts(
  List<Job> jobs,
  List<dynamic> companies,
) {
  final counts = <String, int>{};
  final types = <String, String>{};
  for (final c in companies) {
    types[c['name']] = c['type'] ?? 'custom';
    if (c['enabled'] != false) counts[platformName(c['type'] ?? 'custom')] = 0;
  }
  for (final job in jobs) {
    if (job.status != 'active' || !job.isDirectSource) continue;
    final name = platformName(types[job.company] ?? job.str('ats'));
    counts[name] = (counts[name] ?? 0) + 1;
  }
  return counts.entries.toList()..sort((a, b) {
    final order = b.value.compareTo(a.value);
    return order == 0 ? a.key.compareTo(b.key) : order;
  });
}

const chartColors = [
  Color(0xffb39aff),
  Color(0xff56d5bd),
  Color(0xffffbb70),
  Color(0xff69b9ff),
  Color(0xfff391ba),
  Color(0xffd8dc73),
  Color(0xffadbacf),
];

class InsightsPage extends StatefulWidget {
  final List<Job> jobs;
  const InsightsPage({super.key, required this.jobs});
  @override
  State<InsightsPage> createState() => _InsightsState();
}

class _InsightsState extends State<InsightsPage> {
  Map<String, dynamic>? world, locations;
  List<dynamic> companies = [];
  String selected = '';
  bool loading = true;
  String? error;
  @override
  void initState() {
    super.initState();
    load();
  }

  Future<void> load() async {
    try {
      final geometry = jsonDecode(
        await rootBundle.loadString('assets/world-map.json'),
      ) as Map<String, dynamic>;
      final bundled = jsonDecode(
        await rootBundle.loadString('assets/company-locations.json'),
      ) as Map<String, dynamic>;
      final config = jsonDecode(
        await rootBundle.loadString('assets/companies.json'),
      ) as List<dynamic>;
      final prefs = await SharedPreferences.getInstance();
      Map<String, dynamic>? cache;
      try {
        cache = jsonDecode(
          prefs.getString('radar.cache') ?? 'null',
        ) as Map<String, dynamic>?;
      } catch (_) {}
      if (!mounted) return;
      setState(() {
        world = geometry;
        locations = cache?['locations'] ?? bundled;
        companies = cache?['companies'] ?? config;
      });
      final responses = await Future.wait(
        ['company-locations.json', 'companies.json'].map(
          (file) => http
              .get(Uri.parse('https://yagovfx.github.io/data/$file'))
              .timeout(const Duration(seconds: 20)),
        ),
      );
      if (responses.any((r) => r.statusCode != 200)) {
        throw Exception('Datos del radar aún no publicados');
      }
      final freshLocations = jsonDecode(utf8.decode(responses[0].bodyBytes));
      final freshCompanies = jsonDecode(utf8.decode(responses[1].bodyBytes));
      if (freshLocations is! Map<String, dynamic> ||
          freshLocations['companies'] is! List ||
          freshCompanies is! List) {
        throw const FormatException('Datos del radar no válidos');
      }
      await prefs.setString(
        'radar.cache',
        jsonEncode({'locations': freshLocations, 'companies': freshCompanies}),
      );
      if (mounted) {
        setState(() {
          locations = freshLocations;
          companies = freshCompanies;
          error = null;
        });
      }
    } catch (_) {
      if (mounted) {
        setState(
          () => error = 'Sin actualización del mapa. Mostrando la última copia disponible.',
        );
      }
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final rows = platformCounts(widget.jobs, companies),
        total = rows.fold<int>(0, (n, r) => n + r.value);
    final all = (locations?['companies'] as List<dynamic>? ?? [])
        .cast<Map<String, dynamic>>();
    final placed =
        all.where((c) => (c['locations'] as List).isNotEmpty).toList()
          ..sort((a, b) => (a['name'] as String).compareTo(b['name']));
    final missing = all.where((c) => (c['locations'] as List).isEmpty).toList();
    final visible = placed
        .where((c) => selected.isEmpty || c['name'] == selected)
        .toList();
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Text('Radar global', style: Theme.of(context).textTheme.headlineMedium),
        OutlinedButton.icon(
          onPressed: () => launchUrl(
            Uri.parse(
              'https://github.com/YagoVfx/yagovfx.github.io/actions/workflows/vfx-jobs-scanner.yml',
            ),
            mode: LaunchMode.externalApplication,
          ),
          icon: const Icon(Icons.open_in_new),
          label: const Text('Jobs VFX Scanner en GitHub'),
        ),
        if (loading) const LinearProgressIndicator(),
        if (error != null)
          Text(error!, style: const TextStyle(color: Colors.amber)),
        const SizedBox(height: 20),
        Text(
          'Ofertas por plataforma',
          style: Theme.of(context).textTheme.titleLarge,
        ),
        const Text(
          'Ofertas VFX activas de portales directos, incluidas coincidencias posibles. Sin filtros personales, cerradas ni agregadores.',
        ),
        Semantics(
          label: '$total ofertas activas por plataforma',
          child: SizedBox(
            height: 220,
            child: CustomPaint(
              painter: DonutPainter(rows),
              child: Center(
                child: Text(
                  '$total\nofertas activas',
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.headlineSmall,
                ),
              ),
            ),
          ),
        ),
        ...rows.asMap().entries.map(
          (entry) => ListTile(
            dense: true,
            leading: Icon(
              Icons.circle,
              color: chartColors[entry.key % chartColors.length],
              size: 14,
            ),
            title: Text(entry.value.key),
            trailing: Text(
              '${entry.value.value} · ${total == 0 ? 0 : (entry.value.value / total * 100).round()}%',
            ),
          ),
        ),
        if (rows.isNotEmpty)
          Text(
            'Más ofertas: ${rows.first.key} (${rows.first.value}). Menos: ${rows.where((r) => r.value == rows.last.value).map((r) => r.key).join(', ')}.',
          ),
        const SizedBox(height: 24),
        Text('Mapa de empresas', style: Theme.of(context).textTheme.titleLarge),
        const Text(
          'Ubicaciones publicadas, aproximadas al centro urbano. No son todas las sedes ni la ubicación de cada vacante. Pellizca para ampliar y arrastra para desplazarte.',
        ),
        const SizedBox(height: 12),
        DropdownButtonFormField<String>(
          key: ValueKey('company-picker-$selected'),
          initialValue: selected,
          isExpanded: true,
          decoration: const InputDecoration(labelText: 'Empresa'),
          items: [
            DropdownMenuItem(
              value: '',
              child: Text('Todas (${placed.length})'),
            ),
            ...placed.map(
              (c) => DropdownMenuItem(
                value: c['name'] as String,
                child: Text(c['name'] as String),
              ),
            ),
          ],
          onChanged: (v) => setState(() => selected = v ?? ''),
        ),
        const Padding(
          padding: EdgeInsets.symmetric(vertical: 12),
          child: Text(
            'Pulsa un grupo para ver sus empresas y selecciona un nombre para enfocarlo, sin etiquetas superpuestas.',
          ),
        ),
        if (world != null)
          ClipRRect(
            borderRadius: BorderRadius.circular(12),
            child: SizedBox(
              height: 340,
              child: CompanyWorldMap(
                polygons: world!['polygons'] as List,
                companies: visible,
                onSelected: (name) => setState(() => selected = name),
              ),
            ),
          ),
        Text(
          '${placed.length} empresas localizadas · ${missing.length} sin ubicación verificada',
        ),
        ExpansionTile(
          initiallyExpanded: selected.isNotEmpty,
          key: ValueKey('company-details-$selected'),
          title: const Text('Ubicaciones y fuentes'),
          children: visible
              .map(
                (c) => ListTile(
                  title: Text(c['name'] as String),
                  subtitle: Text(
                    '${(c['locations'] as List).map((p) => p['city']).join(', ')}${c['sharedSource'] == null ? '' : ' · portal compartido con ${c['sharedSource']}'}',
                  ),
                  trailing: const Icon(Icons.open_in_new),
                  onTap: () async {
                    final url = safeUrl(
                      (c['locations'] as List).first['evidence'],
                    );
                    if (url != null) {
                      await launchUrl(
                        Uri.parse(url),
                        mode: LaunchMode.externalApplication,
                      );
                    }
                  },
                ),
              )
              .toList(),
        ),
        ExpansionTile(
          title: Text('Sin ubicación verificada (${missing.length})'),
          children: missing
              .map((c) => ListTile(title: Text(c['name'] as String)))
              .toList(),
        ),
        const Text(
          'Cartografía: Natural Earth, dominio público. Ubicaciones: portales de empleo y páginas oficiales.',
        ),
      ],
    );
  }
}

class DonutPainter extends CustomPainter {
  final List<MapEntry<String, int>> rows;
  DonutPainter(this.rows);
  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2),
        radius = math.min(size.width, size.height) / 2 - 24;
    final paint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 20
      ..color = const Color(0xff293044);
    canvas.drawCircle(center, radius, paint);
    final total = rows.fold<int>(0, (n, r) => n + r.value);
    if (total == 0) return;
    var angle = -math.pi / 2;
    for (var i = 0; i < rows.length; i++) {
      final arc = rows[i].value / total * math.pi * 2;
      paint.color = chartColors[i % chartColors.length];
      canvas.drawArc(
        Rect.fromCircle(center: center, radius: radius),
        angle,
        arc,
        false,
        paint,
      );
      angle += arc;
    }
  }

  @override
  bool shouldRepaint(covariant DonutPainter oldDelegate) => true;
}
