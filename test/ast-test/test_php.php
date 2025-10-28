<?php

namespace RAG\UserService;

use DateTime;
use InvalidArgumentException;

/**
 * User represents a user in the system
 */
class User
{
    private string $id;
    private string $name;
    private int $age;
    private ?string $email;
    private DateTime $createdAt;

    public function __construct(string $name, int $age, ?string $email = null)
    {
        $this->id = uniqid('user_', true);
        $this->name = $name;
        $this->age = $age;
        $this->email = $email;
        $this->createdAt = new DateTime();
    }

    public function getId(): string
    {
        return $this->id;
    }

    public function getName(): string
    {
        return $this->name;
    }

    public function getAge(): int
    {
        return $this->age;
    }

    public function getEmail(): ?string
    {
        return $this->email;
    }

    public function getCreatedAt(): DateTime
    {
        return $this->createdAt;
    }
}

/**
 * UserService manages users
 */
class UserService
{
    private string $dbUrl;
    private array $users = [];

    public function __construct(string $dbUrl)
    {
        $this->dbUrl = $dbUrl;
    }

    public function createUser(string $name, int $age, ?string $email = null): User
    {
        $user = new User($name, $age, $email);
        $this->users[] = $user;
        return $user;
    }

    public function getUser(int $userId): ?User
    {
        return $this->users[$userId] ?? null;
    }

    public function getAllUsers(): array
    {
        return $this->users;
    }
}
