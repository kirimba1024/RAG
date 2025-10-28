module UserService where

import Data.Time
import Data.UUID
import Data.UUID.V4

-- User data type
data User = User
  { userId :: String
  , userName :: String
  , userAge :: Int
  , userEmail :: Maybe String
  , userCreatedAt :: UTCTime
  } deriving (Show, Eq)

-- UserService data type
data UserService = UserService
  { serviceDbUrl :: String
  , serviceUsers :: [User]
  } deriving (Show)

-- Type class for validation
class Validatable a where
  isValid :: a -> Bool

instance Validatable User where
  isValid user = userName user /= "" && userAge user > 0

-- Create a new user
createUser :: String -> Int -> Maybe String -> IO User
createUser name age email = do
  uuid <- nextRandom
  now <- getCurrentTime
  return $ User
    { userId = toString uuid
    , userName = name
    , userAge = age
    , userEmail = email
    , userCreatedAt = now
    }

-- Create user service
newUserService :: String -> UserService
newUserService dbUrl = UserService dbUrl []

-- Add user to service
addUser :: UserService -> User -> UserService
addUser service user = service { serviceUsers = user : serviceUsers service }

-- Get user by ID
getUser :: UserService -> String -> Maybe User
getUser service userId = find (\u -> userId == userId u) (serviceUsers service)

-- Get all users
getAllUsers :: UserService -> [User]
getAllUsers = serviceUsers

-- Get user count
getUserCount :: UserService -> Int
getUserCount = length . serviceUsers
