#include <iostream>
#include <string>
#include <vector>
#include <memory>
#include <chrono>

namespace rag {
namespace user {

class User {
private:
    std::string id;
    std::string name;
    int age;
    std::string email;
    std::chrono::system_clock::time_point created_at;

public:
    User(const std::string& name, int age, const std::string& email = "")
        : name(name), age(age), email(email) {
        id = generateId();
        created_at = std::chrono::system_clock::now();
    }
    
    const std::string& getId() const { return id; }
    const std::string& getName() const { return name; }
    int getAge() const { return age; }
    const std::string& getEmail() const { return email; }
    
private:
    std::string generateId() {
        return "user_" + std::to_string(std::rand());
    }
};

class UserService {
private:
    std::string db_url;
    std::vector<std::unique_ptr<User>> users;

public:
    UserService(const std::string& db_url) : db_url(db_url) {}
    
    User* createUser(const std::string& name, int age, const std::string& email = "") {
        auto user = std::make_unique<User>(name, age, email);
        User* user_ptr = user.get();
        users.push_back(std::move(user));
        return user_ptr;
    }
    
    User* getUser(size_t index) {
        if (index < users.size()) {
            return users[index].get();
        }
        return nullptr;
    }
};

} // namespace user
} // namespace rag

int main() {
    rag::user::UserService service("sqlite://test.db");
    auto* user = service.createUser("Alice", 30, "alice@example.com");
    std::cout << "Created user: " << user->getName() << std::endl;
    return 0;
}
