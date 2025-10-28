import Foundation

/// User represents a user in the system
struct User: Codable, Identifiable {
    let id: String
    let name: String
    let age: Int
    let email: String?
    let createdAt: Date
    
    init(name: String, age: Int, email: String? = nil) {
        self.id = UUID().uuidString
        self.name = name
        self.age = age
        self.email = email
        self.createdAt = Date()
    }
}

/// UserService manages users
class UserService: ObservableObject {
    private let dbURL: String
    @Published private(set) var users: [User] = []
    
    init(dbURL: String) {
        self.dbURL = dbURL
    }
    
    /// Creates a new user
    func createUser(name: String, age: Int, email: String? = nil) -> User {
        let user = User(name: name, age: age, email: email)
        users.append(user)
        return user
    }
    
    /// Gets a user by ID
    func getUser(id: String) -> User? {
        return users.first { $0.id == id }
    }
    
    /// Gets all users
    func getAllUsers() -> [User] {
        return users
    }
}

// Extension for additional functionality
extension UserService {
    func userCount() -> Int {
        return users.count
    }
    
    func usersOlderThan(_ age: Int) -> [User] {
        return users.filter { $0.age > age }
    }
}
