import 'dart:math' as math;

import 'package:flutter/material.dart';

class MapPoint {
  final Offset position;
  final Map<String, dynamic> company;
  final String city;
  MapPoint(this.position, this.company, this.city);
}

class MapCluster {
  final List<MapPoint> points;
  MapCluster(MapPoint point) : points = [point];
  Offset get center =>
      points.fold(Offset.zero, (sum, p) => sum + p.position) /
      points.length.toDouble();
  List<Map<String, dynamic>> get companies =>
      {for (final p in points) p.company['name'] as String: p.company}.values
          .toList();
}

List<MapCluster> clusterMapPoints(List<MapPoint> points, {double radius = 44}) {
  final groups = <MapCluster>[];
  for (final point in points) {
    MapCluster? target;
    for (final group in groups) {
      if ((group.center - point.position).distance < radius) {
        target = group;
        break;
      }
    }
    if (target == null) {
      groups.add(MapCluster(point));
    } else {
      target.points.add(point);
    }
  }
  return groups;
}

class CompanyWorldMap extends StatefulWidget {
  final List polygons;
  final List<Map<String, dynamic>> companies;
  final ValueChanged<String> onSelected;
  const CompanyWorldMap({
    super.key,
    required this.polygons,
    required this.companies,
    required this.onSelected,
  });
  @override
  State<CompanyWorldMap> createState() => _CompanyMapState();
}

class _CompanyMapState extends State<CompanyWorldMap> {
  final transform = TransformationController();
  Size viewport = Size.zero;
  bool fitScheduled = false;
  double baseScale = .2;
  @override
  void initState() {
    super.initState();
    transform.addListener(update);
  }

  void update() {
    if (mounted) setState(() {});
  }

  @override
  void dispose() {
    transform.removeListener(update);
    transform.dispose();
    super.dispose();
  }

  @override
  void didUpdateWidget(covariant CompanyWorldMap oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.companies.map((c) => c['name']).join('|') !=
        widget.companies.map((c) => c['name']).join('|')) {
      scheduleFit();
    }
  }

  Offset worldPoint(Map p) => Offset(
    ((p['lon'] as num) + 180) / 360 * 2000,
    (90 - (p['lat'] as num)) / 180 * 1000,
  );
  void scheduleFit() {
    if (fitScheduled) return;
    fitScheduled = true;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      fitScheduled = false;
      if (mounted) fit();
    });
  }

  void fit() {
    if (viewport.isEmpty) return;
    baseScale = math.min(viewport.width / 2000, viewport.height / 1000);
    final points = [
      for (final c in widget.companies)
        for (final p in c['locations'] as List) worldPoint(p),
    ];
    var scale = baseScale, cx = 1000.0, cy = 500.0;
    if (widget.companies.length == 1 && points.isNotEmpty) {
      final xs = points.map((p) => p.dx), ys = points.map((p) => p.dy);
      final minX = xs.reduce(math.min),
          maxX = xs.reduce(math.max),
          minY = ys.reduce(math.min),
          maxY = ys.reduce(math.max);
      scale = math.min(
        3.0,
        math.min(
          (viewport.width - 80) / math.max(40, maxX - minX),
          (viewport.height - 80) / math.max(40, maxY - minY),
        ),
      );
      cx = (minX + maxX) / 2;
      cy = (minY + maxY) / 2;
    }
    transform.value = Matrix4.diagonal3Values(scale, scale, 1)
      ..setTranslationRaw(
        viewport.width / 2 - cx * scale,
        viewport.height / 2 - cy * scale,
        0,
      );
  }

  void zoom(double factor) {
    final center = Offset(viewport.width / 2, viewport.height / 2),
        anchor = transform.toScene(center);
    final next = (transform.value.getMaxScaleOnAxis() * factor).clamp(
      baseScale,
      8.0,
    );
    transform.value = Matrix4.diagonal3Values(next, next, 1)
      ..setTranslationRaw(
        center.dx - anchor.dx * next,
        center.dy - anchor.dy * next,
        0,
      );
  }

  void openCluster(MapCluster group) {
    final companies = group.companies
      ..sort((a, b) => (a['name'] as String).compareTo(b['name'] as String));
    if (companies.length == 1) {
      openCompany(group, companies.first);
      return;
    }
    showModalBottomSheet(
      context: context,
      showDragHandle: true,
      isScrollControlled: true,
      builder: (context) => SafeArea(
        child: ConstrainedBox(
          constraints: BoxConstraints(
            maxHeight: MediaQuery.sizeOf(context).height * .65,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Padding(
                padding: const EdgeInsets.all(16),
                child: Text(
                  '${companies.length} empresas en esta zona',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
              ),
              Flexible(
                child: ListView(
                  shrinkWrap: true,
                  children: companies
                      .map(
                        (c) => ListTile(
                          title: Text(c['name'] as String),
                          subtitle: Text(
                            group.points
                                .where((p) => p.company['name'] == c['name'])
                                .map((p) => p.city)
                                .toSet()
                                .join(' · '),
                          ),
                          trailing: const Icon(Icons.chevron_right),
                          onTap: () {
                            Navigator.pop(context);
                            openCompany(group, c);
                          },
                        ),
                      )
                      .toList(),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  void openCompany(MapCluster group, Map<String, dynamic> company) {
    final cities = group.points
        .where((p) => p.company['name'] == company['name'])
        .map((p) => p.city)
        .toSet()
        .join(' · ');
    showModalBottomSheet(
      context: context,
      showDragHandle: true,
      builder: (sheetContext) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                company['name'] as String,
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 12),
              Text('Ubicación seleccionada: $cities'),
              const SizedBox(height: 20),
              FilledButton.icon(
                icon: const Icon(Icons.public),
                label: const Text('Ver todas sus sedes'),
                onPressed: () {
                  Navigator.pop(sheetContext);
                  widget.onSelected(company['name'] as String);
                  scheduleFit();
                },
              ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) => LayoutBuilder(
    builder: (context, box) {
      final size = Size(box.maxWidth, box.maxHeight);
      if (viewport != size) {
        viewport = size;
        scheduleFit();
      }
      final points = [
        for (final c in widget.companies)
          for (final p in c['locations'] as List)
            MapPoint(
              MatrixUtils.transformPoint(transform.value, worldPoint(p)),
              c,
              p['city'] as String,
            ),
      ];
      final groups = clusterMapPoints(points);
      return ClipRRect(
        borderRadius: BorderRadius.circular(14),
        child: ColoredBox(
          color: const Color(0xff0d1727),
          child: Stack(
            children: [
              GestureDetector(
                onDoubleTap: () => zoom(2),
                child: InteractiveViewer(
                  constrained: false,
                  transformationController: transform,
                  minScale: .05,
                  maxScale: 8,
                  boundaryMargin: const EdgeInsets.all(400),
                  child: CustomPaint(
                    size: const Size(2000, 1000),
                    painter: WorldShapePainter(widget.polygons),
                  ),
                ),
              ),
              for (final group in groups)
                if (group.center.dx >= 0 &&
                    group.center.dx <= viewport.width &&
                    group.center.dy >= 0 &&
                    group.center.dy <= viewport.height)
                  Positioned(
                    left: group.center.dx - 23,
                    top: group.center.dy - 23,
                    child: Semantics(
                      button: true,
                      label:
                          '${group.companies.length} empresas: ${group.companies.map((c) => c['name']).join(', ')}',
                      child: Tooltip(
                        message: group.companies
                            .map((c) => c['name'])
                            .join(', '),
                        child: Material(
                          color: Colors.transparent,
                          child: InkWell(
                            borderRadius: BorderRadius.circular(24),
                            onTap: () => openCluster(group),
                            child: SizedBox(
                              width: 46,
                              height: 46,
                              child: Center(
                                child: Container(
                                  width: group.companies.length > 1 ? 38 : 25,
                                  height: group.companies.length > 1 ? 38 : 25,
                                  decoration: BoxDecoration(
                                    shape: BoxShape.circle,
                                    color: group.companies.length > 1
                                        ? const Color(0xffa997ff)
                                        : const Color(0xff69e2ce),
                                    border: Border.all(
                                      color: const Color(0xff101b2c),
                                      width: 3,
                                    ),
                                  ),
                                  alignment: Alignment.center,
                                  child: Text(
                                    group.companies.length > 1
                                        ? '${group.companies.length}'
                                        : '•',
                                    style: const TextStyle(
                                      color: Color(0xff101725),
                                      fontWeight: FontWeight.bold,
                                    ),
                                  ),
                                ),
                              ),
                            ),
                          ),
                        ),
                      ),
                    ),
                  ),
              Positioned(
                left: 8,
                top: 8,
                child: Column(
                  children: [
                    IconButton.filledTonal(
                      onPressed: () => zoom(1.5),
                      tooltip: 'Ampliar mapa',
                      icon: const Icon(Icons.add),
                    ),
                    IconButton.filledTonal(
                      onPressed: () => zoom(1 / 1.5),
                      tooltip: 'Reducir mapa',
                      icon: const Icon(Icons.remove),
                    ),
                    IconButton.filledTonal(
                      onPressed: fit,
                      tooltip: 'Restablecer vista',
                      icon: const Icon(Icons.fit_screen),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      );
    },
  );
}

class WorldShapePainter extends CustomPainter {
  final List polygons;
  WorldShapePainter(this.polygons);
  @override
  void paint(Canvas canvas, Size size) {
    for (final polygon in polygons) {
      final path = Path();
      var first = true;
      for (final point in polygon) {
        final x = (point[0] as num).toDouble() * 2,
            y = (point[1] as num).toDouble() * 2;
        if (first) {
          path.moveTo(x, y);
          first = false;
        } else {
          path.lineTo(x, y);
        }
      }
      path.close();
      canvas.drawPath(path, Paint()..color = const Color(0xff263c52));
      canvas.drawPath(
        path,
        Paint()
          ..style = PaintingStyle.stroke
          ..strokeWidth = .7
          ..color = const Color(0xff49667f),
      );
    }
  }

  @override
  bool shouldRepaint(covariant WorldShapePainter oldDelegate) =>
      oldDelegate.polygons != polygons;
}
