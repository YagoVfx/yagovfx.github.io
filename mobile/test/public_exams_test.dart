import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:vfx_jobs_tracker/public_exams.dart';

void main() {
  test('Municipal default excludes provincial and state calls and expired deadlines', () {
    final rows = <Map<String, dynamic>>[
      {
        'id': 'local',
        'municipality': 'coruna',
        'area': 'galicia',
        'title': 'Informática',
        'closingDate': '2026-10-29',
      },
      {
        'id': 'province',
        'municipality': null,
        'area': 'galicia',
        'closingDate': '2026-10-29',
      },
      {'id': 'national', 'area': 'national', 'closingDate': '2026-10-29'},
      {
        'id': 'closed',
        'municipality': 'vigo',
        'area': 'galicia',
        'closingDate': '2026-10-24',
      },
    ];
    expect(
      filterExams(rows, now: DateTime.utc(2026, 10, 25)).map((r) => r['id']),
      ['local'],
    );
    expect(
      filterExams(rows, area: 'all', now: DateTime.utc(2026, 10, 25)),
      hasLength(3),
    );
  });
  testWidgets(
    'Municipal scope and original bases remain visible on narrow screen',
    (tester) async {
      SharedPreferences.setMockInitialValues({
        'exams.cache': jsonEncode({
          'schemaVersion': 1,
          'coverageVersion': 2,
          'calls': [
            {
              'id': 'test',
              'municipality': 'coruna',
              'area': 'galicia',
              'title': 'Técnico de Informática',
              'organization': 'Concello da Coruña',
              'qualification': 'DAM',
              'fit': 'dam',
              'freePlaces': 2,
              'places': 2,
              'closingDate': '2099-10-29',
              'reference': 'test',
              'source': 'PAG',
              'access': 'Acceso libre',
              'url': 'https://example.test/bases',
              'searchUrl': 'https://example.test/search',
              'deadlineEvidence': 'Confirmar las bases',
            },
          ],
          'sources': [],
          'note': 'Cobertura parcial',
        }),
      });
      tester.view.physicalSize = const Size(320, 740);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      await tester.pumpWidget(
        const MaterialApp(home: Scaffold(body: PublicExamsPage())),
      );
      await tester.runAsync(() async {
        await Future<void>.delayed(const Duration(milliseconds: 300));
      });
      await tester.pumpAndSettle();
      expect(find.text('Vigo y A Coruña (municipios)'), findsOneWidget);
      await tester.ensureVisible(find.text('Técnico de Informática'));
      await tester.tap(find.text('Técnico de Informática'));
      await tester.pumpAndSettle();
      expect(find.text('La titulación publicada incluye DAM'), findsOneWidget);
      expect(tester.takeException(), isNull);
      await tester.pumpWidget(const SizedBox());
    },
  );
}
