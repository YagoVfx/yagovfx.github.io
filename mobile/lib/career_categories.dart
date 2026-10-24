import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:url_launcher/url_launcher.dart';

import 'applications.dart';
import 'jobs.dart';

const careerCategories = {
  'vfx': 'VFX',
  'programming': 'Programación',
  'electricity': 'Electricidad',
  'courses': 'Cursos',
};

bool expiredCareerOffer(Map<String, dynamic> item, DateTime now) {
  final end = DateTime.tryParse('${item['closingDate'] ?? ''}');
  return end != null &&
      DateTime.utc(
        now.year,
        now.month,
        now.day,
      ).isAfter(DateTime.utc(end.year, end.month, end.day));
}

List<Map<String, dynamic>> filterCareerItems(
  List<Map<String, dynamic>> items, {
  required String category,
  String query = '',
  bool includeAdvanced = false,
  String scope = 'all',
  String modality = 'all',
  String topic = 'all',
  bool freeOnly = false,
  double budget = 800,
  bool savedOnly = false,
  Set<String> saved = const {},
  DateTime? now,
}) {
  final today = now ?? DateTime.now();
  final words = fold(query).trim().split(RegExp(r'\s+'));
  final out = items.where((item) {
    if (savedOnly && !saved.contains(item['id'])) return false;
    if (!words.every(
      fold(
        '${item['title']} ${item['company'] ?? item['provider']} ${item['location'] ?? ''} ${item['description'] ?? ''}',
      ).contains,
    )) {
      return false;
    }
    if (category == 'courses') {
      if (item['modality'] == 'onsite' && item['inVigo'] != true) return false;
      if (!savedOnly && !includeAdvanced && item['level'] == 'advanced') {
        return false;
      }
      if (modality != 'all' && item['modality'] != modality) return false;
      if (topic != 'all' && item['topic'] != topic) return false;
      final price = item['price'];
      if (price is! num || price > budget || freeOnly && price != 0) {
        return false;
      }
    } else {
      if (item['category'] != category) return false;
      if (!savedOnly && expiredCareerOffer(item, today)) return false;
      if (!savedOnly &&
          !includeAdvanced &&
          item['experience'] == 'experienced') {
        return false;
      }
      if (category == 'electricity' && item['inVigo'] != true) return false;
      if (category == 'programming' &&
          item['inVigo'] != true &&
          item['workplace'] != 'remote') {
        return false;
      }
      if (scope == 'remote' && item['workplace'] != 'remote') return false;
      if (scope == 'vigo' && item['inVigo'] != true) return false;
    }
    return true;
  }).toList();
  out.sort((a, b) {
    if (category == 'courses') {
      final price = (a['price'] as num).compareTo(b['price'] as num);
      if (price != 0) return price;
      final basic = (a['level'] == 'beginner' ? 0 : 1).compareTo(
        b['level'] == 'beginner' ? 0 : 1,
      );
      if (basic != 0) return basic;
    } else {
      final beginner = (a['experience'] == 'junior' ? 0 : 1).compareTo(
        b['experience'] == 'junior' ? 0 : 1,
      );
      if (beginner != 0) return beginner;
    }
    return '${a['title']}'.compareTo('${b['title']}');
  });
  return out;
}

class CareerFeedRepository {
  final http.Client client;
  CareerFeedRepository({http.Client? client})
    : client = client ?? http.Client();
  Map<String, dynamic> decode(String text) {
    final data = jsonDecode(text);
    if (data is! Map<String, dynamic> ||
        data['schemaVersion'] != 1 ||
        data['offers'] is! List ||
        data['courses'] is! List) {
      throw const FormatException('Formato de oportunidades no válido');
    }
    return data;
  }

  Future<Map<String, dynamic>> refresh(SharedPreferences prefs) async {
    final response = await client
        .get(Uri.parse('https://yagovfx.github.io/data/mobile-careers.json'))
        .timeout(const Duration(seconds: 25));
    if (response.statusCode != 200) {
      throw Exception(
        'El feed móvil todavía no está disponible (${response.statusCode}).',
      );
    }
    final raw = utf8.decode(response.bodyBytes), data = decode(raw);
    await prefs.setString('career.feed', raw);
    return data;
  }

  void close() => client.close();
}

class CareerCategoryPage extends StatefulWidget {
  final String category;
  final ApplicationsStore applications;
  final bool savedOnly;
  final int refreshVersion;
  final VoidCallback openApplications;
  const CareerCategoryPage({
    super.key,
    required this.category,
    required this.applications,
    required this.openApplications,
    this.savedOnly = false,
    this.refreshVersion = 0,
  });
  @override
  State<CareerCategoryPage> createState() => _CareerCategoryState();
}

class _CareerCategoryState extends State<CareerCategoryPage> {
  final repository = CareerFeedRepository(), search = TextEditingController();
  SharedPreferences? prefs;
  Map<String, dynamic>? feed, catalog;
  Map<String, Map<String, dynamic>> savedMeta = {};
  Set<String> saved = {};
  Map<String, String> progress = {};
  bool loading = true, includeAdvanced = false, freeOnly = false;
  String scope = 'all', modality = 'all', topic = 'all';
  String? error;
  @override
  void initState() {
    super.initState();
    load();
  }

  @override
  void didUpdateWidget(covariant CareerCategoryPage old) {
    super.didUpdateWidget(old);
    if (old.refreshVersion != widget.refreshVersion) refresh();
  }

  @override
  void dispose() {
    repository.close();
    search.dispose();
    super.dispose();
  }

  Future<void> load() async {
    final p = await SharedPreferences.getInstance();
    final bundled = repository.decode(
      await rootBundle.loadString('assets/mobile-careers.json'),
    );
    final resources = jsonDecode(
      await rootBundle.loadString('assets/career-resources.json'),
    ) as Map<String, dynamic>;
    Map<String, dynamic> data = bundled;
    try {
      final cache = p.getString('career.feed');
      if (cache != null) data = repository.decode(cache);
    } catch (_) {}
    if (!mounted) return;
    prefs = p;
    feed = data;
    catalog = resources;
    saved = (p.getStringList('career.saved') ?? []).toSet();
    try {
      savedMeta =
          (jsonDecode(p.getString('career.savedMeta') ?? '{}')
                  as Map<String, dynamic>)
              .map((k, v) => MapEntry(k, Map<String, dynamic>.from(v)));
    } catch (_) {}
    try {
      progress = (jsonDecode(
        p.getString('career.progress') ?? '{}',
      ) as Map<String, dynamic>).map((k, v) => MapEntry(k, '$v'));
    } catch (_) {}
    search.text = p.getString('career.${widget.category}.query') ?? '';
    includeAdvanced = p.getBool('career.${widget.category}.advanced') ?? false;
    freeOnly = p.getBool('career.courses.freeOnly') ?? false;
    setState(() => loading = false);
    await refresh();
  }

  Future<void> refresh() async {
    if (prefs == null) return;
    setState(() => loading = true);
    try {
      final data = await repository.refresh(prefs!);
      if (mounted) {
        setState(() {
          feed = data;
          error = null;
        });
      }
    } catch (_) {
      if (mounted) {
        setState(
          () => error = 'No se pudo actualizar. Mostrando la última copia disponible; revisa las fechas y el estado de las fuentes.',
        );
      }
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  void toggleSaved(Map<String, dynamic> item) {
    setState(() {
      if (saved.remove(item['id'])) {
        savedMeta.remove(item['id']);
      } else {
        saved.add(item['id']);
        savedMeta[item['id']] = Map.from(item);
      }
    });
    prefs?.setStringList('career.saved', saved.toList());
    prefs?.setString('career.savedMeta', jsonEncode(savedMeta));
  }

  Future<void> open(Object? raw) async {
    final url = safeUrl(raw);
    if (url == null) return;
    try {
      await launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication);
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('No se pudo abrir el enlace.')),
        );
      }
    }
  }

  List<Map<String, dynamic>> items() {
    final entries = <String, Map<String, dynamic>>{};
    if (widget.savedOnly) entries.addAll(savedMeta);
    final list = widget.category == 'courses'
        ? [...?feed?['courses'] as List?, ...?catalog?['courses'] as List?]
        : feed?['offers'] as List? ?? [];
    for (final raw in list) {
      final item = Map<String, dynamic>.from(raw);
      entries[item['id']] = item;
    }
    return filterCareerItems(
      entries.values.toList(),
      category: widget.category,
      query: search.text,
      includeAdvanced: includeAdvanced,
      scope: scope,
      modality: modality,
      topic: topic,
      freeOnly: freeOnly,
      savedOnly: widget.savedOnly,
      saved: saved,
    );
  }

  Widget picker(
    String title,
    String value,
    Map<String, String> options,
    ValueChanged<String> update,
  ) => SizedBox(
    width: 190,
    child: DropdownButtonFormField<String>(
      initialValue: value,
      isExpanded: true,
      decoration: InputDecoration(labelText: title),
      items: options.entries
          .map(
            (e) => DropdownMenuItem(
              value: e.key,
              child: Text(
                e.value,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ),
          )
          .toList(),
      onChanged: (v) {
        if (v != null) setState(() => update(v));
      },
    ),
  );
  Widget courseCard(Map<String, dynamic> item) => Card(
    child: Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(item['title'], style: Theme.of(context).textTheme.titleLarge),
          Text(
            '${item['provider']} · ${item['modality'] == 'online' ? 'Online' : 'Presencial'} · ${item['price'] == 0 ? 'Gratuito' : '${item['price']} €'}',
          ),
          if (item['kind'] == 'guide')
            const Text('Guía práctica; no equivale a un título o certificado'),
          Text(
            item['availability'] ??
                'Consulta acceso e inscripción en el proveedor',
          ),
          if (item['level'] == 'advanced')
            const Text('Nivel avanzado: revisar conocimientos previos'),
          if (item['retainedAfterFailure'] == true)
            const Text(
              'No se ha podido renovar la comprobación de esta ficha',
              style: TextStyle(color: Colors.amber),
            ),
          if (item['description'] != null)
            ExpansionTile(
              title: const Text('Contenido y encaje'),
              children: [
                Padding(
                  padding: const EdgeInsets.all(12),
                  child: Text(item['description']),
                ),
              ],
            ),
          Wrap(
            spacing: 8,
            children: [
              FilledButton(
                onPressed: () => open(item['url']),
                child: const Text('Ver formación'),
              ),
              OutlinedButton.icon(
                onPressed: () => toggleSaved(item),
                icon: Icon(
                  saved.contains(item['id'])
                      ? Icons.bookmark
                      : Icons.bookmark_border,
                ),
                label: Text(
                  saved.contains(item['id']) ? 'Guardado' : 'Guardar',
                ),
              ),
            ],
          ),
          if (saved.contains(item['id']))
            DropdownButtonFormField<String>(
              key: ValueKey('${item['id']}-${progress[item['id']]}'),
              initialValue: progress[item['id']] ?? 'interested',
              decoration: const InputDecoration(
                labelText: 'Mi progreso (en este móvil)',
              ),
              items: const [
                DropdownMenuItem(
                  value: 'interested',
                  child: Text('Me interesa'),
                ),
                DropdownMenuItem(value: 'started', child: Text('En curso')),
                DropdownMenuItem(value: 'finished', child: Text('Completado')),
              ],
              onChanged: (v) {
                if (v != null) {
                  setState(() => progress[item['id']] = v);
                  prefs?.setString('career.progress', jsonEncode(progress));
                }
              },
            ),
        ],
      ),
    ),
  );
  Widget offerCard(Map<String, dynamic> item) {
    final application = widget.applications.records[item['id']];
    final expired = expiredCareerOffer(item, DateTime.now());
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(item['title'], style: Theme.of(context).textTheme.titleLarge),
            Text(item['location']),
            Text(
              '${item['source']} · ${item['sourceKind'] == 'employer' ? 'Portal de empresa' : 'Servicio público de empleo'}',
            ),
            Text(
              item['experience'] == 'junior'
                  ? 'Menciona perfil junior o formación inicial'
                  : item['experience'] == 'experienced'
                  ? 'Exige experiencia: revisar encaje'
                  : 'Experiencia requerida no confirmada',
            ),
            if (item['workplace'] == 'remote')
              const Text(
                'Menciona teletrabajo: confirma condiciones y base en España',
              ),
            if (item['workplace'] == 'hybrid')
              const Text('Modalidad híbrida: revisar presencialidad'),
            if (item['postedDate'] != null)
              Text('Publicada: ${item['postedDate']}'),
            if (item['closingDate'] != null)
              Text('Fin de difusión: ${item['closingDate']}'),
            if (expired || item['retainedAfterFailure'] == true)
              Text(
                expired
                    ? 'Oferta fuera de plazo'
                    : 'Datos conservados tras un fallo; revisar vigencia',
                style: const TextStyle(color: Colors.amber),
              ),
            ...((item['requirements'] as List?) ?? []).map((r) => Text('• $r')),
            ExpansionTile(
              title: const Text('Descripción de la fuente'),
              children: [
                Padding(
                  padding: const EdgeInsets.all(12),
                  child: Text(
                    item['description'] ??
                        'Consulta los requisitos en el enlace oficial.',
                  ),
                ),
              ],
            ),
            Wrap(
              spacing: 8,
              children: [
                FilledButton(
                  onPressed: () => open(item['url']),
                  child: const Text('Ver oferta'),
                ),
                OutlinedButton.icon(
                  onPressed: () => toggleSaved(item),
                  icon: Icon(
                    saved.contains(item['id'])
                        ? Icons.bookmark
                        : Icons.bookmark_border,
                  ),
                  label: Text(
                    saved.contains(item['id']) ? 'Guardada' : 'Guardar',
                  ),
                ),
              ],
            ),
            TextButton.icon(
              icon: const Icon(Icons.send_outlined),
              label: Text(
                application == null
                    ? 'He enviado mi candidatura'
                    : 'Candidatura: ${applicationLabels[application['status']]}',
              ),
              onPressed: widget.applications.busy || expired
                  ? null
                  : () async {
                      if (!widget.applications.signedIn ||
                          application != null) {
                        widget.openApplications();
                        return;
                      }
                      final ok = await widget.applications.save(
                        Job(item),
                        'applied',
                      );
                      if (!mounted) return;
                      if (ok) {
                        widget.openApplications();
                      } else {
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(
                            content: Text(
                              widget.applications.error ??
                                  'No se pudo registrar el envío.',
                            ),
                          ),
                        );
                      }
                    },
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (feed == null || catalog == null) {
      return const Center(child: CircularProgressIndicator());
    }
    final list = items(), isCourse = widget.category == 'courses';
    final resources = (catalog!['sources'] as List)
        .where((s) => (s['categories'] as List).contains(widget.category))
        .toList();
    return RefreshIndicator(
      onRefresh: refresh,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(
            '${careerCategories[widget.category]}${widget.savedOnly ? ' · Guardadas' : ''}',
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          Text(
            isCourse
                ? 'Prioridad a formación gratuita o subvencionada. Tope de 800 € para cursos con precio confirmado; revisa programa, fechas y requisitos antes de inscribirte.'
                : widget.category == 'electricity'
                ? 'Ofertas con ubicación en Vigo. Revisa si la empresa exige desplazamientos diarios o viajes; la búsqueda no los considera aceptados automáticamente.'
                : 'Puestos de programación, QA y software en Vigo o con teletrabajo anunciado. Prioridad junior o reciclaje; no se da por acreditada experiencia profesional.',
          ),
          if (loading) const LinearProgressIndicator(),
          if (error != null)
            Text(error!, style: const TextStyle(color: Colors.amber)),
          Text('Último escaneo: ${feed!['updatedAt'] ?? 'Sin fecha'}'),
          const SizedBox(height: 12),
          TextField(
            controller: search,
            onChanged: (value) {
              setState(() {});
              prefs?.setString('career.${widget.category}.query', value);
            },
            decoration: const InputDecoration(
              labelText: 'Buscar por título, tecnología o contenido',
              prefixIcon: Icon(Icons.search),
            ),
          ),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: Text(
              isCourse
                  ? 'Incluir nivel avanzado'
                  : 'Incluir puestos con experiencia alta',
            ),
            value: includeAdvanced,
            onChanged: (v) {
              setState(() => includeAdvanced = v);
              prefs?.setBool('career.${widget.category}.advanced', v);
            },
          ),
          if (isCourse)
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text('Solo gratuitos o subvencionados'),
              value: freeOnly,
              onChanged: (v) {
                setState(() => freeOnly = v);
                prefs?.setBool('career.courses.freeOnly', v);
              },
            ),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: [
              if (widget.category == 'programming')
                picker('Ubicación', scope, {
                  'all': 'Vigo o remoto',
                  'vigo': 'Solo Vigo',
                  'remote': 'Solo remoto',
                }, (v) => scope = v),
              if (isCourse)
                picker('Modalidad', modality, {
                  'all': 'Online y presenciales',
                  'online': 'Online',
                  'onsite': 'Presenciales',
                }, (v) => modality = v),
              if (isCourse)
                picker('Tema', topic, {
                  'all': 'Todos',
                  'programming': 'Programación',
                  'electricity': 'Electricidad / automatización',
                  'vfx': 'VFX / Unreal',
                }, (v) => topic = v),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            '${list.length} ${isCourse ? 'formaciones' : 'ofertas'}${widget.savedOnly ? ' guardadas' : ''}',
          ),
          if (list.isEmpty)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 16),
              child: Text(
                widget.savedOnly
                    ? 'No tienes elementos guardados en esta categoría.'
                    : 'No hay resultados que cumplan estos filtros en la última consulta. Revisa también las fuentes oficiales de abajo; una búsqueda sin resultados no significa que no haya oportunidades.',
              ),
            ),
          ...list.map(isCourse ? courseCard : offerCard),
          if (!widget.savedOnly)
            ExpansionTile(
              initiallyExpanded: list.isEmpty,
              title: const Text('Más fuentes y buscadores oficiales'),
              subtitle: const Text(
                'Son enlaces de búsqueda, no ofertas ni plazas confirmadas',
              ),
              children: resources
                  .map(
                    (r) => ListTile(
                      title: Text(r['name']),
                      subtitle: Text(r['note']),
                      trailing: const Icon(Icons.open_in_new),
                      onTap: () => open(r['url']),
                    ),
                  )
                  .toList(),
            ),
          ExpansionTile(
            title: const Text('Estado y alcance de las fuentes'),
            children: [
              const Padding(
                padding: EdgeInsets.all(12),
                child: Text(
                  'Ofertas directas de empresas mediante Workable y de los servicios públicos mediante SNE. Los cursos automáticos proceden de eFundae y las guías seleccionadas de sus proveedores. Emprego Galicia se ofrece como enlace manual porque su formulario no permite completar la consulta automática. No es una búsqueda de todo Internet. Las guardadas y el progreso de cursos se guardan en este móvil; las candidaturas sí se sincronizan con tu cuenta.',
                ),
              ),
              ...((feed!['sources'] as List?) ?? []).map(
                (s) => ListTile(
                  title: Text(s['name']),
                  subtitle: Text(
                    s['status'] == 'ok'
                        ? 'Consulta correcta · ${s['examined'] ?? 0} fichas examinadas'
                        : s['reason'] ?? 'Fuente no disponible',
                  ),
                  leading: Icon(
                    s['status'] == 'ok'
                        ? Icons.check_circle_outline
                        : Icons.warning_amber,
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
