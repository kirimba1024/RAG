-- User service for managing users in Lua

local User = {}
User.__index = User

function User:new(name, age, email)
    local self = setmetatable({}, User)
    self.id = tostring(os.time()) .. math.random(1000, 9999)
    self.name = name
    self.age = age
    self.email = email
    self.created_at = os.time()
    return self
end

function User:is_valid()
    return self.name and self.name ~= "" and self.age > 0
end

function User:to_string()
    return string.format("User(id=%s, name=%s, age=%d)", self.id, self.name, self.age)
end

local UserService = {}
UserService.__index = UserService

function UserService:new(db_url)
    local self = setmetatable({}, UserService)
    self.db_url = db_url
    self.users = {}
    return self
end

function UserService:create_user(name, age, email)
    local user = User:new(name, age, email)
    table.insert(self.users, user)
    return user
end

function UserService:get_user(user_id)
    for _, user in ipairs(self.users) do
        if user.id == user_id then
            return user
        end
    end
    return nil
end

function UserService:get_all_users()
    return self.users
end

function UserService:get_user_count()
    return #self.users
end

-- Factory function
function create_user_service(db_url)
    return UserService:new(db_url)
end

return {
    User = User,
    UserService = UserService,
    create_user_service = create_user_service
}
