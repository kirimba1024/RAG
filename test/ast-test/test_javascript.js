// User service for managing users
const { v4: uuidv4 } = require('uuid');

class UserService {
    constructor(dbUrl) {
        this.dbUrl = dbUrl;
        this.users = new Map();
    }
    
    createUser(name, age, email = null) {
        const user = {
            id: uuidv4(),
            name,
            age,
            email,
            createdAt: new Date()
        };
        this.users.set(user.id, user);
        return user;
    }
    
    getUser(userId) {
        return this.users.get(userId) || null;
    }
    
    getAllUsers() {
        return Array.from(this.users.values());
    }
}

// Factory function
function createUserService(dbUrl) {
    return new UserService(dbUrl);
}

// Export for Node.js
module.exports = { UserService, createUserService };

// ES6 export
export { UserService, createUserService };
