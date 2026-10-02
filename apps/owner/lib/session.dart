import 'dart:async';
import 'dart:convert';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;

const apiUrl =
    String.fromEnvironment('API_URL', defaultValue: 'http://localhost:8000');

class OwnerSessionException implements Exception {
  const OwnerSessionException();
}

class OwnerSession extends StateNotifier<String?> {
  OwnerSession(this.storage) : super(null);
  final FlutterSecureStorage storage;
  Future<void> _tail = Future<void>.value();
  Future<void>? _restoring;
  int _epoch = 0;
  int get contextVersion => _epoch;
  String? get accessToken => state;

  // All credential reads, rotation and writes share one owner-isolate queue.
  Future<T> _serial<T>(Future<T> Function() operation) {
    final result = Completer<T>();
    _tail = _tail.then((_) async {
      try {
        result.complete(await operation());
      } catch (error, stack) {
        result.completeError(error, stack);
      }
    });
    return result.future;
  }

  Future<http.Response> _request(String path,
      {String? token, Map<String, String>? body}) async {
    final client = http.Client();
    try {
      final uri = Uri.parse('$apiUrl/api/v1/$path');
      final request = body == null
          ? client.get(uri, headers: {'Authorization': 'Bearer $token'})
          : client.post(uri,
              headers: {'Content-Type': 'application/json'},
              body: jsonEncode(body));
      return await request.timeout(const Duration(seconds: 10));
    } catch (_) {
      throw const OwnerSessionException();
    } finally {
      client.close();
    }
  }

  Map<String, dynamic> _object(http.Response response) {
    try {
      final data = jsonDecode(response.body);
      if (data is Map<String, dynamic>) {
        return data;
      }
    } catch (_) {
      // Do not expose raw response data or credentials.
    }
    throw const OwnerSessionException();
  }

  void _publish(String? token, int epoch) {
    if (mounted && epoch == _epoch) {
      state = token;
    }
  }

  Future<String> _save(http.Response response, int epoch) async {
    final data = _object(response);
    final access = data['access_token'];
    final refresh = data['refresh_token'];
    if (access is! String ||
        access.isEmpty ||
        refresh is! String ||
        refresh.isEmpty) {
      throw const OwnerSessionException();
    }
    // Persist a completed rotation even after logout intent, so the queued
    // logout revokes its successor. Only the current intent may publish it.
    await storage.write(key: 'access_token', value: access);
    await storage.write(key: 'refresh_token', value: refresh);
    _publish(access, epoch);
    return access;
  }

  Future<void> _clear(int epoch) async {
    await storage.deleteAll();
    _publish(null, epoch);
  }

  Future<String?> _refresh(int epoch) async {
    final refresh = await storage.read(key: 'refresh_token');
    if (refresh == null) {
      await _clear(epoch);
      return null;
    }
    final response =
        await _request('auth/refresh', body: {'refresh_token': refresh});
    if (response.statusCode == 401) {
      await _clear(epoch);
      return null;
    }
    if (response.statusCode != 200) {
      throw const OwnerSessionException();
    }
    return _save(response, epoch);
  }

  Future<Map<String, dynamic>?> _me(int epoch) async {
    var token = state ?? await storage.read(key: 'access_token');
    token ??= await _refresh(epoch);
    if (token == null) {
      return null;
    }
    var response = await _request('auth/me', token: token);
    if (response.statusCode == 401) {
      token = await _refresh(epoch);
      if (token == null) {
        return null;
      }
      response = await _request('auth/me', token: token);
    }
    if (response.statusCode == 401) {
      await _clear(epoch);
      return null;
    }
    if (response.statusCode != 200) {
      throw const OwnerSessionException();
    }
    final data = _object(response);
    final organizations = data['organizations'];
    if (organizations is! List ||
        organizations.any((value) => value is! String)) {
      throw const OwnerSessionException();
    }
    _publish(token, epoch);
    return epoch == _epoch ? data : null;
  }

  Future<void> restore() {
    final pending = _restoring;
    if (pending != null) {
      return pending;
    }
    final epoch = _epoch;
    final operation = _serial<void>(() async {
      if (epoch == _epoch) {
        await _me(epoch);
      }
    });
    late final Future<void> tracked;
    tracked = operation.whenComplete(() {
      if (identical(_restoring, tracked)) {
        _restoring = null;
      }
    });
    _restoring = tracked;
    return tracked;
  }

  Future<void> resume() => restore();

  Future<bool> login(String email, String password) {
    final epoch = ++_epoch;
    _publish(null, epoch);
    return _serial<bool>(() async {
      if (epoch != _epoch) {
        return false;
      }
      final response = await _request('auth/login',
          body: {'email': email, 'password': password});
      if (response.statusCode == 401) {
        return false;
      }
      if (response.statusCode != 200) {
        throw const OwnerSessionException();
      }
      await _save(response, epoch);
      return epoch == _epoch;
    });
  }

  Future<String?> organization() {
    final epoch = _epoch;
    return _serial<String?>(() async {
      if (epoch != _epoch) {
        return null;
      }
      final data = await _me(epoch);
      if (data == null) {
        return null;
      }
      final organizations = data['organizations'] as List<dynamic>;
      return organizations.isEmpty ? null : organizations.first as String;
    });
  }

  Future<void> logout() {
    final epoch = ++_epoch;
    _publish(null, epoch);
    return _serial<void>(() async {
      try {
        final refresh = await storage.read(key: 'refresh_token');
        if (refresh != null) {
          await _request('auth/logout', body: {'refresh_token': refresh});
        }
      } catch (_) {
        // Bounded best-effort revocation; local cleanup is still required.
      } finally {
        await _clear(epoch);
      }
    });
  }
}
