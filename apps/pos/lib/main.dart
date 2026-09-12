import 'dart:io';

import 'package:drift/native.dart';
import 'package:drift/drift.dart' hide Column;
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:go_router/go_router.dart';
import 'package:path_provider/path_provider.dart';

enum DeviceState { loading, notActivated, activated, offline }

class DeviceRepository {
  DeviceRepository(this.storage);
  final FlutterSecureStorage storage;

  Future<DeviceState> load() async {
    final directory = await getApplicationSupportDirectory();
    final executor = NativeDatabase.createInBackground(
      File('${directory.path}/pos_foundation.sqlite'),
    );
    try {
      await executor.ensureOpen(_FoundationSchema());
      final identifier = await storage.read(key: 'terminal_id');
      return identifier == null ? DeviceState.notActivated : DeviceState.activated;
    } finally {
      await executor.close();
    }
  }
}

class _FoundationSchema implements QueryExecutorUser {
  @override
  int get schemaVersion => 1;

  @override
  Future<void> beforeOpen(QueryExecutor executor, OpeningDetails details) async {
    await executor.runCustom('CREATE TABLE IF NOT EXISTS device_config (key TEXT PRIMARY KEY, value TEXT NOT NULL)');
    await executor.runCustom('CREATE TABLE IF NOT EXISTS auth_session (id TEXT PRIMARY KEY, updated_at TEXT NOT NULL)');
    await executor.runCustom('CREATE TABLE IF NOT EXISTS sync_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)');
  }
}

final deviceRepositoryProvider = Provider<DeviceRepository>(
  (ref) => DeviceRepository(const FlutterSecureStorage()),
);
final deviceStateProvider = FutureProvider<DeviceState>(
  (ref) => ref.read(deviceRepositoryProvider).load(),
);
final localeProvider = StateProvider<Locale>((ref) => const Locale('ar'));

String tr(BuildContext context, String ar, String en) =>
    Localizations.localeOf(context).languageCode == 'ar' ? ar : en;

void main() => runApp(const ProviderScope(child: PosApp()));

class PosApp extends ConsumerStatefulWidget {
  const PosApp({super.key});
  @override
  ConsumerState<PosApp> createState() => _PosAppState();
}

class _PosAppState extends ConsumerState<PosApp> {
  late final GoRouter router;
  @override
  void initState() {
    super.initState();
    router = GoRouter(routes: [
      GoRoute(path: '/', builder: (_, __) => const StartupScreen()),
      GoRoute(path: '/device', builder: (_, __) => const DeviceScreen()),
      GoRoute(path: '/login', builder: (_, __) => const LoginScreen()),
    ]);
  }

  @override
  void dispose() { router.dispose(); super.dispose(); }

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'Smart Merchant POS',
      locale: ref.watch(localeProvider),
      supportedLocales: const [Locale('ar'), Locale('en')],
      localizationsDelegates: const [GlobalMaterialLocalizations.delegate, GlobalWidgetsLocalizations.delegate, GlobalCupertinoLocalizations.delegate],
      routerConfig: router,
    );
  }
}

class StartupScreen extends ConsumerWidget {
  const StartupScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(deviceStateProvider);
    return Scaffold(
      appBar: AppBar(title: Text(tr(context, 'مساعد التاجر | POS', 'Smart Merchant | POS')),
        actions: [TextButton(onPressed: () => ref.read(localeProvider.notifier).state = Localizations.localeOf(context).languageCode == 'ar' ? const Locale('en') : const Locale('ar'), child: Text(tr(context, 'English', 'العربية')))]),
      body: Center(child: state.when(
        loading: () => const CircularProgressIndicator(),
        error: (_, __) => Text(tr(context, 'تعذّر تحميل إعدادات الجهاز · تحقق من الحالة المحلية', 'Could not load device settings · check offline state')),
        data: (value) => Column(mainAxisSize: MainAxisSize.min, children: [
          Text(value == DeviceState.activated ? tr(context, 'الجهاز مسجل', 'Device registered') : tr(context, 'الجهاز غير مفعل', 'Device not activated')),
          TextButton(onPressed: () => context.go(value == DeviceState.activated ? '/login' : '/device'), child: Text(tr(context, 'متابعة', 'Continue'))),
        ]),
      )),
    );
  }
}

class DeviceScreen extends StatelessWidget {
  const DeviceScreen({super.key});

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: Text(tr(context, 'حالة الجهاز', 'Device status'))),
    body: Center(child: Text(tr(context, 'تفعيل الجهاز يتم بواسطة مسؤول المنشأة. لا يمكن إتمام البيع قبل التفعيل.', 'An administrator must activate this device before checkout.'))),
  );
}

class LoginScreen extends StatelessWidget {
  const LoginScreen({super.key});

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: Text(tr(context, 'تسجيل الدخول', 'Sign in'))),
    body: Center(child: Text(tr(context, 'ربط جلسة الموظف بالجهاز في Sprint لاحق. حالة الاتصال: غير متصل.', 'Employee session linking follows in a later sprint. Offline status.'))),
  );
}
