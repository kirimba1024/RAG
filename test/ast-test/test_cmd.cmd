@echo off
REM User service for managing users in Windows CMD

setlocal enabledelayedexpansion

REM Global variables
set USER_COUNT=0

REM User functions
:create_user
set name=%~1
set age=%~2
set email=%~3
set /a USER_COUNT+=1
set user_id=user_%USER_COUNT%
echo Created user: %name% (ID: %user_id%)
goto :eof

:get_user
set user_id=%~1
echo Getting user: %user_id%
goto :eof

:list_users
echo Listing all users...
echo Total users: %USER_COUNT%
goto :eof

:get_user_count
echo User count: %USER_COUNT%
goto :eof

REM Main execution
:main
echo User Service started

REM Create test users
call :create_user "Alice" 30 "alice@example.com"
call :create_user "Bob" 25 "bob@example.com"

REM List users
call :list_users

echo User Service completed
goto :eof

REM Run main function
call :main
