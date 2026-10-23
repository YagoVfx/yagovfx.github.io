import 'package:flutter_test/flutter_test.dart';
import 'package:vfx_jobs_tracker/jobs.dart';
import 'package:vfx_jobs_tracker/insights.dart';

void main() {
  test('Cuenta plataformas reales con ceros, sin agregadores ni cerradas', () {
    Job job(String id, {String status = 'active', bool aggregator = false}) =>
        Job({
          'id': id,
          'company': 'Room8',
          'ats': 'custom',
          'sourceKind': 'official-site',
          'status': status,
          'viaAggregator': aggregator,
        });
    final rows = platformCounts(
      [
        job('r8-1'),
        job('az-1'),
        job('old', status: 'closed'),
        job('external', aggregator: true),
      ],
      [
        {'name': 'Room8', 'type': 'room8'},
        {'name': 'Empty', 'type': 'greenhouse'},
      ],
    );
    expect(rows.map((e) => '${e.key}:${e.value}').toList(), [
      'WordPress:1',
      'Greenhouse:0',
    ]);
  });
}
