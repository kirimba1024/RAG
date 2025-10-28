package main

import (
	"fmt"
	"time"
	"github.com/google/uuid"
)

// User represents a user in the system
type User struct {
	ID        string    `json:"id"`
	Name      string    `json:"name"`
	Age       int       `json:"age"`
	Email     *string   `json:"email,omitempty"`
	CreatedAt time.Time `json:"created_at"`
}

// UserService manages users
type UserService struct {
	dbURL string
	users map[string]*User
}

// NewUserService creates a new user service
func NewUserService(dbURL string) *UserService {
	return &UserService{
		dbURL: dbURL,
		users: make(map[string]*User),
	}
}

// CreateUser creates a new user
func (s *UserService) CreateUser(name string, age int, email *string) *User {
	user := &User{
		ID:        uuid.New().String(),
		Name:      name,
		Age:       age,
		Email:     email,
		CreatedAt: time.Now(),
	}
	s.users[user.ID] = user
	return user
}

// GetUser retrieves a user by ID
func (s *UserService) GetUser(userID string) (*User, bool) {
	user, exists := s.users[userID]
	return user, exists
}

func main() {
	service := NewUserService("postgres://localhost:5432/test")
	user := service.CreateUser("Alice", 30, nil)
	fmt.Printf("Created user: %+v\n", user)
}
