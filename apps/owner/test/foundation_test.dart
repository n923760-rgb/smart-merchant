import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:smart_merchant_owner/main.dart';

class FakeSession extends OwnerSession {
  FakeSession() : super(const FlutterSecureStorage());
  @override
  Future<void> restore() async {}
}

void main() {
  testWidgets('owner starts at login with Arabic direction', (tester) async {
    await tester.pumpWidget(ProviderScope(
        overrides: [sessionProvider.overrideWith((ref) => FakeSession())],
        child: const OwnerApp()));
    await tester.pumpAndSettle();
    expect(find.text('دخول'), findsOneWidget);
    expect(find.byType(MaterialApp), findsOneWidget);
    await tester.tap(find.text('English'));
    await tester.pumpAndSettle();
    expect(find.text('Sign in'), findsOneWidget);
  });
}
