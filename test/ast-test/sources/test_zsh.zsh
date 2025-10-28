#!/bin/zsh

# User service for managing users in Zsh

# Global variables
typeset -A USERS
integer USER_COUNT=0

# User functions
create_user() {
    local name="$1"
    local age="$2"
    local email="$3"
    
    ((USER_COUNT++))
    local user_id="user_${USER_COUNT}"
    
    USERS["${user_id}_name"]="$name"
    USERS["${user_id}_age"]="$age"
    USERS["${user_id}_email"]="$email"
    USERS["${user_id}_created"]="$(date)"
    
    print "Created user: $name (ID: $user_id)"
    return 0
}

get_user() {
    local user_id="$1"
    
    if [[ -n "${USERS[${user_id}_name]}" ]]; then
        print "User Information:"
        print "  ID: $user_id"
        print "  Name: ${USERS[${user_id}_name]}"
        print "  Age: ${USERS[${user_id}_age]}"
        print "  Email: ${USERS[${user_id}_email]}"
        print "  Created: ${USERS[${user_id}_created]}"
    else
        print "User not found: $user_id" >&2
        return 1
    fi
}

list_users() {
    print "Listing all users:"
    for key in ${(k)USERS}; do
        if [[ "$key" == *"_name" ]]; then
            local user_id="${key%_name}"
            print "User: ${USERS[$key]} (ID: $user_id)"
        fi
    done
}

get_user_count() {
    print "Total users: $USER_COUNT"
}

search_users() {
    local pattern="$1"
    print "Searching for users matching: $pattern"
    
    for key in ${(k)USERS}; do
        if [[ "$key" == *"_name" ]]; then
            local user_id="${key%_name}"
            local name="${USERS[$key]}"
            
            if [[ "$name" == *"$pattern"* ]]; then
                print "Found match: $name (ID: $user_id)"
            fi
        fi
    done
}

get_users_older_than() {
    local min_age="$1"
    print "Users older than $min_age:"
    
    for key in ${(k)USERS}; do
        if [[ "$key" == *"_age" ]]; then
            local user_id="${key%_age}"
            local age="${USERS[$key]}"
            
            if ((age > min_age)); then
                local name="${USERS[${user_id}_name]}"
                print "  $name (age: $age)"
            fi
        fi
    done
}

export_users() {
    local export_file="${1:-users_export.csv}"
    print "Exporting users to: $export_file"
    
    print "ID,Name,Age,Email,Created" > "$export_file"
    
    for key in ${(k)USERS}; do
        if [[ "$key" == *"_name" ]]; then
            local user_id="${key%_name}"
            local name="${USERS[$key]}"
            local age="${USERS[${user_id}_age]}"
            local email="${USERS[${user_id}_email]}"
            local created="${USERS[${user_id}_created]}"
            
            print "$user_id,$name,$age,$email,$created" >> "$export_file"
        fi
    done
    
    print "Export completed"
}

# Main function
main() {
    print "RAG Assistant User Service (Zsh)"
    print "================================="
    
    # Create test users
    create_user "Alice" 30 "alice@example.com"
    create_user "Bob" 25 "bob@example.com"
    create_user "Charlie" 35 "charlie@example.com"
    
    # List users
    list_users
    
    # Search users
    search_users "alice"
    
    # Show statistics
    get_user_count
    get_users_older_than 28
    
    # Export users
    export_users "users_backup.csv"
    
    print ""
    print "User Service completed"
}

# Run main function if script is executed directly
if [[ "${(%):-%x}" == "${0}" ]]; then
    main "$@"
fi
