import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;
import 'package:url_launcher/url_launcher.dart';

import 'jobs.dart';
import 'presentation.dart';

const applicationLabels = {
  'applied': 'Enviada',
  'interview': 'Entrevista',
  'offer': 'Oferta recibida',
  'rejected': 'Rechazada',
  'withdrawn': 'Retirada',
};
const adminUid = 'ylQ3m3XoCHTd0cwP7UQet7cSRpt1';
const firebaseWebKey = 'AIzaSyCQWuMtoQrIMuP99jemn5BpjX18LEChaWY';

Map<String, dynamic> applicationFields(Map<String, dynamic> record) => {
  for (final e in record.entries) e.key: {'stringValue': '${e.value}'},
};
Map<String, dynamic> decodeApplication(Map<String, dynamic> doc) => {
  for (final e in (doc['fields'] as Map<String, dynamic>).entries)
    e.key: e.value['stringValue'] ?? '',
};

class ApplicationsStore extends ChangeNotifier with WidgetsBindingObserver {
  final http.Client client;
  final FlutterSecureStorage storage;
  ApplicationsStore({http.Client? client, FlutterSecureStorage? storage})
    : client = client ?? http.Client(),
      storage = storage ?? const FlutterSecureStorage();
  Map<String, Map<String, dynamic>> records = {};
  String? uid, email, error, lastSync;
  String _token = '', _refresh = '';
  DateTime _expires = DateTime.fromMillisecondsSinceEpoch(0);
  bool busy = false, _reading = false, _disposed = false;
  int _epoch = 0, _version = 0;
  Timer? _timer;
  bool get signedIn => uid == adminUid;
  Map<String, dynamic>? find(Job job) {
    for (final id in [job.id, ...?job.data['sourceIds'] as List?]) {
      if (records['$id'] != null) return records['$id'];
    }
    final urls = [
      job.data['url'],
      job.data['originalUrl'],
    ].whereType<String>().map(vacancyUrl).where((s) => s.isNotEmpty).toSet();
    for (final record in records.values) {
      if (urls.contains(vacancyUrl('${record['url']}'))) return record;
    }
    return null;
  }

  void emit() {
    if (!_disposed) notifyListeners();
  }

  void startPolling() {
    WidgetsBinding.instance.removeObserver(this);
    WidgetsBinding.instance.addObserver(this);
    _timer?.cancel();
    _timer = Timer.periodic(const Duration(seconds: 15), (_) {
      final state = WidgetsBinding.instance.lifecycleState;
      if (signedIn &&
          !busy &&
          (state == null || state == AppLifecycleState.resumed)) {
        refresh();
      }
    });
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed && signedIn && !busy) refresh();
  }

  Future<void> restore() async {
    try {
      final raw = await storage.read(key: 'applications.session');
      if (raw == null || _disposed) return;
      final session = jsonDecode(raw);
      if (session['uid'] != adminUid) return;
      uid = session['uid'];
      email = session['email'];
      _refresh = session['refresh'];
      final cache = await storage.read(key: 'applications.cache.$adminUid');
      if (cache != null) {
        final data = jsonDecode(cache) as Map<String, dynamic>;
        records = data.map((k, v) => MapEntry(k, Map<String, dynamic>.from(v)));
      }
      emit();
      startPolling();
      await refresh();
    } catch (_) {
      error = 'No se pudo recuperar la sesión. Inicia sesión de nuevo.';
      emit();
    }
  }

  Future<void> signIn(String address, String password) async {
    if (busy) return;
    busy = true;
    error = null;
    emit();
    try {
      final response = await client
          .post(
            Uri.parse(
              'https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=$firebaseWebKey',
            ),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({
              'email': address.trim(),
              'password': password,
              'returnSecureToken': true,
            }),
          )
          .timeout(const Duration(seconds: 25));
      if (response.statusCode != 200) {
        throw Exception(
          'Email o contraseña incorrectos, o acceso no disponible.',
        );
      }
      final data = jsonDecode(response.body);
      if (data['localId'] != adminUid) {
        throw Exception(
          'Esta cuenta no está autorizada para las candidaturas.',
        );
      }
      _epoch++;
      uid = adminUid;
      email = data['email'];
      _token = data['idToken'];
      _refresh = data['refreshToken'];
      _expires = DateTime.now().add(
        Duration(seconds: int.parse(data['expiresIn'])),
      );
      await storage.write(
        key: 'applications.session',
        value: jsonEncode({'uid': uid, 'email': email, 'refresh': _refresh}),
      );
      startPolling();
      await refresh();
    } catch (e) {
      error = e.toString().replaceFirst('Exception: ', '');
    } finally {
      busy = false;
      emit();
    }
  }

  Future<void> signOut() async {
    _epoch++;
    _version++;
    _timer?.cancel();
    uid = null;
    email = null;
    _token = '';
    _refresh = '';
    records = {};
    error = null;
    lastSync = null;
    busy = false;
    emit();
    await storage.delete(key: 'applications.session');
  }

  Future<String> token() async {
    final epoch = _epoch;
    if (!signedIn) throw Exception('Inicia sesión');
    if (_token.isNotEmpty &&
        DateTime.now().isBefore(
          _expires.subtract(const Duration(minutes: 1)),
        )) {
      return _token;
    }
    final response = await client
        .post(
          Uri.parse(
            'https://securetoken.googleapis.com/v1/token?key=$firebaseWebKey',
          ),
          body: {'grant_type': 'refresh_token', 'refresh_token': _refresh},
        )
        .timeout(const Duration(seconds: 25));
    if (response.statusCode != 200) {
      throw Exception('La sesión ha caducado. Vuelve a iniciar sesión.');
    }
    if (epoch != _epoch || !signedIn) throw Exception('Sesión cerrada');
    final data = jsonDecode(utf8.decode(response.bodyBytes));
    _token = data['id_token'];
    _refresh = data['refresh_token'];
    _expires = DateTime.now().add(
      Duration(seconds: int.parse(data['expires_in'])),
    );
    await storage.write(
      key: 'applications.session',
      value: jsonEncode({'uid': uid, 'email': email, 'refresh': _refresh}),
    );
    return _token;
  }

  Future<Map<String, dynamic>> request(
    String path, {
    Map<String, dynamic>? body,
    String? method,
  }) async {
    final jwt = await token();
    final url = Uri.parse(
      'https://firestore.googleapis.com/v1/projects/portfolio-44b20/databases/(default)/documents/users/$adminUid/applications$path',
    );
    final headers = {
      'Authorization': 'Bearer $jwt',
      'Content-Type': 'application/json',
    };
    final response =
        await (method == 'DELETE'
                ? client.delete(url, headers: headers)
                : body == null
                ? client.get(url, headers: headers)
                : client.patch(url, headers: headers, body: jsonEncode(body)))
            .timeout(const Duration(seconds: 25));
    if (response.statusCode == 403) {
      throw Exception(
        'Falta publicar las reglas privadas de candidaturas en Firebase (firestore.rules).',
      );
    }
    if (response.statusCode == 401) {
      throw Exception('La sesión ha caducado. Vuelve a iniciar sesión.');
    }
    if (response.statusCode != 200 && response.statusCode != 204) {
      throw Exception(
        'No se pudo sincronizar. El cambio no se ha confirmado; comprueba la conexión y reintenta.',
      );
    }
    return response.bodyBytes.isEmpty
        ? {}
        : jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
  }

  Future<void> refresh() async {
    if (!signedIn || _reading || _disposed) return;
    _reading = true;
    final epoch = _epoch, version = _version;
    try {
      final next = <String, Map<String, dynamic>>{};
      String page = '';
      do {
        final data = await request(
          '?pageSize=300${page.isEmpty ? '' : '&pageToken=${Uri.encodeQueryComponent(page)}'}',
        );
        for (final doc in data['documents'] ?? []) {
          final record = decodeApplication(Map<String, dynamic>.from(doc));
          next[record['id']] = record;
        }
        page = data['nextPageToken'] ?? '';
      } while (page.isNotEmpty);
      if (_epoch != epoch || _version != version) return;
      records = next;
      error = null;
      lastSync = DateTime.now().toUtc().toIso8601String();
      await storage.write(
        key: 'applications.cache.$adminUid',
        value: jsonEncode(records),
      );
    } catch (e) {
      if (_epoch == epoch) error = e.toString().replaceFirst('Exception: ', '');
    } finally {
      _reading = false;
      emit();
    }
  }

  Future<bool> save(
    Job job,
    String status, {
    String? notes,
    String? appliedAt,
  }) async {
    if (!signedIn || busy || !applicationLabels.containsKey(status)) {
      return false;
    }
    final epoch = _epoch;
    _version++;
    busy = true;
    error = null;
    emit();
    try {
      final old = find(job), now = DateTime.now().toUtc().toIso8601String();
      final recordId = old?['id'] ?? job.id;
      final record = old == null
          ? <String, dynamic>{
              'id': recordId,
              'company': job.company,
              'title': job.title,
              'url': safeUrl(job.data['url']) ?? '',
              'location': job.str('location', ''),
              'status': status,
              'appliedAt': appliedAt ?? now,
              'updatedAt': now,
              'notes': notes ?? '',
            }
          : Map<String, dynamic>.from(old);
      record['status'] = status;
      record['updatedAt'] = now;
      if (notes != null) record['notes'] = notes;
      if (appliedAt != null) record['appliedAt'] = appliedAt;
      final patch = old == null
          ? record
          : <String, dynamic>{
              'status': status,
              'updatedAt': now,
              'notes': ?notes,
              'appliedAt': ?appliedAt,
            };
      final mask = old == null
          ? ''
          : '?${patch.keys.map((k) => 'updateMask.fieldPaths=$k').join('&')}';
      await request(
        '/${Uri.encodeComponent(recordId)}$mask',
        body: {'fields': applicationFields(patch)},
      );
      if (epoch == _epoch) {
        records[recordId] = record;
        lastSync = now;
        await storage.write(
          key: 'applications.cache.$adminUid',
          value: jsonEncode(records),
        );
      }
      return true;
    } catch (e) {
      if (epoch == _epoch) error = e.toString().replaceFirst('Exception: ', '');
      return false;
    } finally {
      if (epoch == _epoch) busy = false;
      emit();
    }
  }

  Future<bool> remove(String id) async {
    if (!signedIn || busy || !records.containsKey(id)) return false;
    final epoch = _epoch;
    _version++;
    busy = true;
    error = null;
    emit();
    try {
      await request('/${Uri.encodeComponent(id)}', method: 'DELETE');
      if (epoch == _epoch) {
        records.remove(id);
        lastSync = DateTime.now().toUtc().toIso8601String();
        await storage.write(
          key: 'applications.cache.$adminUid',
          value: jsonEncode(records),
        );
      }
      return true;
    } catch (e) {
      if (epoch == _epoch) error = e.toString().replaceFirst('Exception: ', '');
      return false;
    } finally {
      if (epoch == _epoch) {
        busy = false;
        emit();
      }
    }
  }

  @override
  void dispose() {
    _disposed = true;
    WidgetsBinding.instance.removeObserver(this);
    _timer?.cancel();
    client.close();
    super.dispose();
  }
}

class ApplicationsPage extends StatefulWidget {
  final ApplicationsStore store;
  const ApplicationsPage({super.key, required this.store});
  @override
  State<ApplicationsPage> createState() => _ApplicationsPageState();
}

class _ApplicationsPageState extends State<ApplicationsPage> {
  final email = TextEditingController(), password = TextEditingController();
  String view = 'all';
  int days = 0;
  Future<void> deleteRecord(Map<String, dynamic> record) async {
    final accepted = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('¿Eliminar candidatura?'),
        content: Text(
          'Se eliminará ${record['title']} de tus candidaturas en el móvil y la web. Esto no retira el CV enviado a la empresa. Para conservar el historial, cambia el estado a Retirada o Rechazada.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancelar'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Eliminar'),
          ),
        ],
      ),
    );
    if (accepted == true) await widget.store.remove(record['id']);
  }

  @override
  void initState() {
    super.initState();
    widget.store.refresh();
  }

  @override
  void dispose() {
    email.dispose();
    password.dispose();
    super.dispose();
  }

  Future<void> editNotes(Map<String, dynamic> record) async {
    final controller = TextEditingController(text: record['notes']);
    final value = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Notas privadas'),
        content: TextField(
          controller: controller,
          maxLength: 2000,
          maxLines: 5,
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancelar'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, controller.text),
            child: const Text('Guardar'),
          ),
        ],
      ),
    );
    if (value != null) {
      await widget.store.save(Job(record), record['status'], notes: value);
    }
    controller.dispose();
  }

  Future<void> manual() async {
    final company = TextEditingController(),
        title = TextEditingController(),
        url = TextEditingController();
    DateTime date = DateTime.now();
    final key = GlobalKey<FormState>();
    final result = await showDialog<bool>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, set) => AlertDialog(
          title: const Text('Añadir candidatura enviada'),
          content: SingleChildScrollView(
            child: Form(
              key: key,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  TextFormField(
                    controller: company,
                    maxLength: 200,
                    decoration: const InputDecoration(labelText: 'Empresa'),
                    validator: (v) => v == null || v.trim().isEmpty
                        ? 'Indica la empresa'
                        : null,
                  ),
                  TextFormField(
                    controller: title,
                    maxLength: 300,
                    decoration: const InputDecoration(labelText: 'Puesto'),
                    validator: (v) => v == null || v.trim().isEmpty
                        ? 'Indica el puesto'
                        : null,
                  ),
                  TextFormField(
                    controller: url,
                    decoration: const InputDecoration(
                      labelText: 'Enlace (opcional)',
                    ),
                    validator: (v) =>
                        v != null && v.isNotEmpty && safeUrl(v) == null
                        ? 'Usa un enlace http o https'
                        : null,
                  ),
                  TextButton(
                    onPressed: () async {
                      final picked = await showDatePicker(
                        context: context,
                        initialDate: date,
                        firstDate: DateTime(2000),
                        lastDate: DateTime.now(),
                      );
                      if (picked != null) set(() => date = picked);
                    },
                    child: Text(
                      'Fecha: ${date.toIso8601String().substring(0, 10)}',
                    ),
                  ),
                ],
              ),
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('Cancelar'),
            ),
            FilledButton(
              onPressed: () {
                if (key.currentState!.validate()) Navigator.pop(context, true);
              },
              child: const Text('Guardar'),
            ),
          ],
        ),
      ),
    );
    if (result == true) {
      await widget.store.save(
        Job({
          'id': 'manual-${DateTime.now().microsecondsSinceEpoch}',
          'company': company.text.trim(),
          'title': title.text.trim(),
          'url': url.text.trim(),
          'location': '',
        }),
        'applied',
        appliedAt: DateTime.utc(
          date.year,
          date.month,
          date.day,
          12,
        ).toIso8601String(),
      );
    }
    company.dispose();
    title.dispose();
    url.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final store = widget.store;
    return ListenableBuilder(
      listenable: store,
      builder: (context, _) {
        if (!store.signedIn) {
          return ListView(
            padding: const EdgeInsets.all(24),
            children: [
              Text(
                'Mis candidaturas',
                style: Theme.of(context).textTheme.headlineSmall,
              ),
              const Text(
                'Inicia sesión con la misma cuenta que usas en la web. Las candidaturas son privadas y se sincronizan entre dispositivos.',
              ),
              TextField(
                controller: email,
                keyboardType: TextInputType.emailAddress,
                autofillHints: const [AutofillHints.username],
                decoration: const InputDecoration(labelText: 'Email'),
              ),
              TextField(
                controller: password,
                obscureText: true,
                autofillHints: const [AutofillHints.password],
                decoration: const InputDecoration(labelText: 'Contraseña'),
              ),
              if (store.error != null)
                Text(store.error!, style: const TextStyle(color: Colors.amber)),
              FilledButton(
                onPressed: store.busy
                    ? null
                    : () async {
                        await store.signIn(email.text, password.text);
                        password.clear();
                      },
                child: Text(store.busy ? 'Conectando…' : 'Iniciar sesión'),
              ),
            ],
          );
        }
        final records =
            store.records.values.where((r) {
              final closed = ['rejected', 'withdrawn'].contains(r['status']);
              if (view == 'active' && closed || view == 'closed' && !closed) {
                return false;
              }
              return days == 0 || withinDays(r['appliedAt'], days);
            }).toList()..sort(
              (a, b) => (b['appliedAt'] as String).compareTo(
                a['appliedAt'] as String,
              ),
            );
        return RefreshIndicator(
          onRefresh: store.refresh,
          child: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              Text(
                'Mis candidaturas (${records.length})',
                style: Theme.of(context).textTheme.headlineSmall,
              ),
              Text('Cuenta: ${store.email ?? ''}'),
              const Text(
                'Sincronización automática cada 15 segundos. Desliza para actualizar.',
              ),
              if (store.busy) const LinearProgressIndicator(),
              if (store.error != null)
                Text(store.error!, style: const TextStyle(color: Colors.amber)),
              if (store.lastSync != null)
                Text('Última sincronización: ${readableDate(store.lastSync)}'),
              Wrap(
                spacing: 8,
                children: [
                  OutlinedButton.icon(
                    onPressed: store.busy ? null : manual,
                    icon: const Icon(Icons.add),
                    label: const Text('Añadir anterior'),
                  ),
                  TextButton(
                    onPressed: store.signOut,
                    child: const Text('Cerrar sesión'),
                  ),
                ],
              ),
              Wrap(
                spacing: 8,
                children: [
                  for (final e in {
                    'all': 'Todas',
                    'active': 'En seguimiento',
                    'closed': 'Cerradas',
                  }.entries)
                    ChoiceChip(
                      label: Text(e.value),
                      selected: view == e.key,
                      onSelected: (_) => setState(() => view = e.key),
                    ),
                ],
              ),
              DropdownButtonFormField<int>(
                initialValue: days,
                decoration: const InputDecoration(labelText: 'Fecha de envío'),
                items: const [
                  DropdownMenuItem(value: 0, child: Text('Cualquier fecha')),
                  DropdownMenuItem(value: 7, child: Text('Última semana')),
                  DropdownMenuItem(value: 30, child: Text('Último mes')),
                ],
                onChanged: (v) => setState(() => days = v ?? 0),
              ),
              if (records.isEmpty)
                const Text(
                  'Marca «He enviado mi candidatura» en una oferta o añade una candidatura anterior.',
                ),
              ...records.map(
                (r) => Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          r['title'],
                          style: Theme.of(context).textTheme.titleLarge,
                        ),
                        Text(r['company']),
                        Text(
                          'Enviada: ${(r['appliedAt'] as String).substring(0, 10)}',
                        ),
                        if (!withinDays(r['appliedAt'], 30) &&
                            r['status'] == 'applied')
                          const Text(
                            'Más de 30 días sin cambiar de estado: puedes revisar, cerrar o eliminar esta candidatura.',
                          ),
                        DropdownButtonFormField<String>(
                          key: ValueKey('${r['id']}-${r['status']}'),
                          initialValue: r['status'],
                          decoration: const InputDecoration(
                            labelText: 'Estado',
                          ),
                          items: applicationLabels.entries
                              .map(
                                (e) => DropdownMenuItem(
                                  value: e.key,
                                  child: Text(e.value),
                                ),
                              )
                              .toList(),
                          onChanged: store.busy
                              ? null
                              : (s) {
                                  if (s != null) store.save(Job(r), s);
                                },
                        ),
                        if ((r['notes'] as String).isNotEmpty) Text(r['notes']),
                        Wrap(
                          spacing: 8,
                          children: [
                            TextButton(
                              onPressed: store.busy ? null : () => editNotes(r),
                              child: const Text('Notas privadas'),
                            ),
                            TextButton.icon(
                              onPressed: store.busy
                                  ? null
                                  : () => deleteRecord(r),
                              icon: const Icon(Icons.delete_outline),
                              label: const Text('Eliminar'),
                            ),
                            if (safeUrl(r['url']) != null)
                              TextButton(
                                onPressed: () => launchUrl(
                                  Uri.parse(r['url']),
                                  mode: LaunchMode.externalApplication,
                                ),
                                child: const Text('Abrir oferta'),
                              ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}
