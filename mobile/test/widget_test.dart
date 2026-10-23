import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:vfx_jobs_tracker/main.dart';

void main() {
  testWidgets('Arranque y navegación sin cuenta', (tester) async {
    SharedPreferences.setMockInitialValues({});
    await tester.pumpWidget(const TrackerApp());
    expect(find.text('YAGO / VFX JOBS'), findsOneWidget);
    await tester.tap(find.byIcon(Icons.settings_outlined));
    await tester.pump();
    expect(find.text('Tu radar de empleo VFX'), findsOneWidget);
    await tester.pumpWidget(const SizedBox());
  });
}
