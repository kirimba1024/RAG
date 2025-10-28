package com.example.rag.userservice

import java.time.LocalDateTime
import java.util.UUID

/**
 * User represents a user in the system
 */
class User {
    String id
    String name
    Integer age
    String email
    LocalDateTime createdAt
    
    User(String name, Integer age, String email = null) {
        this.id = UUID.randomUUID().toString()
        this.name = name
        this.age = age
        this.email = email
        this.createdAt = LocalDateTime.now()
    }
    
    boolean isValid() {
        return name && !name.empty && age > 0
    }
    
    @Override
    String toString() {
        return "User(id=${id}, name=${name}, age=${age})"
    }
}

/**
 * UserService manages users
 */
class UserService {
    String dbUrl
    List<User> users = []
    
    UserService(String dbUrl) {
        this.dbUrl = dbUrl
    }
    
    /**
     * Creates a new user
     */
    User createUser(String name, Integer age, String email = null) {
        User user = new User(name, age, email)
        users << user
        return user
    }
    
    /**
     * Gets a user by ID
     */
    User getUser(String userId) {
        return users.find { it.id == userId }
    }
    
    /**
     * Gets all users
     */
    List<User> getAllUsers() {
        return users.clone()
    }
    
    /**
     * Gets user count
     */
    Integer getUserCount() {
        return users.size()
    }
}
