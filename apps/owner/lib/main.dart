import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:go_router/go_router.dart';
import 'package:http/http.dart' as http;

const apiUrl =
    String.fromEnvironment('API_URL', defaultValue: 'http://localhost:8000');

class OwnerSession extends StateNotifier<String?> {
  OwnerSession(this.storage) : super(null);
  final FlutterSecureStorage storage;

  Future<void> restore() async {
    final refreshToken = await storage.read(key: 'refresh_token');
    if (refreshToken == null) {
      return;
    }
    try {
      final response = await http.post(Uri.parse('$apiUrl/api/v1/auth/refresh'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({'refresh_token': refreshToken}));
      if (response.statusCode != 200) {
        await storage.deleteAll();
        return;
      }
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      await storage.write(
          key: 'access_token', value: data['access_token'] as String);
      await storage.write(
          key: 'refresh_token', value: data['refresh_token'] as String);
      state = data['access_token'] as String;
    } catch (_) {
      state = null;
    }
  }

  Future<bool> login(String email, String password) async {
    final response = await http.post(Uri.parse('$apiUrl/api/v1/auth/login'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'email': email, 'password': password}));
    if (response.statusCode != 200) {
      return false;
    }
    final data = jsonDecode(response.body) as Map<String, dynamic>;
    await storage.write(
        key: 'access_token', value: data['access_token'] as String);
    await storage.write(
        key: 'refresh_token', value: data['refresh_token'] as String);
    state = data['access_token'] as String;
    return true;
  }

  Future<String?> organization() async {
    if (state == null) {
      return null;
    }
    final response = await http.get(Uri.parse('$apiUrl/api/v1/auth/me'),
        headers: {'Authorization': 'Bearer $state'});
    if (response.statusCode != 200) {
      return null;
    }
    final organizations = (jsonDecode(response.body)
        as Map<String, dynamic>)['organizations'] as List<dynamic>;
    return organizations.isEmpty ? null : organizations.first as String;
  }

  Future<void> logout() async {
    final refresh = await storage.read(key: 'refresh_token');
    if (refresh != null && state != null) {
      try {
        await http.post(Uri.parse('$apiUrl/api/v1/auth/logout'),
            headers: {
              'Authorization': 'Bearer $state',
              'Content-Type': 'application/json'
            },
            body: jsonEncode({'refresh_token': refresh}));
      } catch (_) {/* Local logout still clears credentials. */}
    }
    await storage.deleteAll();
    state = null;
  }
}

final sessionProvider = StateNotifierProvider<OwnerSession, String?>(
  (ref) => OwnerSession(const FlutterSecureStorage()),
);
final localeProvider = StateProvider<Locale>((ref) => const Locale('ar'));
String tr(BuildContext context, String ar, String en) =>
    Localizations.localeOf(context).languageCode == 'ar' ? ar : en;

void main() => runApp(const ProviderScope(child: OwnerApp()));

class OwnerApp extends ConsumerStatefulWidget {
  const OwnerApp({super.key});
  @override
  ConsumerState<OwnerApp> createState() => _OwnerAppState();
}

class _OwnerAppState extends ConsumerState<OwnerApp> {
  late final GoRouter router;
  @override
  void initState() {
    super.initState();
    router = GoRouter(routes: [
      GoRoute(path: '/', builder: (_, __) => const LoginScreen()),
      GoRoute(path: '/home', builder: (_, __) => const HomeScreen()),
      GoRoute(path: '/account', builder: (_, __) => const AccountScreen()),
    ]);
    Future.microtask(() => ref.read(sessionProvider.notifier).restore());
  }

  @override
  void dispose() {
    router.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'Smart Merchant Owner',
      locale: ref.watch(localeProvider),
      supportedLocales: const [Locale('ar'), Locale('en')],
      localizationsDelegates: const [
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate
      ],
      routerConfig: router,
    );
  }
}

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});
  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final email = TextEditingController();
  final password = TextEditingController();
  String? error;

  @override
  void dispose() {
    email.dispose();
    password.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final session = ref.watch(sessionProvider);
    if (session != null) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (context.mounted) {
          context.go('/home');
        }
      });
    }
    return Scaffold(
      appBar: AppBar(
          title: Text(tr(context, 'مساعد التاجر', 'Smart Merchant')),
          actions: [
            TextButton(
                onPressed: () => ref.read(localeProvider.notifier).state =
                    Localizations.localeOf(context).languageCode == 'ar'
                        ? const Locale('en')
                        : const Locale('ar'),
                child: Text(tr(context, 'English', 'العربية')))
          ]),
      body: Center(
          child: SizedBox(
              width: 320,
              child: Column(mainAxisSize: MainAxisSize.min, children: [
                TextField(
                    controller: email,
                    decoration: InputDecoration(
                        labelText: tr(context, 'البريد الإلكتروني', 'Email'))),
                TextField(
                    controller: password,
                    obscureText: true,
                    decoration: InputDecoration(
                        labelText: tr(context, 'كلمة المرور', 'Password'))),
                if (error != null)
                  Text(error!, style: const TextStyle(color: Colors.red)),
                ElevatedButton(
                    onPressed: () async {
                      try {
                        final success = await ref
                            .read(sessionProvider.notifier)
                            .login(email.text, password.text);
                        if (!context.mounted) {
                          return;
                        }
                        if (success) {
                          context.go('/home');
                        } else {
                          setState(() => error =
                              tr(context, 'تعذر الدخول', 'Sign-in failed'));
                        }
                      } catch (_) {
                        if (context.mounted) {
                          setState(() => error =
                              tr(context, 'تعذر الاتصال', 'Connection failed'));
                        }
                      }
                    },
                    child: Text(tr(context, 'دخول', 'Sign in'))),
              ]))),
    );
  }
}

class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final token = ref.watch(sessionProvider);
    if (token == null) {
      return const LoginScreen();
    }
    return Scaffold(
      appBar: AppBar(title: Text(tr(context, 'المنشأة', 'Organization'))),
      body: FutureBuilder<String?>(
          future: ref.read(sessionProvider.notifier).organization(),
          builder: (context, snapshot) => Center(
              child: Text(snapshot.data == null
                  ? tr(context, 'جارٍ تحميل المنشأة...',
                      'Loading organization...')
                  : '${tr(context, 'المنشأة', 'Organization')}: ${snapshot.data}'))),
      bottomNavigationBar: TextButton(
          onPressed: () => context.go('/account'),
          child: Text(tr(context, 'الحساب', 'Account'))),
    );
  }
}

class AccountScreen extends ConsumerWidget {
  const AccountScreen({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) => Scaffold(
        appBar: AppBar(title: Text(tr(context, 'حسابي', 'Account'))),
        body: Center(
            child: ElevatedButton(
                onPressed: () async {
                  await ref.read(sessionProvider.notifier).logout();
                  if (context.mounted) {
                    context.go('/');
                  }
                },
                child: Text(tr(context, 'تسجيل خروج', 'Sign out')))),
      );
}
