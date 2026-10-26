import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:url_launcher/url_launcher.dart';

import 'jobs.dart';
import 'insights.dart';
import 'applications.dart';
import 'career_categories.dart';
import 'presentation.dart';
import 'public_exams.dart';

void main() => runApp(const TrackerApp());

class TrackerApp extends StatelessWidget {
  const TrackerApp({super.key});
  @override
  Widget build(BuildContext context) => MaterialApp(
    debugShowCheckedModeBanner: false,
    title: 'Yago Job Radar',
    theme: ThemeData(
      brightness: Brightness.dark,
      colorSchemeSeed: const Color(0xFFAA90FF),
      scaffoldBackgroundColor: const Color(0xFF0E1017),
      cardTheme: CardThemeData(
        color: const Color(0xff191d29),
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: const BorderSide(color: Color(0xff30374a)),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: const Color(0xff191d29),
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(14)),
        contentPadding: const EdgeInsets.symmetric(
          horizontal: 16,
          vertical: 14,
        ),
      ),
      navigationBarTheme: const NavigationBarThemeData(
        backgroundColor: Color(0xff141824),
        height: 72,
        indicatorColor: Color(0xff393052),
      ),
      useMaterial3: true,
    ),
    home: const OffersPage(),
  );
}

class OffersPage extends StatefulWidget {
  const OffersPage({super.key});
  @override
  State<OffersPage> createState() => _OffersState();
}

class _OffersState extends State<OffersPage> {
  final applications = ApplicationsStore();
  SharedPreferences? prefs;
  List<Job> jobs = [];
  Set<String> saved = {}, discarded = {};
  JobFilters filters = JobFilters();
  final search = TextEditingController();
  int tab = 0;
  String category = 'vfx';
  final selectedCategoryKey = GlobalKey();
  void revealCategory() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final selected = selectedCategoryKey.currentContext;
      if (mounted && selected != null) {
        final scrollable = Scrollable.of(selected);
        final target = selected.findRenderObject();
        final viewport = scrollable.context.findRenderObject();
        if (target is RenderBox && viewport is RenderBox) {
          final x = target.localToGlobal(Offset.zero, ancestor: viewport).dx;
          final position = scrollable.position;
          position.jumpTo(
            (position.pixels +
                    x -
                    (position.viewportDimension - target.size.width) / 2)
                .clamp(position.minScrollExtent, position.maxScrollExtent),
          );
        }
      }
    });
  }

  Widget categoryTabs() => SingleChildScrollView(
    scrollDirection: Axis.horizontal,
    padding: const EdgeInsets.fromLTRB(16, 0, 16, 10),
    child: Row(
      children: [
        for (final entry in navigationCategories.entries)
          Padding(
            padding: const EdgeInsets.only(right: 8),
            child: ChoiceChip(
              key: category == entry.key ? selectedCategoryKey : null,
              avatar: Icon(
                categoryIcon(entry.key),
                size: 19,
                color: category == entry.key
                    ? categoryAccent(entry.key)
                    : mutedColor,
              ),
              label: Text(entry.value),
              selected: category == entry.key,
              showCheckmark: false,
              selectedColor: categoryAccent(entry.key).withValues(alpha: .16),
              side: BorderSide(
                color: category == entry.key
                    ? categoryAccent(entry.key).withValues(alpha: .65)
                    : const Color(0xff30374a),
              ),
              labelStyle: TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w600,
                color: category == entry.key
                    ? categoryAccent(entry.key)
                    : mutedColor,
              ),
              onSelected: (_) {
                setState(() => category = entry.key);
                revealCategory();
                prefs?.setString('career.category', entry.key);
              },
            ),
          ),
      ],
    ),
  );
  int careerRefresh = 0;
  bool loading = true;
  String? error, updated;
  @override
  void initState() {
    super.initState();
    applications.addListener(applicationsChanged);
    applications.restore();
    init();
  }

  void applicationsChanged() {
    if (mounted) setState(() {});
  }

  @override
  void dispose() {
    applications.removeListener(applicationsChanged);
    applications.dispose();
    search.dispose();
    super.dispose();
  }

  Future<void> init() async {
    final p = await SharedPreferences.getInstance();
    if (!mounted) return;
    prefs = p;
    final storedCategory = p.getString('career.category');
    if (navigationCategories.containsKey(storedCategory)) {
      category = storedCategory!;
      revealCategory();
    }
    saved = {...?p.getStringList('saved'), ...?p.getStringList('career.saved')};
    final links = JobsRepository(p).cached();
    for (final row in (links?['jobs'] as List? ?? [])) {
      if ((row['sourceIds'] as List? ?? []).any(saved.contains)) {
        saved.add(row['id']);
      }
    }
    discarded = (p.getStringList('discarded') ?? []).toSet();
    try {
      filters = JobFilters.fromJson(jsonDecode(p.getString('filters') ?? '{}'));
    } catch (_) {
      filters = JobFilters();
    }
    search.text = filters.query;
    final cache = JobsRepository(p).cached();
    if (cache != null) {
      accept(cache);
      setState(() => loading = false);
    }
    await refresh();
  }

  void accept(Map<String, dynamic> d) {
    jobs = (d['jobs'] as List)
        .whereType<Map<String, dynamic>>()
        .map(Job.new)
        .where((job) => job.isDirectSource)
        .toList();
    updated = d['lastUpdated']?.toString();
    for (final job in jobs) {
      if ((job.data['sourceIds'] as List? ?? []).any(saved.contains)) {
        saved.add(job.id);
      }
    }
  }

  Future<void> refresh() async {
    if (prefs == null) return;
    setState(() => loading = true);
    try {
      final d = await JobsRepository(prefs!).refresh();
      if (!mounted) return;
      setState(() {
        accept(d);
        error = null;
      });
    } catch (e) {
      if (mounted) {
        setState(
          () => error =
              'No se pudo actualizar. ${jobs.isEmpty ? 'Comprueba tu conexión y reintenta.' : 'Mostrando la última copia guardada.'}',
        );
      }
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  void change(VoidCallback action) {
    setState(action);
    prefs?.setStringList('saved', saved.toList());
    prefs?.setStringList('career.saved', saved.toList());
    prefs?.setStringList('discarded', discarded.toList());
    prefs?.setString('filters', jsonEncode(filters.toJson()));
  }

  void toggleSaved(Job j) => change(() {
    if (saved.remove(j.id)) {
      for (final alias in (j.data['sourceIds'] as List? ?? [])) {
        saved.remove(alias);
      }
    } else {
      saved.add(j.id);
    }
    if (prefs?.getBool('bookmark.noticeSeen') != true) {
      prefs?.setBool('bookmark.noticeSeen', true);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'Guardadas: en este móvil. Solicitudes: sincronizadas con tu cuenta.',
          ),
        ),
      );
    }
  });
  Future<void> open(Object? raw) async {
    final url = safeUrl(raw);
    if (url == null) return;
    try {
      if (await launchUrl(
        Uri.parse(url),
        mode: LaunchMode.externalApplication,
      )) {
        return;
      }
    } catch (_) {}
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('No se pudo abrir el enlace.')),
      );
    }
  }

  String label(String s) =>
      const {
        'remote': 'Remoto',
        'hybrid': 'Híbrido',
        'onsite': 'Presencial',
        'unknown': 'Sin confirmar',
        'confirmed': 'Confirmada',
        'possible': 'Posible',
        'restricted': 'Restringida',
        'contradiction': 'Contradicción: revisar',
        'employee': 'Empleo asalariado',
        'freelance': 'Freelance / B2B',
        'temporary': 'Temporal',
        'compatible': 'Compatible',
        'review': 'Para revisar',
        'incompatible': 'Incompatible',
        'ats': 'ATS oficial',
        'official-site': 'Web oficial',
        'aggregator': 'Agregador',
        'signal': 'Señal sin vacante',
      }[s] ??
      s;
  Widget pill(String s) => Chip(
    label: Text(s, style: const TextStyle(fontSize: 12)),
    visualDensity: VisualDensity.compact,
  );
  void detail(Job j) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      showDragHandle: true,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, update) => DraggableScrollableSheet(
          expand: false,
          initialChildSize: .85,
          minChildSize: .4,
          maxChildSize: .95,
          builder: (ctx, scroll) => ListView(
            controller: scroll,
            padding: const EdgeInsets.fromLTRB(24, 8, 24, 32),
            children: [
              Text(j.company, style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 8),
              Text(j.title, style: Theme.of(context).textTheme.headlineSmall),
              Text(j.str('location', 'Ubicación no indicada')),
              Wrap(
                spacing: 6,
                children: [
                  pill(label(j.str('workplaceType'))),
                  pill('España: ${label(j.eligibility)}'),
                  pill(label(j.str('contractType'))),
                  pill(j.verified ? 'Verificada' : 'Sin verificar'),
                ],
              ),
              const SizedBox(height: 12),
              Text(
                j.compatibility == 'compatible'
                    ? 'Cumple los filtros de búsqueda; revisa experiencia y requisitos'
                    : 'Condiciones por revisar',
              ),
              Text(
                j.str(
                  'spainReason',
                  'La fuente no confirma la elegibilidad en España.',
                ),
              ),
              const SizedBox(height: 16),
              Text(
                'Por qué aparece aquí · ${j.score} puntos',
                style: Theme.of(context).textTheme.titleMedium,
              ),
              ...j.reasons.map(
                (s) => Padding(
                  padding: const EdgeInsets.symmetric(vertical: 3),
                  child: Text('• $s'),
                ),
              ),
              if (j.str('contractEvidence', '').isNotEmpty)
                Text('Evidencia del contrato: ${j.str('contractEvidence')}'),
              const SizedBox(height: 16),
              TextButton.icon(
                onPressed: () => showProvenance(context, j.data, open),
                icon: const Icon(Icons.info_outline),
                label: const Text('De dónde sale esta oferta'),
              ),
              Text(
                'Publicación oficial: ${j.str('postedDate', 'No disponible')}',
              ),
              Text('Última detección: ${j.str('lastSeen', 'No disponible')}'),
              if (!j.direct)
                const Padding(
                  padding: EdgeInsets.symmetric(vertical: 12),
                  child: Text(
                    'El enlace puede llevar al portal de empleo, no a una vacante concreta.',
                  ),
                ),
              FilledButton.icon(
                onPressed: safeUrl(j.data['url']) == null
                    ? null
                    : () => open(j.data['url']),
                icon: const Icon(Icons.open_in_new),
                label: const Text('Abrir oferta'),
              ),
              FilledButton.tonalIcon(
                icon: const Icon(Icons.send),
                label: Text(
                  applications.find(j) != null
                      ? 'Candidatura: ${applicationLabels[applications.find(j)!['status']]}'
                      : 'He enviado mi candidatura',
                ),
                onPressed: applications.busy
                    ? null
                    : () async {
                        if (!applications.signedIn ||
                            applications.find(j) != null) {
                          Navigator.pop(ctx);
                          setState(() => tab = 4);
                          return;
                        }
                        final ok = await applications.save(j, 'applied');
                        if (!mounted || !ctx.mounted) return;
                        if (ok) {
                          Navigator.pop(ctx);
                          setState(() => tab = 4);
                        } else {
                          ScaffoldMessenger.of(context).showSnackBar(
                            SnackBar(
                              content: Text(
                                applications.error ?? 'No se pudo guardar.',
                              ),
                            ),
                          );
                        }
                      },
              ),
              if (safeUrl(j.data['companyCareersUrl']) != null)
                TextButton(
                  onPressed: () => open(j.data['companyCareersUrl']),
                  child: const Text('Portal de la empresa'),
                ),
              OutlinedButton.icon(
                onPressed: () {
                  toggleSaved(j);
                  update(() {});
                },
                icon: Icon(
                  saved.contains(j.id) ? Icons.bookmark : Icons.bookmark_border,
                ),
                label: Text(
                  saved.contains(j.id)
                      ? 'Quitar de guardadas'
                      : 'Guardar oferta',
                ),
              ),
              TextButton(
                onPressed: () {
                  change(() => discarded.add(j.id));
                  Navigator.pop(ctx);
                },
                child: const Text('Descartar oferta'),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget select(
    String title,
    String value,
    Map<String, String> options,
    ValueChanged<String> onChanged,
  ) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 8),
    child: DropdownButtonFormField<String>(
      initialValue: value,
      decoration: InputDecoration(
        labelText: title,
        border: const OutlineInputBorder(),
      ),
      items: options.entries
          .map((e) => DropdownMenuItem(value: e.key, child: Text(e.value)))
          .toList(),
      onChanged: (v) {
        if (v != null) onChanged(v);
      },
    ),
  );
  void advanced() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      showDragHandle: true,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, update) => SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text('Filtros', style: Theme.of(context).textTheme.headlineSmall),
              select(
                'Antigüedad',
                '${filters.days}',
                {
                  '0': 'Cualquier fecha',
                  '1': 'Últimas 24 horas',
                  '7': 'Última semana',
                  '30': 'Último mes',
                },
                (v) {
                  change(() => filters.days = int.parse(v));
                  update(() {});
                },
              ),
              select(
                'Modalidad',
                filters.workplace,
                {
                  'all': 'Todas',
                  'remote': 'Remoto',
                  'hybrid': 'Híbrido',
                  'onsite': 'Presencial',
                  'unknown': 'Sin confirmar',
                },
                (v) {
                  change(() => filters.workplace = v);
                  update(() {});
                },
              ),
              select(
                'Compatibilidad España',
                filters.eligibility,
                {
                  'all': 'Todas',
                  'confirmed': 'Confirmada',
                  'possible': 'Posible',
                  'unknown': 'Sin confirmar / contradicción',
                  'restricted': 'Restringida',
                },
                (v) {
                  change(() => filters.eligibility = v);
                  update(() {});
                },
              ),
              select(
                'Contrato',
                filters.contract,
                {
                  'all': 'Todos',
                  'employee': 'Empleo asalariado',
                  'freelance': 'Freelance / B2B',
                  'temporary': 'Temporal',
                  'unknown': 'Desconocido',
                },
                (v) {
                  change(() => filters.contract = v);
                  update(() {});
                },
              ),
              select(
                'Orden',
                filters.sort,
                {
                  'relevance': 'Más relevantes',
                  'recent': 'Más recientes',
                  'company': 'Empresa A–Z',
                },
                (v) {
                  change(() => filters.sort = v);
                  update(() {});
                },
              ),
              SwitchListTile(
                contentPadding: EdgeInsets.zero,
                title: const Text('Incluir sin verificar'),
                value: filters.unverified,
                onChanged: (v) {
                  change(() => filters.unverified = v);
                  update(() {});
                },
              ),
              SwitchListTile(
                contentPadding: EdgeInsets.zero,
                title: const Text('Coincidencias posibles'),
                value: filters.possible,
                onChanged: (v) {
                  change(() => filters.possible = v);
                  update(() {});
                },
              ),
              FilledButton(
                onPressed: () => Navigator.pop(ctx),
                child: const Text('Ver resultados'),
              ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final visible = filterJobs(
      jobs,
      filters,
      saved: saved,
      discarded: discarded,
      savedOnly: tab == 1,
    );
    final time = DateTime.tryParse(updated ?? '');
    final old = time != null && DateTime.now().difference(time).inHours > 13;
    return Scaffold(
      appBar: AppBar(
        title: Text(
          tab == 2
              ? 'Ajustes'
              : tab == 3
              ? 'Radar'
              : 'Job Radar',
          style: const TextStyle(
            fontWeight: FontWeight.w800,
            letterSpacing: -.5,
          ),
        ),
        leading: tab == 2 || tab == 3
            ? IconButton(
                tooltip: 'Volver a explorar',
                icon: const Icon(Icons.arrow_back),
                onPressed: () => setState(() => tab = 0),
              )
            : null,
        bottom: tab <= 1
            ? PreferredSize(
                preferredSize: const Size.fromHeight(54),
                child: categoryTabs(),
              )
            : null,
        actions: [
          IconButton(
            tooltip: 'Radar y fuentes',
            icon: const Icon(Icons.radar),
            onPressed: () => setState(() => tab = 3),
          ),
          IconButton(
            tooltip: 'Ajustes',
            icon: const Icon(Icons.settings_outlined),
            onPressed: () => setState(() => tab = 2),
          ),
          IconButton(
            onPressed: () {
              setState(() => careerRefresh++);
              if (category == 'vfx' || tab == 2) refresh();
            },
            tooltip: 'Actualizar',
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: tab == 4
            ? 2
            : tab == 1
            ? 1
            : 0,
        onDestinationSelected: (v) => setState(() => tab = [0, 1, 4][v]),
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.work_outline),
            label: 'Explorar',
          ),
          NavigationDestination(
            icon: Icon(Icons.bookmark_border),
            label: 'Guardadas',
          ),
          NavigationDestination(
            icon: Icon(Icons.send_outlined),
            label: 'Solicitudes',
          ),
        ],
      ),
      body: tab <= 1 && category == 'public'
          ? SafeArea(
              child: PublicExamsPage(
                savedOnly: tab == 1,
                refreshVersion: careerRefresh,
              ),
            )
          : tab <= 1
          ? SafeArea(
              child: CareerCategoryPage(
                key: ValueKey(category),
                category: category,
                directJobs: jobs,
                applications: applications,
                savedOnly: tab == 1,
                refreshVersion: careerRefresh,
                openApplications: () => setState(() => tab = 4),
                onSavedChanged: () => setState(
                  () => saved = (prefs?.getStringList('saved') ?? []).toSet(),
                ),
              ),
            )
          : tab == 4
          ? SafeArea(child: ApplicationsPage(store: applications))
          : tab == 3
          ? SafeArea(
              child: category == 'public'
                  ? const Center(
                      child: Padding(
                        padding: EdgeInsets.all(24),
                        child: Text(
                          'Las plazas y fuentes de oposiciones se consultan en Ofertas. No se mezclan con las estadísticas de empleo.',
                        ),
                      ),
                    )
                  : InsightsPage(
                      jobs: jobs,
                      category: category == 'public' ? 'programming' : category,
                      refreshVersion: careerRefresh,
                    ),
            )
          : SafeArea(
              child: Column(
                children: [
                  if (loading) const LinearProgressIndicator(),
                  if (error != null)
                    Padding(
                      padding: const EdgeInsets.all(12),
                      child: Text(
                        error!,
                        style: const TextStyle(color: Colors.orangeAccent),
                      ),
                    ),
                  if (old)
                    const Padding(
                      padding: EdgeInsets.all(12),
                      child: Text(
                        'Datos de hace más de 13 horas. Revisa el scanner.',
                        style: TextStyle(color: Colors.amber),
                      ),
                    ),
                  if (tab == 2)
                    Expanded(
                      child: ListView(
                        padding: const EdgeInsets.all(24),
                        children: [
                          const RadarHeader(
                            title: 'Tu radar de empleo',
                            subtitle: 'Preferencias y datos de tu búsqueda',
                            category: 'settings',
                          ),
                          const SizedBox(height: 16),
                          const Text(
                            'Versión 0.14.0 · Tu radar personal',
                            style: TextStyle(color: mutedColor, fontSize: 12),
                          ),
                          const SizedBox(height: 16),
                          Text('Datos VFX: ${readableDate(updated)}'),
                          Text(
                            'Catálogo VFX cargado: ${jobs.length} anuncios antes de filtros',
                          ),
                          TextButton(
                            onPressed: refresh,
                            child: const Text('Actualizar VFX de empresas'),
                          ),
                          TextButton(
                            onPressed: () => change(() => discarded.clear()),
                            child: Text(
                              'Restaurar descartadas (${discarded.length})',
                            ),
                          ),
                          const Text(
                            'Las candidaturas se sincronizan con tu cuenta. Guardadas y descartadas siguen siendo locales.\n\nDesconocido no significa incompatible. Revisa las condiciones de cada oferta.',
                          ),
                        ],
                      ),
                    )
                  else ...[
                    Padding(
                      padding: const EdgeInsets.fromLTRB(16, 8, 16, 8),
                      child: TextField(
                        controller: search,
                        onChanged: (v) => change(() => filters.query = v),
                        decoration: InputDecoration(
                          hintText: 'Cargo, estudio, ubicación…',
                          prefixIcon: const Icon(Icons.search),
                          suffixIcon: IconButton(
                            onPressed: advanced,
                            tooltip: 'Filtros',
                            icon: const Icon(Icons.tune),
                          ),
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(18),
                          ),
                        ),
                      ),
                    ),
                    SingleChildScrollView(
                      scrollDirection: Axis.horizontal,
                      padding: const EdgeInsets.symmetric(horizontal: 16),
                      child: Row(
                        children: [
                          for (final e in {
                            'all': 'Todas',
                            'compatible': 'Cumplen filtros',
                            'review': 'Para revisar',
                          }.entries)
                            Padding(
                              padding: const EdgeInsets.only(right: 8),
                              child: ChoiceChip(
                                label: Text(e.value),
                                selected: filters.view == e.key,
                                onSelected: (_) =>
                                    change(() => filters.view = e.key),
                              ),
                            ),
                        ],
                      ),
                    ),
                    Padding(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 20,
                        vertical: 8,
                      ),
                      child: Wrap(
                        alignment: WrapAlignment.spaceBetween,
                        children: [
                          Text('${visible.length} ofertas'),
                          TextButton(
                            onPressed: () {
                              change(() => filters = JobFilters());
                              search.clear();
                            },
                            child: const Text('Limpiar filtros'),
                          ),
                        ],
                      ),
                    ),
                    Expanded(
                      child: RefreshIndicator(
                        onRefresh: refresh,
                        child: visible.isEmpty
                            ? ListView(
                                physics: const AlwaysScrollableScrollPhysics(),
                                padding: const EdgeInsets.all(32),
                                children: [
                                  const Icon(Icons.manage_search, size: 56),
                                  const SizedBox(height: 16),
                                  Text(
                                    loading
                                        ? 'Cargando ofertas…'
                                        : tab == 1
                                        ? 'No hay guardadas con estos filtros.'
                                        : 'No hay resultados. Limpia los filtros o incluye ofertas sin verificar.',
                                    textAlign: TextAlign.center,
                                  ),
                                  if (!loading)
                                    TextButton(
                                      onPressed: refresh,
                                      child: const Text(
                                        'Reintentar actualización',
                                      ),
                                    ),
                                ],
                              )
                            : ListView.builder(
                                physics: const AlwaysScrollableScrollPhysics(),
                                padding: const EdgeInsets.fromLTRB(
                                  16,
                                  0,
                                  16,
                                  16,
                                ),
                                itemCount: visible.length,
                                itemBuilder: (ctx, i) {
                                  final j = visible[i];
                                  return Card(
                                    margin: const EdgeInsets.only(bottom: 12),
                                    child: InkWell(
                                      borderRadius: BorderRadius.circular(12),
                                      onTap: () => detail(j),
                                      child: Padding(
                                        padding: const EdgeInsets.all(16),
                                        child: Column(
                                          crossAxisAlignment:
                                              CrossAxisAlignment.start,
                                          children: [
                                            Row(
                                              children: [
                                                Expanded(
                                                  child: Text(
                                                    j.company,
                                                    style: TextStyle(
                                                      color: Theme.of(context)
                                                          .colorScheme
                                                          .primary,
                                                    ),
                                                  ),
                                                ),
                                                IconButton(
                                                  onPressed: () =>
                                                      toggleSaved(j),
                                                  tooltip: 'Guardar',
                                                  icon: Icon(
                                                    saved.contains(j.id)
                                                        ? Icons.bookmark
                                                        : Icons.bookmark_border,
                                                  ),
                                                ),
                                              ],
                                            ),
                                            Text(
                                              j.title,
                                              style: Theme.of(context)
                                                  .textTheme
                                                  .titleLarge,
                                            ),
                                            const SizedBox(height: 8),
                                            Text(
                                              j.str(
                                                'location',
                                                'Ubicación no indicada',
                                              ),
                                            ),
                                            Wrap(
                                              spacing: 6,
                                              children: [
                                                pill(
                                                  label(j.str('workplaceType')),
                                                ),
                                                statusTag(
                                                  j.compatibility ==
                                                          'compatible'
                                                      ? 'Cumple filtros'
                                                      : 'Revisar condiciones',
                                                  confirmed:
                                                      j.compatibility ==
                                                      'compatible',
                                                ),
                                                pill(
                                                  j.verified
                                                      ? 'Procedencia oficial'
                                                      : 'Origen por revisar',
                                                ),
                                                if (applications.find(j) !=
                                                    null)
                                                  pill(
                                                    'Candidatura: ${applicationLabels[applications.find(j)!['status']]}',
                                                  ),
                                              ],
                                            ),
                                          ],
                                        ),
                                      ),
                                    ),
                                  );
                                },
                              ),
                      ),
                    ),
                  ],
                ],
              ),
            ),
    );
  }
}
