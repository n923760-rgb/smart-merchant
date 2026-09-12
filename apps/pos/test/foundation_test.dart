import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:smart_merchant_pos/main.dart';

void main() {
  testWidgets('unactivated device starts safely', (tester) async {
    await tester.pumpWidget(ProviderScope(
      overrides: [deviceStateProvider.overrideWith((ref) async => DeviceState.notActivated)],
      child: const PosApp(),
    ));
    await tester.pumpAndSettle();
    expect(find.text('الجهاز غير مفعل'), findsOneWidget);
    expect(find.byType(MaterialApp), findsOneWidget);
    await tester.tap(find.text('English'));
    await tester.pumpAndSettle();
    expect(find.text('Device not activated'), findsOneWidget);
  });
}
