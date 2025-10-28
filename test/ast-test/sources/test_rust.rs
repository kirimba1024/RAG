use std::collections::HashMap;
use uuid::Uuid;
use serde::{Deserialize, Serialize};

/// User represents a user in the system
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct User {
    pub id: String,
    pub name: String,
    pub age: u32,
    pub email: Option<String>,
    pub created_at: chrono::DateTime<chrono::Utc>,
}

/// UserService manages users
pub struct UserService {
    db_url: String,
    users: HashMap<String, User>,
}

impl UserService {
    /// Creates a new user service
    pub fn new(db_url: String) -> Self {
        Self {
            db_url,
            users: HashMap::new(),
        }
    }
    
    /// Creates a new user
    pub fn create_user(&mut self, name: String, age: u32, email: Option<String>) -> User {
        let user = User {
            id: Uuid::new_v4().to_string(),
            name,
            age,
            email,
            created_at: chrono::Utc::now(),
        };
        self.users.insert(user.id.clone(), user.clone());
        user
    }
    
    /// Gets a user by ID
    pub fn get_user(&self, user_id: &str) -> Option<&User> {
        self.users.get(user_id)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_create_user() {
        let mut service = UserService::new("sqlite://test.db".to_string());
        let user = service.create_user("Alice".to_string(), 30, None);
        assert_eq!(user.name, "Alice");
    }
}
