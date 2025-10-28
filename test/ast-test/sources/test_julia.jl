module UserService

using UUIDs
using Dates
using JSON

"""
    User

Represents a user in the system with basic information and validation.
"""
mutable struct User
    id::String
    name::String
    age::Int
    email::Union{String, Nothing}
    created_at::DateTime
    
    function User(name::String, age::Int, email::Union{String, Nothing} = nothing)
        new(
            string(uuid4()),
            name,
            age,
            email,
            now()
        )
    end
end

"""
    UserService

Service for managing users with CRUD operations.
"""
mutable struct UserService
    db_url::String
    users::Vector{User}
    
    function UserService(db_url::String)
        new(db_url, User[])
    end
end

"""
    is_valid(user::User) -> Bool

Checks if a user is valid (has name and positive age).
"""
function is_valid(user::User)::Bool
    return !isempty(user.name) && user.age > 0
end

"""
    create_user(service::UserService, name::String, age::Int, email::Union{String, Nothing} = nothing) -> User

Creates a new user and adds it to the service.
"""
function create_user(service::UserService, name::String, age::Int, email::Union{String, Nothing} = nothing)::User
    user = User(name, age, email)
    push!(service.users, user)
    return user
end

"""
    get_user(service::UserService, user_id::String) -> Union{User, Nothing}

Gets a user by ID.
"""
function get_user(service::UserService, user_id::String)::Union{User, Nothing}
    for user in service.users
        if user.id == user_id
            return user
        end
    end
    return nothing
end

"""
    get_all_users(service::UserService) -> Vector{User}

Gets all users.
"""
function get_all_users(service::UserService)::Vector{User}
    return copy(service.users)
end

"""
    get_user_count(service::UserService) -> Int

Gets the number of users.
"""
function get_user_count(service::UserService)::Int
    return length(service.users)
end

"""
    to_json(user::User) -> String

Converts a user to JSON string.
"""
function to_json(user::User)::String
    return JSON.json(Dict(
        "id" => user.id,
        "name" => user.name,
        "age" => user.age,
        "email" => user.email,
        "created_at" => string(user.created_at)
    ))
end

# Export public functions
export User, UserService, create_user, get_user, get_all_users, get_user_count, is_valid, to_json

end # module
