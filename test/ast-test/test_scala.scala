package com.example.rag.userservice

import java.time.LocalDateTime
import java.util.UUID
import scala.collection.mutable.ListBuffer

/**
 * User represents a user in the system
 */
case class User(
  id: String = UUID.randomUUID().toString,
  name: String,
  age: Int,
  email: Option[String] = None,
  createdAt: LocalDateTime = LocalDateTime.now()
) {
  def isValid: Boolean = name.nonEmpty && age > 0
}

/**
 * UserService manages users
 */
class UserService(dbUrl: String) {
  private val users: ListBuffer[User] = ListBuffer.empty[User]
  
  /**
   * Creates a new user
   */
  def createUser(name: String, age: Int, email: Option[String] = None): User = {
    val user = User(name = name, age = age, email = email)
    users += user
    user
  }
  
  /**
   * Gets a user by ID
   */
  def getUser(userId: String): Option[User] = {
    users.find(_.id == userId)
  }
  
  /**
   * Gets all users
   */
  def getAllUsers: List[User] = users.toList
  
  /**
   * Gets user count
   */
  def getUserCount: Int = users.length
}

// Companion object with factory methods
object UserService {
  def apply(dbUrl: String): UserService = new UserService(dbUrl)
}
