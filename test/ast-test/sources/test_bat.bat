@echo off
REM User service for managing users in Windows Batch

setlocal enabledelayedexpansion

REM Global variables
set USER_COUNT=0
set USER_DATA_DIR=%~dp0user_data

REM Create user data directory if it doesn't exist
if not exist "%USER_DATA_DIR%" mkdir "%USER_DATA_DIR%"

REM User functions
:create_user
set name=%~1
set age=%~2
set email=%~3
set /a USER_COUNT+=1
set user_id=user_%USER_COUNT%
set user_file=%USER_DATA_DIR%\user_%USER_COUNT%.txt

echo ID=%user_id% > "%user_file%"
echo NAME=%name% >> "%user_file%"
echo AGE=%age% >> "%user_file%"
echo EMAIL=%email% >> "%user_file%"
echo CREATED=%date% %time% >> "%user_file%"

echo Created user: %name% (ID: %user_id%)
goto :eof

:get_user
set user_id=%~1
set user_file=%USER_DATA_DIR%\user_%user_id%.txt

if exist "%user_file%" (
    echo User Information:
    type "%user_file%"
) else (
    echo User not found: %user_id%
    exit /b 1
)
goto :eof

:list_users
echo Listing all users...
for %%f in ("%USER_DATA_DIR%\user_*.txt") do (
    echo.
    echo User file: %%~nxf
    type "%%f"
)
goto :eof

:get_user_count
echo User count: %USER_COUNT%
goto :eof

:search_users
set pattern=%~1
echo Searching for users matching: %pattern%
for %%f in ("%USER_DATA_DIR%\user_*.txt") do (
    findstr /i "%pattern%" "%%f" >nul
    if !errorlevel! equ 0 (
        echo Found match in %%~nxf:
        type "%%f"
        echo.
    )
)
goto :eof

:delete_user
set user_id=%~1
set user_file=%USER_DATA_DIR%\user_%user_id%.txt

if exist "%user_file%" (
    del "%user_file%"
    echo User %user_id% deleted
) else (
    echo User not found: %user_id%
    exit /b 1
)
goto :eof

:export_users
set export_file=%~1
if "%export_file%"=="" set export_file=users_export.txt

echo Exporting users to: %export_file%
echo USER_ID,NAME,AGE,EMAIL,CREATED > "%export_file%"
for %%f in ("%USER_DATA_DIR%\user_*.txt") do (
    for /f "tokens=2 delims==" %%a in (%%f) do (
        if "%%a"=="ID" set id=%%b
        if "%%a"=="NAME" set name=%%b
        if "%%a"=="AGE" set age=%%b
        if "%%a"=="EMAIL" set email=%%b
        if "%%a"=="CREATED" set created=%%b
    )
    echo !id!,!name!,!age!,!email!,!created! >> "%export_file%"
)
echo Export completed
goto :eof

REM Main execution
:main
echo RAG Assistant User Service (Batch)
echo ==================================

REM Create test users
call :create_user "Alice" 30 "alice@example.com"
call :create_user "Bob" 25 "bob@example.com"
call :create_user "Charlie" 35 "charlie@example.com"

REM List users
call :list_users

REM Search users
call :search_users "alice"

REM Show statistics
call :get_user_count

REM Export users
call :export_users "users_backup.txt"

echo.
echo User Service completed
goto :eof

REM Run main function
call :main
