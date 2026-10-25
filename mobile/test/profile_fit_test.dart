import 'package:flutter_test/flutter_test.dart';
import 'package:vfx_jobs_tracker/profile_fit.dart';
import 'package:vfx_jobs_tracker/career_categories.dart';

void main() {
  test(
    'Engineer title does not require a degree; explicit mandatory degree does',
    () {
      final engineer = <String, dynamic>{
        'id': 'a',
        'title': 'Software Engineer',
        'category': 'programming',
        'workplace': 'remote',
        'description': 'FP DAM. Java development.',
      };
      final degree = {
        ...engineer,
        'id': 'b',
        'description': 'Mandatory university degree. Java development.',
      };
      final equivalent = {
        ...engineer,
        'id': 'c',
        'description': 'Bachelor degree required or equivalent experience.',
      };
      expect(educationFit(engineer), 'fp');
      expect(educationFit(degree), 'university');
      expect(educationFit(equivalent), 'fp');
      expect(
        filterCareerItems([
          engineer,
          degree,
          equivalent,
        ], category: 'programming').map((r) => r['id']),
        ['a', 'c'],
      );
      expect(
        filterCareerItems(
          [degree],
          category: 'programming',
          includeAdvanced: true,
        ),
        hasLength(1),
      );
    },
  );
  test('Unknown requirements and internships are not labelled compatible', () {
    expect(fitLabel({'title': 'Developer'}), 'Requisitos por confirmar');
    expect(fitLabel({'title': 'Beca soporte'}), 'Prácticas: comprobar acceso');
    expect(entryProfile({'title': 'Analytics Engineer'}), false);
    expect(
      entryProfile({'title': 'Web Developer (Fresh graduate welcome)'}),
      true,
    );
    expect(
      entryProfile({'title': 'Developer', 'description': 'FP2 DAM'}),
      true,
    );
  });
  test('Learning objective changes ordering without changing course topic', () {
    final basic = <String, dynamic>{
      'id': 'basic',
      'title': 'Java',
      'kind': 'course',
      'topic': 'programming',
      'price': 0,
      'modality': 'online',
      'level': 'beginner',
    };
    final advanced = {
      ...basic,
      'id': 'advanced',
      'title': 'Cloud',
      'level': 'advanced',
      'learningGoal': 'new',
    };
    expect(
      coursePriority(basic).score,
      greaterThan(coursePriority(advanced).score),
    );
    expect(
      coursePriority(advanced, goal: 'improve').score,
      greaterThan(coursePriority(basic, goal: 'improve').score),
    );
    expect(
      filterCareerItems(
        [basic, advanced],
        category: 'courses',
        topic: 'programming',
        goal: 'new',
        includeAdvanced: true,
      ).first['id'],
      'advanced',
    );
  });
}
