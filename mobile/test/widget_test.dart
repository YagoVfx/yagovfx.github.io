import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:vfx_jobs_tracker/main.dart';
import 'package:vfx_jobs_tracker/insights.dart';
import 'package:vfx_jobs_tracker/company_map.dart';

void main() {
  testWidgets('Cuatro pestañas superiores visibles en móvil estrecho', (
    tester,
  ) async {
    SharedPreferences.setMockInitialValues({});
    tester.view.physicalSize = const Size(320, 740);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await tester.pumpWidget(const TrackerApp());
    expect(find.text('VFX'), findsOneWidget);
    expect(find.text('Código'), findsOneWidget);
    expect(find.text('Electricidad'), findsOneWidget);
    expect(find.text('Cursos'), findsOneWidget);
    await tester.tap(find.text('Portales'));
    await tester.pump();
    await tester.runAsync(() async {
      await Future<void>.delayed(const Duration(milliseconds: 300));
    });
    await tester.pumpAndSettle();
    expect(find.text('VFX / Games · Portales'), findsOneWidget);
    expect(tester.takeException(), isNull);
    await tester.tap(find.text('Código'));
    await tester.pump();
    await tester.runAsync(() async {
      await Future<void>.delayed(const Duration(milliseconds: 300));
    });
    await tester.pumpAndSettle();
    expect(find.text('Programación'), findsOneWidget);
    expect(tester.takeException(), isNull);
    await tester.pumpWidget(const SizedBox());
  });
  testWidgets('Arranque y navegación sin cuenta', (tester) async {
    SharedPreferences.setMockInitialValues({});
    await tester.pumpWidget(const TrackerApp());
    expect(find.text('YAGO / JOB RADAR'), findsOneWidget);
    await tester.tap(find.byIcon(Icons.settings_outlined));
    await tester.pump();
    expect(find.text('Tu radar de empleo'), findsOneWidget);
    await tester.pumpWidget(const SizedBox());
  });

  testWidgets(
    'Radar carga su copia local y dibuja el mapa en pantalla estrecha',
    (tester) async {
      SharedPreferences.setMockInitialValues({});
      tester.view.physicalSize = const Size(390, 844);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(body: InsightsPage(jobs: [])),
        ),
      );
      await tester.tap(find.text('Mapa'));
      await tester.pump();
      await tester.runAsync(() async {
        await Future<void>.delayed(const Duration(milliseconds: 300));
      });
      await tester.pumpAndSettle();
      expect(find.text('Mapa de empresas'), findsOneWidget);
      await tester.scrollUntilVisible(
        find.byType(CompanyWorldMap),
        300,
        scrollable: find.byType(Scrollable).first,
      );
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
      expect(find.byType(InteractiveViewer), findsOneWidget);
      await tester.pumpWidget(const SizedBox());
    },
  );
}
