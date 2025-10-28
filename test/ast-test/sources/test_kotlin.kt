package com.example.rag.userservice

import java.time.LocalDateTime
import java.util.*

/**
 * User represents a user in the system
 */
data class User(
    val id: String = UUID.randomUUID().toString(),
    val name: String,
    val age: Int,
    val email: String? = null,
    val createdAt: LocalDateTime = LocalDateTime.now()
) {
    fun isValid(): Boolean = name.isNotBlank() && age > 0
}

/**
 * UserService manages users
 */
class UserService(private val dbUrl: String) {
    private val users = mutableListOf<User>()
    
    /**
     * Creates a new user
     */
    fun createUser(name: String, age: Int, email: String? = null): User {
        val user = User(name = name, age = age, email = email)
        users.add(user)
        return user
    }
    
    /**
     * Gets a user by ID
     */
    fun getUser(userId: String): User? {
        return users.find { it.id == userId }
    }
    
    /**
     * Gets all users
     */
    fun getAllUsers(): List<User> {
        return users.toList()
    }
    
    /**
     * Gets user count
     */
    fun getUserCount(): Int = users.size
}

// Extension functions
fun UserService.getUsersOlderThan(age: Int): List<User> {
    return users.filter { it.age > age }
}
