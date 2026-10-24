import 'dart:convert';

import 'package:flutter/material.dart';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:vfx_jobs_tracker/career_categories.dart';
import 'package:vfx_jobs_tracker/applications.dart';

void main() {
  testWidgets('Cursos carga recursos reales y filtros en un móvil estrecho', (
    tester,
  ) async {
    SharedPreferences.setMockInitialValues({});
    tester.view.physicalSize = const Size(320, 740);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    final applications = ApplicationsStore();
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: CareerCategoryPage(
            category: 'courses',
            applications: applications,
            openApplications: () {},
          ),
        ),
      ),
    );
    await tester.runAsync(() async {
      await Future<void>.delayed(const Duration(milliseconds: 300));
    });
    await tester.pumpAndSettle();
    expect(find.text('Cursos'), findsOneWidget);
    expect(find.textContaining('800 €'), findsOneWidget);
    await tester.scrollUntilVisible(
      find.text('Escribir el primer código con C#'),
      250,
      scrollable: find.byType(Scrollable).first,
    );
    expect(tester.takeException(), isNull);
    await tester.pumpWidget(const SizedBox());
    applications.dispose();
  });
  test(
    'Filtra ubicación real, modalidad y experiencia sin mezclar categorías',
    () {
      final jobs = <Map<String, dynamic>>[
        {
          'id': 'remote',
          'title': 'Developer',
          'category': 'programming',
          'workplace': 'remote',
        },
        {
          'id': 'hybrid',
          'title': 'Developer',
          'category': 'programming',
          'workplace': 'hybrid',
        },
        {
          'id': 'senior',
          'title': 'Developer',
          'category': 'programming',
          'workplace': 'remote',
          'experience': 'experienced',
        },
        {
          'id': 'vigo',
          'title': 'Electricista',
          'category': 'electricity',
          'inVigo': true,
        },
        {
          'id': 'other',
          'title': 'Electricista',
          'category': 'electricity',
          'inVigo': false,
        },
      ];
      expect(
        filterCareerItems(jobs, category: 'programming').map((j) => j['id']),
        ['remote'],
      );
      expect(
        filterCareerItems(
          jobs,
          category: 'programming',
          includeAdvanced: true,
        ).length,
        2,
      );
      expect(
        filterCareerItems(jobs, category: 'electricity').single['id'],
        'vigo',
      );
    },
  );

  test('Cursos con precio confirmado, presupuesto y presenciales en Vigo', () {
    final courses = <Map<String, dynamic>>[
      {'id': 'free', 'title': 'Gratis', 'price': 0, 'modality': 'online'},
      {'id': 'paid', 'title': 'Pago', 'price': 600, 'modality': 'online'},
      {'id': 'unknown', 'title': 'Sin precio', 'modality': 'online'},
      {'id': 'expensive', 'title': 'Caro', 'price': 900, 'modality': 'online'},
      {
        'id': 'outside',
        'title': 'Presencial fuera',
        'price': 0,
        'modality': 'onsite',
      },
      {
        'id': 'advanced',
        'title': 'Avanzado',
        'price': 0,
        'modality': 'online',
        'level': 'advanced',
      },
    ];
    expect(
      filterCareerItems(courses, category: 'courses').map((c) => c['id']),
      ['free', 'paid'],
    );
    expect(
      filterCareerItems(
        courses,
        category: 'courses',
        freeOnly: true,
      ).single['id'],
      'free',
    );
  });

  test('Las ofertas caducadas no se ofrecen pero se conserva la guardada', () {
    final jobs = <Map<String, dynamic>>[
      {
        'id': 'old',
        'title': 'Developer',
        'category': 'programming',
        'workplace': 'remote',
        'closingDate': '2026-10-01',
      },
    ];
    expect(
      filterCareerItems(
        jobs,
        category: 'programming',
        now: DateTime(2026, 10, 24),
      ),
      isEmpty,
    );
    expect(
      filterCareerItems(
        jobs,
        category: 'programming',
        savedOnly: true,
        saved: {'old'},
        now: DateTime(2026, 10, 24),
      ),
      hasLength(1),
    );
  });

  test(
    'Una respuesta inválida no sobrescribe la última copia válida',
    () async {
      SharedPreferences.setMockInitialValues({'career.feed': 'previous'});
      final prefs = await SharedPreferences.getInstance();
      final bad = CareerFeedRepository(
        client: MockClient((_) async => http.Response('{}', 200)),
      );
      await expectLater(bad.refresh(prefs), throwsFormatException);
      expect(prefs.getString('career.feed'), 'previous');
      bad.close();
      final good = CareerFeedRepository(
        client: MockClient(
          (_) async => http.Response(
            jsonEncode({'schemaVersion': 1, 'offers': [], 'courses': []}),
            200,
          ),
        ),
      );
      expect((await good.refresh(prefs))['offers'], isEmpty);
      expect(jsonDecode(prefs.getString('career.feed')!)['schemaVersion'], 1);
      good.close();
    },
  );
}
