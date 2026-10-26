import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:url_launcher/url_launcher.dart';

import 'jobs.dart';
import 'presentation.dart';

List<Map<String, dynamic>> filterExams(
  List<Map<String, dynamic>> rows, {
  String area = 'local',
  String query = '',
  Set<String>? saved,
  DateTime? now,
}) {
  final today = (now ?? DateTime.now()).toIso8601String().substring(0, 10);
  return rows.where((r) {
    if (r['closingDate'] is String &&
        (r['closingDate'] as String).compareTo(today) < 0) {
      return false;
    }
    if (saved != null && !saved.contains(r['id'])) return false;
    if (area == 'galicia-national' &&
        !['galicia', 'national'].contains(r['area'])) {
      return false;
    }
    if (area == 'local' && !['vigo', 'coruna'].contains(r['municipality'])) {
      return false;
    }
    if (area == 'galicia' && r['area'] != 'galicia') return false;
    return fold('${r['title']} ${r['organization']} ${r['qualification']}')
        .contains(fold(query.trim()));
  }).toList()..sort(
    (a, b) => '${a['closingDate'] ?? '9999'}'.compareTo(
      '${b['closingDate'] ?? '9999'}',
    ),
  );
}

class PublicExamsPage extends StatefulWidget {
  final bool savedOnly;
  final int refreshVersion;
  const PublicExamsPage({
    super.key,
    this.savedOnly = false,
    this.refreshVersion = 0,
  });
  @override
  State<PublicExamsPage> createState() => _PublicExamsState();
}

class _PublicExamsState extends State<PublicExamsPage> {
  Map<String, dynamic>? feed;
  SharedPreferences? prefs;
  Set<String> saved = {};
  String area = 'local', query = '';
  String? error;
  @override
  void initState() {
    super.initState();
    load();
  }

  @override
  void didUpdateWidget(covariant PublicExamsPage old) {
    super.didUpdateWidget(old);
    if (old.refreshVersion != widget.refreshVersion) refresh();
  }

  Map<String, dynamic> decode(String raw) {
    final data = jsonDecode(raw);
    if (data is! Map<String, dynamic> ||
        data['schemaVersion'] != 1 ||
        data['calls'] is! List) {
      throw const FormatException('Formato no compatible');
    }
    return data;
  }

  Future<void> load() async {
    prefs = await SharedPreferences.getInstance();
    var data = decode(await rootBundle.loadString('assets/public-exams.json'));
    try {
      data = decode(prefs!.getString('exams.cache') ?? '');
    } catch (_) {}
    if (!mounted) return;
    setState(() {
      feed = data;
      saved = (prefs!.getStringList('exams.saved') ?? []).toSet();
      area = prefs!.getString('exams.area') ?? 'local';
    });
    await refresh();
  }

  Future<void> refresh() async {
    final client = http.Client();
    try {
      final response = await client
          .get(Uri.parse('https://yagovfx.github.io/data/public-exams.json'))
          .timeout(const Duration(seconds: 20));
      if (response.statusCode != 200) throw Exception('No actualizado');
      final data = decode(utf8.decode(response.bodyBytes));
      await prefs?.setString('exams.cache', jsonEncode(data));
      if (mounted) {
        setState(() {
          feed = data;
          error = null;
        });
      }
    } catch (_) {
      if (mounted) {
        setState(
          () => error = 'Sin actualización. Mostrando la copia guardada; confirma los plazos en las bases.',
        );
      }
    } finally {
      client.close();
    }
  }

  Future<void> open(Object? value) async {
    final url = safeUrl(value);
    if (url != null) {
      await launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication);
    }
  }

  void toggle(Map<String, dynamic> row) {
    setState(() {
      if (!saved.remove(row['id'])) saved.add(row['id']);
    });
    prefs?.setStringList('exams.saved', saved.toList());
  }

  void detail(Map<String, dynamic> row) => Navigator.of(context).push(
    MaterialPageRoute<void>(
      builder: (context) => Scaffold(
        appBar: AppBar(title: const Text('Convocatoria')),
        body: ListView(
          padding: const EdgeInsets.all(20),
          children: [
            Text(
              row['title'],
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            Text(
              row['organization'],
              style: TextStyle(color: Theme.of(context).colorScheme.primary),
            ),
            statusTag(
              row['fit'] == 'dam'
                  ? 'La titulación publicada incluye DAM'
                  : 'Revisar título exigido',
              confirmed: row['fit'] == 'dam',
            ),
            const SizedBox(height: 12),
            Text(
              'Plazas convocadas: ${row['places'] ?? 'No especificadas'} · Libres: ${row['freePlaces'] ?? 'Por confirmar'}',
            ),
            Text('Fin de solicitudes: ${readableDate(row['closingDate'])}'),
            Text(row['deadlineEvidence']),
            const Text(
              'Fecha de examen: consultar los avisos del organismo; no se presupone una fecha.',
            ),
            const SizedBox(height: 16),
            const Text(
              'Titulación publicada',
              style: TextStyle(fontWeight: FontWeight.bold),
            ),
            Text(row['qualification']),
            Text('Ámbito: ${row['location']}'),
            if (row['area'] == 'national')
              const Text(
                'Destino concreto por confirmar; no se garantiza una plaza en Galicia.',
              ),
            Text(row['access']),
            const SizedBox(height: 16),
            const Text(
              'Revisa también idioma, nacionalidad, tasas, requisitos específicos y fechas de examen en las bases. Guardar aquí solo indica interés; no presenta una solicitud.',
            ),
            FilledButton.icon(
              onPressed: () => open(row['url']),
              icon: const Icon(Icons.open_in_new),
              label: const Text('Ver convocatoria oficial'),
            ),
            TextButton(
              onPressed: () => open(row['searchUrl']),
              child: Text('Buscar referencia ${row['reference']} en el PAG'),
            ),
            Text('Fuente: ${row['source']}'),
            Text(
              'Comprobada: ${readableDate(row['checkedAt'])}',
              style: const TextStyle(color: mutedColor),
            ),
          ],
        ),
      ),
    ),
  );
  @override
  Widget build(BuildContext context) {
    if (feed == null) return const Center(child: CircularProgressIndicator());
    final rows = filterExams(
      (feed!['calls'] as List).cast<Map<String, dynamic>>(),
      area: area,
      query: query,
      saved: widget.savedOnly ? saved : null,
    );
    return RefreshIndicator(
      onRefresh: refresh,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(
            'Oposiciones${widget.savedOnly ? ' guardadas' : ''}',
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          const Text(
            'Acceso libre relacionado con tus estudios. Confirma titulación y plazos en las bases.',
          ),
          if (error != null)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 8),
              child: Text(error!, style: const TextStyle(color: reviewColor)),
            ),
          const SizedBox(height: 12),
          DropdownButtonFormField<String>(
            initialValue: area,
            isExpanded: true,
            decoration: const InputDecoration(labelText: 'Ámbito'),
            items: [
              for (final e in {
                'galicia-national': 'Galicia y convocatorias estatales',
                'galicia': 'Solo Galicia',
                'local': 'Vigo y A Coruña (municipios)',
                'all': 'Toda España',
              }.entries)
                DropdownMenuItem(value: e.key, child: Text(e.value)),
            ],
            onChanged: (v) {
              setState(() => area = v!);
              prefs?.setString('exams.area', v!);
            },
          ),
          const SizedBox(height: 12),
          TextField(
            decoration: const InputDecoration(
              labelText: 'Buscar convocatoria u organismo',
              prefixIcon: Icon(Icons.search),
            ),
            onChanged: (v) => setState(() => query = v),
          ),
          const SizedBox(height: 12),
          Text(
            '${rows.length} convocatorias en tu vista',
            style: const TextStyle(fontWeight: FontWeight.bold),
          ),
          const Text(
            'Fechas orientativas del PAG: confirma siempre las bases. Cobertura parcial de las convocatorias municipales.',
            style: TextStyle(color: mutedColor, fontSize: 12),
          ),
          for (final row in rows)
            Card(
              child: ListTile(
                contentPadding: const EdgeInsets.all(16),
                title: Text(
                  row['title'],
                  style: const TextStyle(fontWeight: FontWeight.w700),
                ),
                subtitle: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      row['organization'],
                      style: TextStyle(
                        color: Theme.of(context).colorScheme.primary,
                      ),
                    ),
                    Text(
                      '${row['freePlaces'] ?? row['places'] ?? '?'} plazas · Fin: ${readableDate(row['closingDate'])}',
                    ),
                    statusTag(
                      row['retainedAfterFailure'] == true
                          ? 'Vigencia sin confirmar · consulta fallida'
                          : row['fit'] == 'dam'
                          ? 'Incluye DAM en la titulación'
                          : 'Revisar titulación',
                      confirmed: row['fit'] == 'dam',
                    ),
                  ],
                ),
                trailing: IconButton(
                  tooltip: 'Guardar interés en este móvil',
                  onPressed: () => toggle(row),
                  icon: Icon(
                    saved.contains(row['id'])
                        ? Icons.bookmark
                        : Icons.bookmark_border,
                  ),
                ),
                onTap: () => detail(row),
              ),
            ),
          if (rows.isEmpty)
            const Padding(
              padding: EdgeInsets.all(16),
              child: Text(
                'No hay convocatorias recogidas con estos filtros. La cobertura es parcial; consulta también las fuentes oficiales.',
              ),
            ),
          ExpansionTile(
            title: const Text('Fuentes y alcance'),
            children: [
              Text(feed!['note']),
              for (final source in feed!['sources'])
                ListTile(
                  title: Text(source['name']),
                  subtitle: Text(
                    source['status'] == 'ok'
                        ? 'Consulta correcta · ${source['examined']} resultados examinados'
                        : 'No se pudo actualizar esta consulta',
                  ),
                ),
              TextButton(
                onPressed: () => open(
                  'https://www.coruna.gal/administracion-publica/gl/recursos-humanos/convocatorias-de-seleccion-de-persoal',
                ),
                child: const Text('Concello da Coruña'),
              ),
              TextButton(
                onPressed: () => open(
                  'https://sede.vigo.org/expedientes/oposicions/ofertas_tipo.jsp?id=2&lang=es&tipo=1',
                ),
                child: const Text('Sede municipal de Vigo'),
              ),
              TextButton(
                onPressed: () => open(
                  'https://www.xunta.gal/es/funcion-publica/procesos-selectivos/consulta',
                ),
                child: const Text('Procesos selectivos Xunta'),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
