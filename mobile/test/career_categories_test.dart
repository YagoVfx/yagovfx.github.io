import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:vfx_jobs_tracker/career_categories.dart';
import 'package:vfx_jobs_tracker/applications.dart';
import 'package:vfx_jobs_tracker/jobs.dart';

void main() {
  setUp(() => rootBundle.clear());
  testWidgets(
    'VFX shows a single vacancy when employer and portal share its identity',
    (tester) async {
      final row = <String, dynamic>{
        'id': 'gh-1',
        'category': 'vfx',
        'title': 'Unified VFX Artist',
        'company': 'Studio',
        'location': 'Madrid',
        'source': 'Hitmarker',
        'sourceKind': 'job-board',
        'foundIn': ['Greenhouse', 'Hitmarker'],
        'url': 'https://example.test/jobs/1',
      };
      SharedPreferences.setMockInitialValues({
        'career.feed': jsonEncode({
          'schemaVersion': 2,
          'coverageVersion': 9,
          'offers': [row],
          'courses': [],
          'sources': [],
        }),
      });
      final store = ApplicationsStore();
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: CareerCategoryPage(
              category: 'vfx',
              feedRepository: CareerFeedRepository(
                client: MockClient((_) async => http.Response('{}', 503)),
              ),
              applications: store,
              openApplications: () {},
              directJobs: [
                Job({
                  ...row,
                  'sourceKind': 'ats',
                  'ats': 'greenhouse',
                  'verification': 'verified',
                  'status': 'active',
                  'workplaceType': 'remote',
                }),
              ],
            ),
          ),
        ),
      );
      await tester.runAsync(() async {
        await Future<void>.delayed(const Duration(milliseconds: 300));
      });
      await tester.pumpAndSettle();
      expect(find.text('Unified VFX Artist'), findsOneWidget);
      expect(find.text('Encontrada en 2 fuentes'), findsOneWidget);
      expect(tester.takeException(), isNull);
      await tester.pumpWidget(const SizedBox());
      store.dispose();
    },
  );
  test('Prioridad de cursos explica encaje y separa especialidades', () {
    final basic = <String, dynamic>{
      'id': 'basic',
      'kind': 'course',
      'title': 'Electricidad de circuitos',
      'topic': 'electricity',
      'price': 0,
      'modality': 'online',
      'level': 'beginner',
      'durationHours': 70,
    };
    final advanced = <String, dynamic>{
      'id': 'advanced',
      'title': 'Automatización avanzada',
      'topic': 'electricity',
      'price': 0,
      'modality': 'online',
      'level': 'advanced',
    };
    final programming = <String, dynamic>{
      'id': 'java',
      'title': 'Java',
      'topic': 'programming',
      'price': 0,
      'modality': 'online',
    };
    final closed = <String, dynamic>{
      ...basic,
      'id': 'closed',
      'enrollmentEnd': '2026-10-01',
    };
    expect(
      coursePriority(basic).score,
      greaterThan(coursePriority(advanced).score),
    );
    expect(coursePriority(basic).reasons, isNotEmpty);
    expect(
      filterCareerItems(
        [advanced, programming, basic, closed],
        category: 'courses',
        topic: 'electricity',
        includeAdvanced: true,
        now: DateTime.utc(2026, 10, 24),
      ).map((x) => x['id']),
      ['basic', 'advanced'],
    );
  });
  test('Coruña y publicación reciente: nunca usa la fecha de escaneo como publicación', () {
    final items = <Map<String, dynamic>>[
      {
        'id': 'new',
        'title': 'Electricista',
        'category': 'electricity',
        'inCoruna': true,
        'postedDate': '2026-10-22',
      },
      {
        'id': 'old',
        'title': 'Electricista',
        'category': 'electricity',
        'inCoruna': true,
        'postedDate': '2026-09-01',
        'checkedAt': '2026-10-24',
      },
      {
        'id': 'unknown',
        'title': 'Electricista',
        'category': 'electricity',
        'inCoruna': true,
        'checkedAt': '2026-10-24',
      },
    ];
    expect(
      filterCareerItems(
        items,
        category: 'electricity',
        scope: 'coruna',
        days: 7,
        now: DateTime.utc(2026, 10, 24),
      ).single['id'],
      'new',
    );
    expect(
      filterCareerItems(items, category: 'electricity', scope: 'vigo'),
      isEmpty,
    );
    expect(withinDays('2026-11-01', 7, now: DateTime.utc(2026, 10, 24)), false);
    expect(JobFilters.fromJson({'days': 7}).toJson()['days'], 7);
  });
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
            feedRepository: CareerFeedRepository(
              client: MockClient((_) async => http.Response('{}', 503)),
            ),
            applications: applications,
            openApplications: () {},
          ),
        ),
      ),
    );
    for (var attempt = 0; attempt < 15; attempt++) {
      await tester.runAsync(() async {
        await Future<void>.delayed(const Duration(milliseconds: 100));
      });
      await tester.pump();
      if (find.byType(CircularProgressIndicator).evaluate().isEmpty &&
          find.byType(LinearProgressIndicator).evaluate().isEmpty) {
        break;
      }
    }
    await tester.pumpAndSettle();
    expect(find.text('Cursos'), findsOneWidget);
    expect(find.text('Filtrar'), findsOneWidget);
    expect(find.text('Solo gratuitos o subvencionados'), findsNothing);
    await tester.tap(find.text('Filtrar'));
    await tester.pumpAndSettle();
    expect(find.text('Objetivo'), findsOneWidget);
    await tester.tap(find.byTooltip('Cerrar filtros'));
    await tester.pumpAndSettle();
    expect(find.text('Objetivo'), findsNothing);
    await tester.scrollUntilVisible(
      find.text('Escribir el primer código con C#'),
      250,
      scrollable: find.byType(Scrollable).first,
    );
    expect(tester.takeException(), isNull);
    tester
        .state<ScrollableState>(find.byType(Scrollable).first)
        .position
        .jumpTo(0);
    await tester.pump();
    await tester.tap(find.byType(DropdownButtonFormField<String>).first);
    await tester.pumpAndSettle();
    await tester.tap(find.text('VFX / Games'));
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(
      find.text('Niagara Introduction: repaso práctico de VFX en Unreal'),
      300,
      scrollable: find.byType(Scrollable).first,
    );
    expect(
      find.text('Niagara Introduction: repaso práctico de VFX en Unreal'),
      findsOneWidget,
    );
    expect(find.text('Escribir el primer código con C#'), findsNothing);
    await tester.ensureVisible(
      find.text('Niagara Introduction: repaso práctico de VFX en Unreal'),
    );
    await tester.pumpAndSettle();
    await tester.tap(
      find.text('Niagara Introduction: repaso práctico de VFX en Unreal'),
    );
    await tester.pumpAndSettle();
    expect(find.text('Formación'), findsOneWidget);
    await tester.scrollUntilVisible(
      find.widgetWithText(OutlinedButton, 'Guardar'),
      250,
      scrollable: find.byType(Scrollable).last,
    );
    await tester.ensureVisible(find.widgetWithText(OutlinedButton, 'Guardar'));
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(OutlinedButton, 'Guardar'));
    await tester.pumpAndSettle();
    expect(find.text('Guardado'), findsOneWidget);
    await tester.pageBack();
    await tester.pumpAndSettle();
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
            jsonEncode({
              'schemaVersion': 2,
              'coverageVersion': 9,
              'offers': [],
              'courses': [],
            }),
            200,
          ),
        ),
      );
      expect((await good.refresh(prefs))['offers'], isEmpty);
      expect(jsonDecode(prefs.getString('career.feed')!)['schemaVersion'], 2);
      good.close();
    },
  );
}
