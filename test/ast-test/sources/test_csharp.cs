using System;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;

namespace RAG.UserService
{
    /// <summary>
    /// Represents a user in the system
    /// </summary>
    public class User
    {
        [Key]
        public string Id { get; set; } = Guid.NewGuid().ToString();
        
        [Required]
        public string Name { get; set; }
        
        [Range(0, 150)]
        public int Age { get; set; }
        
        [EmailAddress]
        public string? Email { get; set; }
        
        public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    }

    /// <summary>
    /// Service for managing users
    /// </summary>
    public class UserService
    {
        private readonly string _dbUrl;
        private readonly List<User> _users;

        public UserService(string dbUrl)
        {
            _dbUrl = dbUrl;
            _users = new List<User>();
        }

        /// <summary>
        /// Creates a new user
        /// </summary>
        public User CreateUser(string name, int age, string? email = null)
        {
            var user = new User
            {
                Name = name,
                Age = age,
                Email = email
            };
            _users.Add(user);
            return user;
        }

        /// <summary>
        /// Gets a user by ID
        /// </summary>
        public User? GetUser(string userId)
        {
            return _users.Find(u => u.Id == userId);
        }

        /// <summary>
        /// Gets all users
        /// </summary>
        public IEnumerable<User> GetAllUsers()
        {
            return _users.AsReadOnly();
        }
    }
}
