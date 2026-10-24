import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:vfx_jobs_tracker/applications.dart';
import 'package:vfx_jobs_tracker/jobs.dart';
import 'package:vfx_jobs_tracker/geography.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUp(() => FlutterSecureStorage.setMockInitialValues({}));
  test('UE tiene los mismos límites que en la web y conserva el filtro', () {
    for (final code
        in 'AT BE BG HR CY CZ DK EE FI FR DE GR HU IE IT LV LT LU MT NL PL PT RO SK SI ES SE'
            .split(' ')) {
      expect(isEUJob({'countryCode': code}), true);
    }
    for (final location in [
      'Remote, Europe',
      'London, UK',
      'Zurich, Switzerland',
      'Oslo, Norway',
      'Paris, Texas, USA',
    ]) {
      expect(isEUJob({'location': location}), false, reason: location);
    }
    expect(isEUJob({'location': 'Madrid'}), true);
    expect(isEUJob({'remoteScope': 'Spain'}), true);
    expect(JobFilters.fromJson({'eu': true}).toJson()['eu'], true);
  });
  test('Guarda candidaturas con el mismo contrato Firestore que la web y recibe cambios remotos', () async {
    final records = <String, Map<String, dynamic>>{};
    final store = ApplicationsStore(
      client: MockClient((request) async {
        if (request.url.host == 'identitytoolkit.googleapis.com') {
          return http.Response(
            jsonEncode({
              'localId': adminUid,
              'email': 'admin@example.com',
              'idToken': 'fixture',
              'refreshToken': 'refresh-fixture',
              'expiresIn': '3600',
            }),
            200,
          );
        }
        expect(request.headers['Authorization'], 'Bearer fixture');
        expect(request.url.path, contains('/users/$adminUid/applications'));
        if (request.method == 'PATCH') {
          final id = request.url.pathSegments.last;
          final patch =
              jsonDecode(request.body)['fields'] as Map<String, dynamic>;
          if (records.containsKey(id)) {
            records[id]!['fields'].addAll(patch);
          } else {
            records[id] = {'fields': patch};
          }
          return http.Response(jsonEncode(records[id]), 200);
        }
        return http.Response(
          jsonEncode({'documents': records.values.toList()}),
          200,
        );
      }),
    );
    addTearDown(store.dispose);
    await store.signIn('admin@example.com', 'do-not-store-this-password');
    final job = Job({
      'id': 'gh-1',
      'company': 'Studio',
      'title': 'VFX Artist',
      'url': 'https://example.com/job',
      'location': 'Madrid',
    });
    expect(await store.save(job, 'applied'), true);
    expect(records['gh-1']!['fields']['status']['stringValue'], 'applied');
    records['gh-1']!['fields']['status'] = {'stringValue': 'interview'};
    await store.refresh();
    expect(store.records['gh-1']!['status'], 'interview');
    await store.save(job, 'interview', notes: 'Private note');
    expect(records['gh-1']!['fields']['notes']['stringValue'], 'Private note');
    final session = await store.storage.read(key: 'applications.session');
    expect(session, isNot(contains('do-not-store-this-password')));
    await store.signOut();
    expect(store.records, isEmpty);
    expect(await store.storage.read(key: 'applications.session'), isNull);
  });
  test('Un permiso denegado no marca la oferta como solicitada', () async {
    final store = ApplicationsStore(
      client: MockClient((r) async {
        if (r.url.host == 'identitytoolkit.googleapis.com') {
          return http.Response(
            jsonEncode({
              'localId': adminUid,
              'email': 'admin@example.com',
              'idToken': 'fixture',
              'refreshToken': 'fixture',
              'expiresIn': '3600',
            }),
            200,
          );
        }
        if (r.method == 'PATCH') return http.Response('{}', 403);
        return http.Response('{}', 200);
      }),
    );
    addTearDown(store.dispose);
    await store.signIn('admin@example.com', 'password');
    expect(
      await store.save(
        Job({
          'id': 'gh-1',
          'company': 'Studio',
          'title': 'VFX Artist',
          'url': 'https://example.com',
        }),
        'applied',
      ),
      false,
    );
    expect(store.records, isEmpty);
    expect(store.error, contains('reglas privadas'));
  });
  test(
    'Rechaza otra cuenta antes de guardar una sesión o leer candidaturas',
    () async {
      final store = ApplicationsStore(
        client: MockClient((r) async {
          expect(r.url.host, 'identitytoolkit.googleapis.com');
          return http.Response(jsonEncode({'localId': 'other-account'}), 200);
        }),
      );
      addTearDown(store.dispose);
      await store.signIn('other@example.com', 'password');
      expect(store.signedIn, false);
      expect(await store.storage.read(key: 'applications.session'), isNull);
    },
  );
}
