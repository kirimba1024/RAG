package com.example.rag;

import java.util.*;
import java.time.LocalDateTime;

/**
 * User service for managing users
 */
public class UserService {
    private final String dbUrl;
    private final List<User> users;
    
    public UserService(String dbUrl) {
        this.dbUrl = dbUrl;
        this.users = new ArrayList<>();
    }
    
    public User createUser(String name, int age, String email) {
        User user = new User(name, age, email);
        users.add(user);
        return user;
    }
    
    public Optional<User> getUser(int userId) {
        if (userId >= 0 && userId < users.size()) {
            return Optional.of(users.get(userId));
        }
        return Optional.empty();
    }
}

class User {
    private String name;
    private int age;
    private String email;
    private LocalDateTime createdAt;
    
    public User(String name, int age, String email) {
        this.name = name;
        this.age = age;
        this.email = email;
        this.createdAt = LocalDateTime.now();
    }
    
    // Getters and setters
    public String getName() { return name; }
    public int getAge() { return age; }
    public String getEmail() { return email; }
}
