import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'presentation.dart';

final appSettings = AppSettings();

class AppSettings extends ChangeNotifier {
  double textSize = 1;
  bool compact = false, autoRefresh = true;
  String startCategory = 'last';
  Future<void> load() async {
    final p = await SharedPreferences.getInstance();
    textSize = p.getDouble('app.textSize') ?? 1;
    compact = p.getBool('app.compact') ?? false;
    autoRefresh = p.getBool('app.autoRefresh') ?? true;
    startCategory = p.getString('app.startCategory') ?? 'last';
    notifyListeners();
  }

  Future<void> save() async {
    final p = await SharedPreferences.getInstance();
    await p.setDouble('app.textSize', textSize);
    await p.setBool('app.compact', compact);
    await p.setBool('app.autoRefresh', autoRefresh);
    await p.setString('app.startCategory', startCategory);
    notifyListeners();
  }
}

class AppSettingsPage extends StatelessWidget {
  final VoidCallback refresh;
  const AppSettingsPage({super.key, required this.refresh});
  @override
  Widget build(BuildContext context) => ListenableBuilder(
    listenable: appSettings,
    builder: (context, _) => ListView(
      padding: const EdgeInsets.all(16),
      children: [
        const RadarHeader(
          title: 'A tu manera',
          subtitle: 'Preferencias generales de este móvil',
          category: 'settings',
        ),
        const SizedBox(height: 20),
        const Text(
          'Presentación',
          style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 12),
        DropdownButtonFormField<double>(
          initialValue: appSettings.textSize,
          decoration: const InputDecoration(labelText: 'Tamaño del texto'),
          items: const [
            DropdownMenuItem(value: 1, child: Text('Tamaño del dispositivo')),
            DropdownMenuItem(value: 1.15, child: Text('Un poco más grande')),
            DropdownMenuItem(value: 1.3, child: Text('Más grande')),
          ],
          onChanged: (v) {
            appSettings.textSize = v!;
            appSettings.save();
          },
        ),
        SwitchListTile(
          contentPadding: EdgeInsets.zero,
          title: const Text('Tarjetas compactas'),
          subtitle: const Text(
            'Menos espacio entre elementos para ver más resultados.',
          ),
          value: appSettings.compact,
          onChanged: (v) {
            appSettings.compact = v;
            appSettings.save();
          },
        ),
        const Divider(height: 32),
        const Text(
          'Al abrir la app',
          style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 12),
        DropdownButtonFormField<String>(
          initialValue: appSettings.startCategory,
          isExpanded: true,
          decoration: const InputDecoration(labelText: 'Pantalla inicial'),
          items: [
            for (final e in {
              'last': 'Última categoría utilizada',
              'vfx': 'VFX',
              'programming': 'Programación',
              'electricity': 'Electricidad',
              'courses': 'Cursos',
              'public': 'Oposiciones',
            }.entries)
              DropdownMenuItem(value: e.key, child: Text(e.value)),
          ],
          onChanged: (v) {
            appSettings.startCategory = v!;
            appSettings.save();
          },
        ),
        SwitchListTile(
          contentPadding: EdgeInsets.zero,
          title: const Text('Actualizar al abrir'),
          subtitle: const Text(
            'Si lo desactivas, puedes deslizar las listas para consultar novedades.',
          ),
          value: appSettings.autoRefresh,
          onChanged: (v) {
            appSettings.autoRefresh = v;
            appSettings.save();
          },
        ),
        OutlinedButton.icon(
          onPressed: refresh,
          icon: const Icon(Icons.refresh),
          label: const Text('Actualizar empresas VFX ahora'),
        ),
        const Divider(height: 32),
        const Text(
          'Privacidad y sincronización',
          style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 8),
        const Text(
          'Las candidaturas se sincronizan al iniciar sesión. Las guardadas, filtros y estas preferencias se conservan solo en este móvil.',
          style: TextStyle(color: mutedColor),
        ),
        const SizedBox(height: 24),
        const Text(
          'Job Radar · 0.16.0',
          style: TextStyle(color: mutedColor, fontSize: 12),
        ),
      ],
    ),
  );
}
