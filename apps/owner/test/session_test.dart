import 'dart:async';
import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:smart_merchant_owner/main.dart';

http.Response me() => http.Response(
    jsonEncode({
      'organizations': ['org-fixture']
    }),
    200);

http.Response pair() => http.Response(
    jsonEncode({
      'access_token': 'new-access-fixture',
      'refresh_token': 'new-refresh-fixture',
    }),
    200);

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  const storage = FlutterSecureStorage();

  setUp(() {
    FlutterSecureStorage.setMockInitialValues({
      'access_token': 'old-access-fixture',
      'refresh_token': 'old-refresh-fixture',
    });
  });

  test('cold restore probes valid access without rotating', () async {
    final session = OwnerSession(storage);
    final paths = <String>[];
    await http.runWithClient(
      () => session.restore(),
      () => MockClient((request) async {
        paths.add(request.url.path);
        expect(request.headers['authorization'], 'Bearer old-access-fixture');
        return me();
      }),
    );
    expect(paths, ['/api/v1/auth/me']);
    expect(session.accessToken, 'old-access-fixture');
    session.dispose();
  });

  test('concurrent organization reads rotate expired access once', () async {
    final session = OwnerSession(storage);
    var refreshes = 0;
    final access = <String?>[];
    await http.runWithClient(
      () async {
        final results =
            await Future.wait([session.organization(), session.organization()]);
        expect(results, ['org-fixture', 'org-fixture']);
      },
      () => MockClient((request) async {
        if (request.url.path.endsWith('/refresh')) {
          refreshes++;
          expect(jsonDecode(request.body),
              {'refresh_token': 'old-refresh-fixture'});
          return pair();
        }
        access.add(request.headers['authorization']);
        return request.headers['authorization'] == 'Bearer old-access-fixture'
            ? http.Response('', 401)
            : me();
      }),
    );
    expect(refreshes, 1);
    expect(access, [
      'Bearer old-access-fixture',
      'Bearer new-access-fixture',
      'Bearer new-access-fixture',
    ]);
    expect(await storage.read(key: 'refresh_token'), 'new-refresh-fixture');
    session.dispose();
  });

  test('startup and resumed checks share the in-flight probe', () async {
    final session = OwnerSession(storage);
    final response = Completer<http.Response>();
    final started = Completer<void>();
    var calls = 0;
    await http.runWithClient(
      () async {
        final first = session.restore();
        await started.future;
        final resumed = session.resume();
        response.complete(me());
        await Future.wait([first, resumed]);
      },
      () => MockClient((_) {
        calls++;
        started.complete();
        return response.future;
      }),
    );
    expect(calls, 1);
    session.dispose();
  });

  test('resume rechecks access and renews only after explicit 401', () async {
    final session = OwnerSession(storage);
    var expired = false;
    var refreshes = 0;
    await http.runWithClient(
      () async {
        await session.restore();
        expired = true;
        await session.resume();
      },
      () => MockClient((request) async {
        if (request.url.path.endsWith('/refresh')) {
          refreshes++;
          return pair();
        }
        return expired &&
                request.headers['authorization'] == 'Bearer old-access-fixture'
            ? http.Response('', 401)
            : me();
      }),
    );
    expect(refreshes, 1);
    expect(session.accessToken, 'new-access-fixture');
    session.dispose();
  });

  test('rejected refresh clears credentials and stops after one attempt',
      () async {
    final session = OwnerSession(storage);
    final paths = <String>[];
    await http.runWithClient(
      () => session.restore(),
      () => MockClient((request) async {
        paths.add(request.url.path);
        return http.Response('', 401);
      }),
    );
    expect(paths, ['/api/v1/auth/me', '/api/v1/auth/refresh']);
    expect(session.accessToken, isNull);
    expect(await storage.read(key: 'refresh_token'), isNull);
    session.dispose();
  });

  test('service failure preserves credentials and permits a later retry',
      () async {
    final session = OwnerSession(storage);
    var unavailable = true;
    var calls = 0;
    await http.runWithClient(
      () async {
        await expectLater(
            session.restore(), throwsA(isA<OwnerSessionException>()));
        expect(await storage.read(key: 'refresh_token'), 'old-refresh-fixture');
        unavailable = false;
        await session.resume();
      },
      () => MockClient((_) async {
        calls++;
        return unavailable ? http.Response('', 503) : me();
      }),
    );
    expect(calls, 2);
    expect(session.accessToken, 'old-access-fixture');
    session.dispose();
  });

  test('malformed rotation never writes a partial pair', () async {
    final session = OwnerSession(storage);
    await http.runWithClient(
      () =>
          expectLater(session.restore(), throwsA(isA<OwnerSessionException>())),
      () => MockClient((request) async => request.url.path.endsWith('/refresh')
          ? http.Response('{"access_token":"incomplete-fixture"}', 200)
          : http.Response('', 401)),
    );
    expect(await storage.read(key: 'access_token'), 'old-access-fixture');
    expect(await storage.read(key: 'refresh_token'), 'old-refresh-fixture');
    session.dispose();
  });

  test('logout waits for rotation and revokes its persisted successor',
      () async {
    final session = OwnerSession(storage);
    final rotating = Completer<void>();
    final rotation = Completer<http.Response>();
    final revoked = <String>[];
    await http.runWithClient(
      () async {
        final restore = session.restore();
        await rotating.future;
        final logout = session.logout();
        expect(session.accessToken, isNull);
        rotation.complete(pair());
        await Future.wait([restore, logout]);
      },
      () => MockClient((request) async {
        if (request.url.path.endsWith('/refresh')) {
          rotating.complete();
          return rotation.future;
        }
        if (request.url.path.endsWith('/logout')) {
          revoked.add(jsonDecode(request.body)['refresh_token'] as String);
          return http.Response('', 204);
        }
        return request.headers['authorization'] == 'Bearer old-access-fixture'
            ? http.Response('', 401)
            : me();
      }),
    );
    expect(revoked, ['new-refresh-fixture']);
    expect(session.accessToken, isNull);
    expect(await storage.read(key: 'refresh_token'), isNull);
    session.dispose();
  });

  test('an organization response after logout intent is discarded', () async {
    final session = OwnerSession(storage);
    final started = Completer<void>();
    final response = Completer<http.Response>();
    await http.runWithClient(
      () async {
        final organization = session.organization();
        await started.future;
        final logout = session.logout();
        response.complete(me());
        expect(await organization, isNull);
        await logout;
      },
      () => MockClient((request) async {
        if (request.url.path.endsWith('/logout')) {
          return http.Response('', 204);
        }
        started.complete();
        return response.future;
      }),
    );
    expect(session.accessToken, isNull);
    session.dispose();
  });

  test('refresh-only storage can restore without an access credential',
      () async {
    FlutterSecureStorage.setMockInitialValues({
      'refresh_token': 'old-refresh-fixture',
    });
    final session = OwnerSession(storage);
    final paths = <String>[];
    await http.runWithClient(
      () => session.restore(),
      () => MockClient((request) async {
        paths.add(request.url.path);
        return request.url.path.endsWith('/refresh') ? pair() : me();
      }),
    );
    expect(paths, ['/api/v1/auth/refresh', '/api/v1/auth/me']);
    expect(session.accessToken, 'new-access-fixture');
    session.dispose();
  });

  for (final refreshOnly in [false, true]) {
    test('a rejected renewed access stops after one rotation: $refreshOnly',
        () async {
      if (refreshOnly) {
        FlutterSecureStorage.setMockInitialValues({
          'refresh_token': 'old-refresh-fixture',
        });
      }
      final session = OwnerSession(storage);
      var refreshes = 0;
      await http.runWithClient(
        () => session.restore(),
        () => MockClient((request) async {
          if (request.url.path.endsWith('/refresh')) {
            refreshes++;
            return pair();
          }
          return http.Response('', 401);
        }),
      );
      expect(refreshes, 1);
      expect(session.accessToken, isNull);
      expect(await storage.read(key: 'refresh_token'), isNull);
      session.dispose();
    });
  }

  testWidgets('timeout releases the session queue without replay',
      (tester) async {
    final session = OwnerSession(storage);
    final stalled = Completer<http.Response>();
    var requests = 0;
    await http.runWithClient(
      () async {
        final restoring = expectLater(
            session.restore(), throwsA(isA<OwnerSessionException>()));
        await tester.pump();
        final logout = session.logout();
        await tester.pump(const Duration(seconds: 10));
        await restoring;
        await logout;
      },
      () => MockClient((request) {
        requests++;
        return request.url.path.endsWith('/logout')
            ? Future.value(http.Response('', 204))
            : stalled.future;
      }),
    );
    expect(requests, 2);
    expect(await storage.read(key: 'refresh_token'), isNull);
    stalled.complete(me());
    await tester.pump();
    expect(session.accessToken, isNull);
    session.dispose();
  });
}
