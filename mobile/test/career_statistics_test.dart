import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:vfx_jobs_tracker/career_statistics.dart';

void main() {
  test('ATS attribution distinguishes employer portals from job boards', () {
    expect(careerPlatform({'source': 'Plain Concepts · Workable'}), 'Workable');
    expect(
      careerPlatform({
        'source': 'Portal de empresa',
        'company': 'Indra / Minsait',
      }),
      'SuccessFactors',
    );
    expect(
      careerPlatform({'source': 'We Work Remotely'}),
      'Web / portal público',
    );
  });
  testWidgets(
    'Statistics shows programming ATS and a separate training catalog at narrow width',
    (tester) async {
      SharedPreferences.setMockInitialValues({});
      tester.view.physicalSize = const Size(320, 740);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      await tester.pumpWidget(
        const MaterialApp(home: Scaffold(body: CareerStatistics())),
      );
      await tester.runAsync(() async {
        await Future<void>.delayed(const Duration(milliseconds: 400));
      });
      await tester.pumpAndSettle();
      expect(find.text('ATS conectados'), findsOneWidget);
      expect(find.text('Workable'), findsOneWidget);
      await tester.tap(find.byType(DropdownButtonFormField<String>));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Cursos').last);
      await tester.pumpAndSettle();
      expect(find.textContaining('con consulta automática ·'), findsOneWidget);
      expect(find.text('ATS conectados'), findsNothing);
      expect(tester.takeException(), isNull);
      await tester.pumpWidget(const SizedBox());
    },
  );
}
