#!/bin/bash

# User service for managing users in Bash

# Global variables
declare -A USERS
USER_COUNT=0

# User functions
create_user() {
    local name="$1"
    local age="$2"
    local email="$3"
    
    local user_id="user_$(date +%s)_$$"
    USERS["${user_id}_name"]="$name"
    USERS["${user_id}_age"]="$age"
    USERS["${user_id}_email"]="$email"
    USERS["${user_id}_created"]="$(date)"
    
    echo "$user_id"
}

get_user() {
    local user_id="$1"
    
    if [[ -n "${USERS[${user_id}_name]}" ]]; then
        echo "ID: $user_id"
        echo "Name: ${USERS[${user_id}_name]}"
        echo "Age: ${USERS[${user_id}_age]}"
        echo "Email: ${USERS[${user_id}_email]}"
        echo "Created: ${USERS[${user_id}_created]}"
    else
        echo "User not found"
        return 1
    fi
}

list_users() {
    for key in "${!USERS[@]}"; do
        if [[ "$key" == *"_name" ]]; then
            local user_id="${key%_name}"
            echo "User: ${USERS[$key]} (ID: $user_id)"
        fi
    done
}

get_user_count() {
    echo "Total users: $USER_COUNT"
}

# Main function
main() {
    echo "User Service started"
    
    # Create some test users
    local user1=$(create_user "Alice" 30 "alice@example.com")
    local user2=$(create_user "Bob" 25 "bob@example.com")
    
    echo "Created users:"
    list_users
    
    echo "User details:"
    get_user "$user1"
}

# Run main if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
