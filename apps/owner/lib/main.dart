import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:go_router/go_router.dart';
import 'session.dart';

export 'session.dart';

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

class _OwnerAppState extends ConsumerState<OwnerApp>
    with WidgetsBindingObserver {
  late final GoRouter router;
  bool sessionUnavailable = false;

  Future<void> checkSession() async {
    final session = ref.read(sessionProvider.notifier);
    final epoch = session.contextVersion;
    try {
      await session.resume();
      if (mounted && epoch == session.contextVersion) {
        setState(() => sessionUnavailable = false);
      }
    } catch (_) {
      if (mounted && epoch == session.contextVersion) {
        setState(() => sessionUnavailable = true);
      }
    }
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      checkSession();
    }
  }
  @override
  void initState() {
    super.initState();
    router = GoRouter(routes: [
      GoRoute(path: '/', builder: (_, __) => const LoginScreen()),
      GoRoute(path: '/home', builder: (_, __) => const HomeScreen()),
      GoRoute(path: '/account', builder: (_, __) => const AccountScreen()),
    ]);
    WidgetsBinding.instance.addObserver(this);
    Future.microtask(checkSession);
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
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
      builder: (context, child) => Column(children: [
        if (sessionUnavailable)
          MaterialBanner(
            content: Text(tr(context, 'تعذر التحقق من الجلسة. أعد المحاولة.',
                'Session unavailable. Try again.')),
            actions: [
              TextButton(
                onPressed: checkSession,
                child: Text(tr(context, 'إعادة المحاولة', 'Retry')),
              ),
            ],
          ),
        Expanded(child: child!),
      ]),
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

class HomeScreen extends ConsumerStatefulWidget {
  const HomeScreen({super.key});
  @override
  ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends ConsumerState<HomeScreen> {
  Future<String?>? organization;
  int? loadedContext;

  @override
  Widget build(BuildContext context) {
    final token = ref.watch(sessionProvider);
    if (token == null) {
      organization = null;
      return const LoginScreen();
    }
    final currentContext = ref.read(sessionProvider.notifier).contextVersion;
    if (loadedContext != currentContext) {
      organization = null;
      loadedContext = currentContext;
    }
    organization ??= ref.read(sessionProvider.notifier).organization();
    return Scaffold(
      appBar: AppBar(title: Text(tr(context, 'المنشأة', 'Organization'))),
      body: FutureBuilder<String?>(
        future: organization,
        builder: (context, snapshot) {
          if (snapshot.hasError) {
            return Center(
              child: Column(mainAxisSize: MainAxisSize.min, children: [
                Text(tr(context, 'تعذر تحميل المنشأة', 'Organization unavailable')),
                TextButton(
                  onPressed: () => setState(() {
                    organization =
                        ref.read(sessionProvider.notifier).organization();
                  }),
                  child: Text(tr(context, 'إعادة المحاولة', 'Retry')),
                ),
              ]),
            );
          }
          return Center(
            child: Text(snapshot.connectionState != ConnectionState.done
                ? tr(context, 'جارٍ تحميل المنشأة...', 'Loading organization...')
                : snapshot.data == null
                    ? tr(context, 'لا توجد منشأة متاحة', 'No organization available')
                    : '${tr(context, 'المنشأة', 'Organization')}: ${snapshot.data}'),
          );
        },
      ),
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
