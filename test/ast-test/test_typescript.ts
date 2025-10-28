// User service for managing users
import { v4 as uuidv4 } from 'uuid';

interface User {
    id: string;
    name: string;
    age: number;
    email?: string;
    createdAt: Date;
}

interface UserServiceConfig {
    dbUrl: string;
    maxUsers?: number;
}

class UserService {
    private dbUrl: string;
    private users: Map<string, User>;
    private maxUsers: number;
    
    constructor(config: UserServiceConfig) {
        this.dbUrl = config.dbUrl;
        this.users = new Map();
        this.maxUsers = config.maxUsers || 1000;
    }
    
    createUser(name: string, age: number, email?: string): User {
        const user: User = {
            id: uuidv4(),
            name,
            age,
            email,
            createdAt: new Date()
        };
        this.users.set(user.id, user);
        return user;
    }
    
    getUser(userId: string): User | null {
        return this.users.get(userId) || null;
    }
    
    getAllUsers(): User[] {
        return Array.from(this.users.values());
    }
}

// Factory function
export function createUserService(config: UserServiceConfig): UserService {
    return new UserService(config);
}

export { UserService, type User, type UserServiceConfig };
