// User service for managing users in Dart
import 'dart:convert';
import 'dart:math';

/// User class representing a user in the system
class User {
  final String id;
  final String name;
  final int age;
  final String? email;
  final DateTime createdAt;

  User({
    required this.name,
    required this.age,
    this.email,
  }) : id = _generateId(),
       createdAt = DateTime.now();

  static String _generateId() {
    return 'user_${Random().nextInt(1000000)}';
  }

  /// Checks if the user is valid
  bool isValid() {
    return name.isNotEmpty && age > 0;
  }

  /// Converts user to JSON
  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'age': age,
      'email': email,
      'createdAt': createdAt.toIso8601String(),
    };
  }

  /// Creates user from JSON
  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      name: json['name'],
      age: json['age'],
      email: json['email'],
    );
  }

  @override
  String toString() {
    return 'User(id: $id, name: $name, age: $age)';
  }
}

/// UserService class for managing users
class UserService {
  final String dbUrl;
  final List<User> _users = [];

  UserService(this.dbUrl);

  /// Creates a new user
  User createUser(String name, int age, {String? email}) {
    final user = User(name: name, age: age, email: email);
    _users.add(user);
    return user;
  }

  /// Gets a user by ID
  User? getUser(String userId) {
    try {
      return _users.firstWhere((user) => user.id == userId);
    } catch (e) {
      return null;
    }
  }

  /// Gets all users
  List<User> getAllUsers() {
    return List.unmodifiable(_users);
  }

  /// Gets user count
  int getUserCount() {
    return _users.length;
  }

  /// Gets users older than specified age
  List<User> getUsersOlderThan(int age) {
    return _users.where((user) => user.age > age).toList();
  }

  /// Removes a user by ID
  bool removeUser(String userId) {
    final index = _users.indexWhere((user) => user.id == userId);
    if (index != -1) {
      _users.removeAt(index);
      return true;
    }
    return false;
  }

  /// Exports users to JSON
  String exportToJson() {
    final usersJson = _users.map((user) => user.toJson()).toList();
    return jsonEncode(usersJson);
  }

  /// Imports users from JSON
  void importFromJson(String jsonString) {
    final List<dynamic> usersList = jsonDecode(jsonString);
    for (final userJson in usersList) {
      final user = User.fromJson(userJson);
      _users.add(user);
    }
  }
}

/// Extension methods for UserService
extension UserServiceExtensions on UserService {
  /// Gets average age of all users
  double getAverageAge() {
    if (_users.isEmpty) return 0.0;
    final totalAge = _users.fold(0, (sum, user) => sum + user.age);
    return totalAge / _users.length;
  }

  /// Gets users by name pattern
  List<User> searchUsersByName(String pattern) {
    return _users
        .where((user) => user.name.toLowerCase().contains(pattern.toLowerCase()))
        .toList();
  }
}

/// Main function for testing
void main() {
  final service = UserService('sqlite://test.db');
  
  // Create test users
  final user1 = service.createUser('Alice', 30, email: 'alice@example.com');
  final user2 = service.createUser('Bob', 25, email: 'bob@example.com');
  
  print('Created users:');
  print(user1);
  print(user2);
  
  print('Total users: ${service.getUserCount()}');
  print('Average age: ${service.getAverageAge()}');
  
  // Search users
  final searchResults = service.searchUsersByName('alice');
  print('Search results: $searchResults');
}
