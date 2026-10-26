import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:vfx_jobs_tracker/app_settings.dart';
import 'package:vfx_jobs_tracker/career_categories.dart';
import 'package:vfx_jobs_tracker/public_exams.dart';
import 'package:vfx_jobs_tracker/feed_freshness.dart';

void main() {
  test('Unrelated specialties stay out of the main view but saved records remain accessible', () {
    final outside = <String, dynamic>{
      'id': 'a',
      'title': 'Analytics Engineer',
      'category': 'programming',
      'workplace': 'remote',
      'profileMatch': 'outside',
    };
    final retrain = {...outside, 'id': 'b', 'profileMatch': 'retrain'};
    final current = {
      ...outside,
      'id': 'c',
      'title': 'Junior Developer',
      'profileMatch': 'current',
    };
    expect(
      filterCareerItems([
        outside,
        retrain,
        current,
      ], category: 'programming').map((r) => r['id']),
      ['c'],
    );
    expect(
      filterCareerItems(
        [outside, retrain, current],
        category: 'programming',
        profileScope: 'retrain',
      ).map((r) => r['id']),
      ['b'],
    );
    expect(
      filterCareerItems(
        [outside],
        category: 'programming',
        savedOnly: true,
        saved: {'a'},
      ),
      hasLength(1),
    );
  });
  test(
    'Unknown dates can be included explicitly without being labelled recent',
    () {
      final row = <String, dynamic>{
        'id': 'a',
        'title': 'Java Developer',
        'category': 'programming',
        'workplace': 'remote',
        'postedDate': null,
      };
      expect(
        filterCareerItems([row], category: 'programming', days: 30),
        isEmpty,
      );
      expect(
        filterCareerItems(
          [row],
          category: 'programming',
          days: 30,
          includeUnknownDates: true,
        ),
        hasLength(1),
      );
    },
  );
  test(
    'A newer bundled partial update cannot be replaced by an older cache',
    () {
      final bundled = <String, dynamic>{
        'updatedAt': '2026-10-25T12:00:00Z',
        'lastPartialUpdate': '2026-10-26T12:00:00Z',
      };
      final cache = <String, dynamic>{'updatedAt': '2026-10-26T10:00:00Z'};
      expect(newerFeed(bundled, cache), same(bundled));
      expect(
        newerFeed(bundled, {'updatedAt': '2026-10-27T12:00:00Z'})['updatedAt'],
        '2026-10-27T12:00:00Z',
      );
    },
  );
  test('Course center and origin filters work independently of specialty', () {
    final course = <String, dynamic>{
      'id': 'xunta',
      'title': 'Automatismos',
      'kind': 'course',
      'topic': 'electricity',
      'provider': 'Centro Vigo',
      'source': 'Xunta / DIPLOS',
      'price': 0,
      'modality': 'online',
      'level': 'intermediate',
    };
    final other = {
      ...course,
      'id': 'other',
      'provider': 'Otro centro',
      'source': 'Otra fuente',
    };
    expect(
      filterCareerItems(
        [course, other],
        category: 'courses',
        topic: 'all',
        origin: 'Xunta / DIPLOS',
      ).map((r) => r['id']),
      ['xunta'],
    );
    expect(
      filterCareerItems(
        [course, other],
        category: 'courses',
        organization: 'Otro centro',
      ).map((r) => r['id']),
      ['other'],
    );
    expect(
      filterCareerItems([course], category: 'courses', topic: 'programming'),
      isEmpty,
    );
  });
  test('Employer filters work for VFX and electrical roles', () {
    for (final category in ['vfx', 'electricity']) {
      final job = <String, dynamic>{
        'id': 'a',
        'title': 'Puesto',
        'category': category,
        'company': 'Empresa A',
        'inVigo': true,
      };
      expect(
        filterCareerItems(
          [
            job,
            {...job, 'id': 'b', 'company': 'Empresa B'},
          ],
          category: category,
          organization: 'Empresa A',
        ).map((r) => r['id']),
        ['a'],
      );
    }
  });
  test('Administrative scope and geographical scope are independent', () {
    final local = <String, dynamic>{
      'id': 'a',
      'title': 'Informática',
      'organization': 'Concello',
      'qualification': 'DAM',
      'area': 'galicia',
      'adminScope': 'local',
      'municipality': 'vigo',
      'closingDate': '2099-01-01',
    };
    final state = {
      ...local,
      'id': 'b',
      'adminScope': 'state',
      'municipality': null,
      'area': 'national',
    };
    expect(
      filterExams(
        [local, state],
        area: 'all',
        administration: 'state',
      ).map((r) => r['id']),
      ['b'],
    );
    expect(
      filterExams([local, state], area: 'local', administration: 'state'),
      isEmpty,
    );
  });
  test('General display and startup preferences survive restarting', () async {
    SharedPreferences.setMockInitialValues({});
    final settings = AppSettings()
      ..compact = true
      ..textSize = 1.3
      ..autoRefresh = false
      ..startCategory = 'courses';
    await settings.save();
    final restored = AppSettings();
    await restored.load();
    expect(restored.compact, true);
    expect(restored.textSize, 1.3);
    expect(restored.autoRefresh, false);
    expect(restored.startCategory, 'courses');
    settings.dispose();
    restored.dispose();
  });
}
