import 'dart:convert';

import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:smart_merchant_owner/main.dart';

void main() {
  setUp(() {
    FlutterSecureStorage.setMockInitialValues({
      'access_token': 'old-access-fixture',
      'refresh_token': 'old-refresh-fixture',
    });
  });

  testWidgets('resume renews expiry and an outage offers retry',
      (tester) async {
    final session = OwnerSession(const FlutterSecureStorage());
    var expired = false;
    var unavailable = false;
    var refreshes = 0;
    await http.runWithClient(
      () async {
        await tester.pumpWidget(ProviderScope(
          overrides: [sessionProvider.overrideWith((ref) => session)],
          child: const OwnerApp(),
        ));
        await tester.pumpAndSettle();
        expect(find.text('المنشأة: org-fixture'), findsOneWidget);
        unavailable = true;
        tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.paused);
        tester.binding
            .handleAppLifecycleStateChanged(AppLifecycleState.resumed);
        await tester.pumpAndSettle();
        expect(
            find.text('تعذر التحقق من الجلسة. أعد المحاولة.'), findsOneWidget);
        expect(session.accessToken, 'old-access-fixture');
        unavailable = false;
        await tester.tap(find.text('إعادة المحاولة'));
        await tester.pumpAndSettle();
        expect(find.text('تعذر التحقق من الجلسة. أعد المحاولة.'), findsNothing);
        expired = true;
        tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.paused);
        tester.binding
            .handleAppLifecycleStateChanged(AppLifecycleState.resumed);
        await tester.pumpAndSettle();
        expect(session.accessToken, 'new-access-fixture');
        expect(refreshes, 1);
        await tester.pumpWidget(const SizedBox());
      },
      () => MockClient((request) async {
        if (unavailable) {
          return http.Response('', 503);
        }
        if (request.url.path.endsWith('/refresh')) {
          refreshes++;
          return http.Response(
              jsonEncode({
                'access_token': 'new-access-fixture',
                'refresh_token': 'new-refresh-fixture',
              }),
              200);
        }
        if (expired &&
            request.headers['authorization'] == 'Bearer old-access-fixture') {
          return http.Response('', 401);
        }
        return http.Response(
            jsonEncode({
              'organizations': ['org-fixture']
            }),
            200);
      }),
    );
  });

  testWidgets('a new login replaces the rendered organization', (tester) async {
    final session = OwnerSession(const FlutterSecureStorage());
    await http.runWithClient(
      () async {
        await tester.pumpWidget(ProviderScope(
          overrides: [sessionProvider.overrideWith((ref) => session)],
          child: const OwnerApp(),
        ));
        await tester.pumpAndSettle();
        expect(find.text('المنشأة: alpha-fixture'), findsOneWidget);
        expect(await session.login('beta@example.test', 'fixture-password'),
            isTrue);
        await tester.pumpAndSettle();
        expect(find.text('المنشأة: beta-fixture'), findsOneWidget);
        expect(find.text('المنشأة: alpha-fixture'), findsNothing);
        await tester.pumpWidget(const SizedBox());
      },
      () => MockClient((request) async {
        if (request.url.path.endsWith('/login')) {
          return http.Response(
              jsonEncode({
                'access_token': 'beta-access-fixture',
                'refresh_token': 'beta-refresh-fixture',
              }),
              200);
        }
        final organization =
            request.headers['authorization'] == 'Bearer beta-access-fixture'
                ? 'beta-fixture'
                : 'alpha-fixture';
        return http.Response(
            jsonEncode({
              'organizations': [organization]
            }),
            200);
      }),
    );
  });
}
