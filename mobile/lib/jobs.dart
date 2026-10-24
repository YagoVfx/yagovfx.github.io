import 'dart:convert';

import 'geography.dart';

import 'package:diacritic/diacritic.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

String fold(Object? s) => removeDiacritics('$s').toLowerCase();
bool withinDays(Object? value, int days, {DateTime? now}) {
  if (days == 0) return true;
  final date = DateTime.tryParse('$value');
  if (date == null) return false;
  final age = (now ?? DateTime.now()).toUtc().difference(date.toUtc());
  return !age.isNegative && age < Duration(days: days);
}

String? safeUrl(Object? s) {
  final u = Uri.tryParse(s is String ? s.trim() : '');
  return u != null && ['http', 'https'].contains(u.scheme) && u.host.isNotEmpty
      ? u.toString()
      : null;
}

class Job {
  final Map<String, dynamic> data;
  Job(Map<String, dynamic> raw) : data = Map.of(raw) {
    if (id.startsWith('az-') &&
        !['adzuna', 'adzuna-signal', ''].contains(str('ats', ''))) {
      data['companyCareersUrl'] ??= data['url'];
      data.addAll({
        'ats': 'adzuna',
        'viaAggregator': true,
        'urlIsLanding': true,
        'verification': 'unverified',
      });
    }
  }
  String str(String k, [String fallback = 'unknown']) =>
      data[k] is String && (data[k] as String).isNotEmpty ? data[k] : fallback;
  String get id => str('id', '');
  String get title => str('title', 'Sin título');
  String get company => str('company', 'Empresa desconocida');
  String get status => str('status', 'active');
  String get eligibility => str('spainEligibility');
  String get source {
    if (data['signalOnly'] == true ||
        id.startsWith('sig-') ||
        str('ats') == 'adzuna-signal') {
      return 'signal';
    }
    if (data['viaAggregator'] == true || str('ats') == 'adzuna') {
      return 'aggregator';
    }
    if (data['sourceKind'] is String) return data['sourceKind'];
    if (str('ats') == 'custom') return 'official-site';
    return [
          'greenhouse',
          'lever',
          'ashby',
          'smartrecruiters',
          'recruitee',
          'personio',
          'teamtailor',
          'workday',
          'workable',
          'massive-wp',
        ].contains(str('ats'))
        ? 'ats'
        : 'aggregator';
  }

  bool get isDirectSource =>
      ['ats', 'official-site'].contains(source) &&
      !id.startsWith('az-') &&
      !id.startsWith('sig-') &&
      data['viaAggregator'] != true;
  bool get verified =>
      status == 'active' &&
      (data['verification'] == 'verified' ||
          (data['verification'] == null &&
              ['ats', 'official-site'].contains(source) &&
              safeUrl(data['url']) != null));
  bool get direct => data['directUrl'] is bool
      ? data['directUrl']
      : data['urlIsLanding'] != true && source != 'signal';
  String get compatibility {
    if ([
      'compatible',
      'review',
      'incompatible',
    ].contains(data['compatibility'])) {
      return data['compatibility'];
    }
    if (eligibility == 'restricted' ||
        str('contractType') == 'freelance' ||
        str('hours') == 'part') {
      return 'incompatible';
    }
    return ['confirmed', 'possible'].contains(eligibility) &&
            str('contractType') != 'temporary'
        ? 'compatible'
        : 'review';
  }

  bool get inSpain =>
      RegExp(
        r'espa(n|ñ)a|spain',
        caseSensitive: false,
      ).hasMatch(str('location', '')) ||
      fold(str('remoteScope')) == 'spain' ||
      eligibility == 'confirmed';
  Map get relevance => data['relevance'] is Map ? data['relevance'] : {};
  num get score => relevance['score'] is num ? relevance['score'] : 0;
  List<String> get reasons => relevance['reasons'] is List
      ? (relevance['reasons'] as List).map((e) => '$e').toList()
      : ['Sin puntuación: pendiente de un nuevo escaneo.'];
  DateTime get date =>
      DateTime.tryParse(str('postedDate', '')) ??
      DateTime.tryParse(str('firstSeen', '')) ??
      DateTime.fromMillisecondsSinceEpoch(0);
}

class JobFilters {
  int days = 0;
  String query = '',
      view = 'all',
      workplace = 'all',
      eligibility = 'all',
      contract = 'all',
      sort = 'relevance';
  bool spain = false, eu = false, unverified = false, possible = false;
  JobFilters();
  JobFilters.fromJson(Map m) {
    days = [0, 1, 7, 30].contains(m['days']) ? m['days'] : 0;
    query = m['query'] is String ? m['query'] : '';
    view = pick(m['view'], ['all', 'compatible', 'review']);
    workplace = pick(m['workplace'], [
      'all',
      'remote',
      'hybrid',
      'onsite',
      'unknown',
    ]);
    eligibility = pick(m['eligibility'], [
      'all',
      'confirmed',
      'possible',
      'unknown',
      'restricted',
    ]);
    contract = pick(m['contract'], [
      'all',
      'employee',
      'freelance',
      'temporary',
      'unknown',
    ]);
    sort = pick(m['sort'], ['relevance', 'recent', 'company']);
    spain = m['spain'] == true;
    eu = m['eu'] == true;
    unverified = m['unverified'] == true;
    possible = m['possible'] == true;
  }
  static String pick(dynamic s, List<String> values) =>
      values.contains(s) ? s : values.first;
  Map<String, dynamic> toJson() => {
    'days': days,
    'query': query,
    'view': view,
    'workplace': workplace,
    'eligibility': eligibility,
    'contract': contract,
    'sort': sort,
    'spain': spain,
    'eu': eu,
    'unverified': unverified,
    'possible': possible,
  };
}

List<Job> filterJobs(
  List<Job> jobs,
  JobFilters f, {
  Set<String> saved = const {},
  Set<String> discarded = const {},
  bool savedOnly = false,
}) {
  final out = jobs.where((j) {
    if (!j.isDirectSource || j.status == 'closed') return false;
    if (!withinDays(j.data['postedDate'] ?? j.data['firstSeen'], f.days)) {
      return false;
    }
    if (savedOnly) {
      if (!saved.contains(j.id)) return false;
    } else {
      if (discarded.contains(j.id) || (!f.unverified && !j.verified)) {
        return false;
      }
      if (f.view != 'all' && j.compatibility != f.view) return false;
    }
    if (!f.possible && j.str('matchType') == 'possibleMatch') return false;
    if (f.spain && !j.inSpain) return false;
    if (f.eu && !isEUJob(j.data)) return false;
    if (f.workplace != 'all' && j.str('workplaceType') != f.workplace) {
      return false;
    }
    if (f.contract != 'all' && j.str('contractType') != f.contract) {
      return false;
    }
    final e = j.eligibility == 'contradiction' ? 'unknown' : j.eligibility;
    if (f.eligibility != 'all' && e != f.eligibility) return false;
    final hay = fold(
      '${j.company} ${j.title} ${j.str('location', '')} ${j.data['engines']} ${j.str('seniority')} ${j.str('role')}',
    );
    return fold(f.query).trim().split(RegExp(r'\s+')).every(hay.contains);
  }).toList();
  out.sort((a, b) {
    if (f.sort == 'company') return fold(a.company).compareTo(fold(b.company));
    if (f.sort == 'recent') return b.date.compareTo(a.date);
    final n = b.score.compareTo(a.score);
    return n != 0 ? n : b.date.compareTo(a.date);
  });
  return out;
}

class JobsRepository {
  static final endpoint = Uri.parse('https://yagovfx.github.io/data/jobs.json');
  final SharedPreferences prefs;
  JobsRepository(this.prefs);
  Map<String, dynamic>? cached() {
    try {
      final raw = prefs.getString('jobs.cache');
      return raw == null ? null : decode(raw);
    } catch (_) {
      return null;
    }
  }

  Map<String, dynamic> decode(String raw) {
    final v = jsonDecode(raw);
    if (v is! Map<String, dynamic> || v['jobs'] is! List) {
      throw const FormatException('Formato de ofertas no válido');
    }
    if (v['schemaVersion'] is num && v['schemaVersion'] > 2) {
      throw const FormatException(
        'Actualiza la app: formato nuevo de ofertas.',
      );
    }
    return v;
  }

  Future<Map<String, dynamic>> refresh() async {
    final etag = prefs.getString('jobs.etag');
    final r = await http
        .get(
          endpoint,
          headers: {
            if (etag != null && cached() != null) 'If-None-Match': etag,
          },
        )
        .timeout(const Duration(seconds: 25));
    if (r.statusCode == 304 && cached() != null) return cached()!;
    if (r.statusCode != 200) throw Exception('HTTP ${r.statusCode}');
    final raw = utf8.decode(r.bodyBytes), v = decode(raw);
    await prefs.setString('jobs.cache', raw);
    if (r.headers['etag'] != null) {
      await prefs.setString('jobs.etag', r.headers['etag']!);
    } else {
      await prefs.remove('jobs.etag');
    }
    return v;
  }
}
