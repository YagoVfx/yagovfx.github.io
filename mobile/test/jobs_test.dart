import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:vfx_jobs_tracker/jobs.dart';

void main() {
  final raw =
      jsonDecode(File('test/jobs_fixture.json').readAsStringSync())['jobs']
          as List;
  final jobs = raw.map((r) => Job(Map<String, dynamic>.from(r))).toList();
  List<String> ids(
    JobFilters f, {
    Set<String> saved = const {},
    Set<String> discarded = const {},
    bool savedOnly = false,
  }) => (filterJobs(
    jobs,
    f,
    saved: saved,
    discarded: discarded,
    savedOnly: savedOnly,
  ).map((j) => j.id).toList()..sort());
  test('Paridad: seis verificadas por defecto', () {
    expect(ids(JobFilters()), [
      'gh-1',
      'gh-2',
      'gh-3',
      'gh-4',
      'gh-5',
      'sr-legacy',
    ]);
  });
  test('España se activa y desactiva', () {
    final f = JobFilters()..unverified = true;
    final all = ids(f);
    f.spain = true;
    expect(ids(f), ['gh-1', 'gh-5']);
    f.spain = false;
    expect(ids(f), all);
  });
  test('Elegibilidad y contradicciones', () {
    final f = JobFilters()..unverified = true;
    f.eligibility = 'confirmed';
    expect(ids(f), ['gh-1']);
    f.eligibility = 'possible';
    expect(ids(f), ['gh-2', 'gh-4']);
    f.eligibility = 'unknown';
    expect(ids(f), ['gh-5', 'sr-legacy']);
    f.eligibility = 'restricted';
    expect(ids(f), ['gh-3']);
  });
  test('Búsqueda AND sin acentos', () {
    expect(
      ids(
        JobFilters()
          ..unverified = true
          ..query = 'ALPHA senior',
      ),
      ['gh-1'],
    );
    expect(
      ids(
        JobFilters()
          ..unverified = true
          ..query = 'barcelóna',
      ),
      <String>[],
    );
  });
  test('Vistas compatibles y revisión', () {
    final f = JobFilters()
      ..unverified = true
      ..possible = true
      ..view = 'compatible';
    expect(ids(f), ['gh-1', 'gh-2']);
    f.view = 'review';
    expect(ids(f), ['gh-5', 'sr-legacy']);
  });
  test('Guardadas sin verificar y descartadas', () {
    expect(ids(JobFilters(), saved: {'az-1'}, savedOnly: true), <String>[]);
    expect(ids(JobFilters(), discarded: {'gh-1'}), isNot(contains('gh-1')));
  });
  test('URLs inseguras no se abren', () {
    expect(safeUrl('javascript:alert(1)'), null);
    expect(safeUrl('//evil.test'), null);
    expect(safeUrl('https://example.com/job'), 'https://example.com/job');
  });
  test('Stale no es verificada; legacy de Adzuna sigue agregador', () {
    expect(
      Job({'id': 'x', 'status': 'stale', 'verification': 'verified'}).verified,
      false,
    );
    final j = Job({
      'id': 'az-2',
      'ats': 'greenhouse',
      'url': 'https://example.com',
    });
    expect(j.source, 'aggregator');
    expect(j.verified, false);
    expect(j.direct, false);
  });
  test('Caché y versión desconocida', () async {
    SharedPreferences.setMockInitialValues({
      'jobs.cache': '{"schemaVersion":2,"jobs":[]}',
    });
    final r = JobsRepository(await SharedPreferences.getInstance());
    expect(r.cached()!['jobs'], isEmpty);
    expect(
      () => r.decode('{"schemaVersion":3,"jobs":[]}'),
      throwsFormatException,
    );
  });
}
