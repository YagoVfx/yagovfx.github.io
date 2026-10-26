DateTime? feedDate(Map<String, dynamic> feed) {
  final dates =
      ['updatedAt', 'lastPartialUpdate']
          .map((k) => DateTime.tryParse('${feed[k]}'))
          .whereType<DateTime>()
          .toList()
        ..sort();
  return dates.isEmpty ? null : dates.last;
}

Map<String, dynamic> newerFeed(
  Map<String, dynamic> current,
  Map<String, dynamic> candidate,
) {
  final a = feedDate(current), b = feedDate(candidate);
  return a != null && b != null && b.isBefore(a) ? current : candidate;
}
