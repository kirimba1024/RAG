# User service for managing users in R

library(uuid)
library(jsonlite)

#' User class for representing users
User <- R6::R6Class("User",
  public = list(
    id = NULL,
    name = NULL,
    age = NULL,
    email = NULL,
    created_at = NULL,
    
    initialize = function(name, age, email = NULL) {
      self$id <- UUIDgenerate()
      self$name <- name
      self$age <- age
      self$email <- email
      self$created_at <- Sys.time()
    },
    
    is_valid = function() {
      return(!is.null(self$name) && nchar(self$name) > 0 && self$age > 0)
    },
    
    to_string = function() {
      return(paste0("User(id=", self$id, ", name=", self$name, ", age=", self$age, ")"))
    }
  )
)

#' UserService class for managing users
UserService <- R6::R6Class("UserService",
  public = list(
    db_url = NULL,
    users = NULL,
    
    initialize = function(db_url) {
      self$db_url <- db_url
      self$users <- list()
    },
    
    create_user = function(name, age, email = NULL) {
      user <- User$new(name, age, email)
      self$users[[user$id]] <- user
      return(user)
    },
    
    get_user = function(user_id) {
      return(self$users[[user_id]])
    },
    
    get_all_users = function() {
      return(self$users)
    },
    
    get_user_count = function() {
      return(length(self$users))
    }
  )
)

# Factory function
create_user_service <- function(db_url) {
  return(UserService$new(db_url))
}
