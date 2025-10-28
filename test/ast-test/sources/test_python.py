#!/usr/bin/env python3
"""
Test Python file for AST extraction
"""

import os
import sys
from typing import List, Dict, Optional
from dataclasses import dataclass

@dataclass
class User:
    name: str
    age: int
    email: Optional[str] = None

class UserService:
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.users: List[User] = []
    
    def create_user(self, name: str, age: int, email: str = None) -> User:
        """Create a new user"""
        user = User(name=name, age=age, email=email)
        self.users.append(user)
        return user
    
    def get_user(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        if 0 <= user_id < len(self.users):
            return self.users[user_id]
        return None

def main():
    service = UserService("sqlite:///test.db")
    user = service.create_user("Alice", 30, "alice@example.com")
    print(f"Created user: {user}")

if __name__ == "__main__":
    main()
