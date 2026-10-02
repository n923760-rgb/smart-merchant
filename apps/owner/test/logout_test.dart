import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:smart_merchant_owner/main.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    FlutterSecureStorage.setMockInitialValues({
      'refresh_token': 'logout-refresh-fixture',
      'access_token': 'expired-access-fixture',
    });
  });

  test('logout revokes refresh even without in-memory access', () async {
    const storage = FlutterSecureStorage();
    final session = OwnerSession(storage);
    final requests = <http.Request>[];
    await http.runWithClient(
      () => session.logout(),
      () => MockClient((request) async {
        requests.add(request);
        return http.Response('', 204);
      }),
    );
    expect(requests, hasLength(1));
    expect(requests.single.url.path, '/api/v1/auth/logout');
    expect(jsonDecode(requests.single.body), {
      'refresh_token': 'logout-refresh-fixture',
    });
    expect(requests.single.headers.containsKey('authorization'), isFalse);
    expect(await storage.read(key: 'refresh_token'), isNull);
    expect(await storage.read(key: 'access_token'), isNull);
    session.dispose();
  });

  test('logout clears local credentials if revocation is unreachable', () async {
    const storage = FlutterSecureStorage();
    final session = OwnerSession(storage);
    await http.runWithClient(
      () => session.logout(),
      () => MockClient((_) async => throw Exception('fixture offline')),
    );
    expect(await storage.read(key: 'refresh_token'), isNull);
    expect(await storage.read(key: 'access_token'), isNull);
    session.dispose();
  });
}
