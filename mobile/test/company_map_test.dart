import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:vfx_jobs_tracker/company_map.dart';

void main() {
  final alpha = <String, dynamic>{
    'name': 'Alpha',
    'locations': [
      {'city': 'London', 'lat': 51.5, 'lon': -.1},
    ],
  };
  final beta = <String, dynamic>{
    'name': 'Beta',
    'locations': [
      {'city': 'London', 'lat': 51.5, 'lon': -.1},
    ],
  };
  test('Agrupa empresas próximas sin perder nombres', () {
    final groups = clusterMapPoints([
      MapPoint(const Offset(100, 100), alpha, 'London'),
      MapPoint(const Offset(110, 100), beta, 'London'),
      MapPoint(const Offset(500, 100), alpha, 'Madrid'),
    ]);
    expect(groups.length, 2);
    expect(groups.first.companies.map((c) => c['name']).toSet(), {
      'Alpha',
      'Beta',
    });
  });

  testWidgets(
    'Un grupo abre nombres legibles y permite seleccionar una empresa',
    (tester) async {
      String? selected;
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: SizedBox(
              width: 390,
              height: 360,
              child: CompanyWorldMap(
                polygons: const [],
                companies: [alpha, beta],
                onSelected: (name) => selected = name,
              ),
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();
      await tester.tap(find.byTooltip('Alpha, Beta'));
      await tester.pumpAndSettle();
      expect(find.text('2 empresas en esta zona'), findsOneWidget);
      await tester.tap(find.text('Beta'));
      await tester.pumpAndSettle();
      expect(selected, 'Beta');
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets('El pellizco amplía el mapa manteniendo marcadores pulsables', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SizedBox(
            width: 390,
            height: 360,
            child: CompanyWorldMap(
              polygons: const [],
              companies: [alpha, beta],
              onSelected: (_) {},
            ),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
    final viewer = tester.widget<InteractiveViewer>(
      find.byType(InteractiveViewer),
    );
    final before = viewer.transformationController!.value.getMaxScaleOnAxis();
    final first = await tester.startGesture(const Offset(120, 260), pointer: 1);
    final second = await tester.startGesture(
      const Offset(180, 260),
      pointer: 2,
    );
    await first.moveTo(const Offset(70, 260));
    await second.moveTo(const Offset(230, 260));
    await tester.pump();
    await first.up();
    await second.up();
    await tester.pumpAndSettle();
    expect(
      viewer.transformationController!.value.getMaxScaleOnAxis(),
      greaterThan(before),
    );
    expect(tester.takeException(), isNull);
  });
}
