# User service for managing users in PowerShell

# Import required modules
Import-Module Microsoft.PowerShell.Utility
Import-Module Microsoft.PowerShell.Management

# User class
class User {
    [string]$Id
    [string]$Name
    [int]$Age
    [string]$Email
    [DateTime]$CreatedAt
    
    User([string]$Name, [int]$Age, [string]$Email = $null) {
        $this.Id = [System.Guid]::NewGuid().ToString()
        $this.Name = $Name
        $this.Age = $Age
        $this.Email = $Email
        $this.CreatedAt = Get-Date
    }
    
    [bool]IsValid() {
        return $this.Name -and $this.Name.Length -gt 0 -and $this.Age -gt 0
    }
    
    [string]ToString() {
        return "User(Id=$($this.Id), Name=$($this.Name), Age=$($this.Age))"
    }
}

# UserService class
class UserService {
    [string]$DbUrl
    [System.Collections.Generic.List[User]]$Users
    
    UserService([string]$DbUrl) {
        $this.DbUrl = $DbUrl
        $this.Users = [System.Collections.Generic.List[User]]::new()
    }
    
    [User]CreateUser([string]$Name, [int]$Age, [string]$Email = $null) {
        $user = [User]::new($Name, $Age, $Email)
        $this.Users.Add($user)
        return $user
    }
    
    [User]GetUser([string]$UserId) {
        return $this.Users | Where-Object { $_.Id -eq $UserId }
    }
    
    [User[]]GetAllUsers() {
        return $this.Users.ToArray()
    }
    
    [int]GetUserCount() {
        return $this.Users.Count
    }
    
    [User[]]GetUsersOlderThan([int]$Age) {
        return $this.Users | Where-Object { $_.Age -gt $Age }
    }
    
    [bool]RemoveUser([string]$UserId) {
        $user = $this.GetUser($UserId)
        if ($user) {
            $this.Users.Remove($user)
            return $true
        }
        return $false
    }
}

# Factory function
function New-UserService {
    param(
        [Parameter(Mandatory=$true)]
        [string]$DbUrl
    )
    
    return [UserService]::new($DbUrl)
}

# Helper functions
function Get-UserInfo {
    param(
        [Parameter(Mandatory=$true)]
        [User]$User
    )
    
    Write-Host "User Information:" -ForegroundColor Green
    Write-Host "  ID: $($User.Id)" -ForegroundColor Yellow
    Write-Host "  Name: $($User.Name)" -ForegroundColor Yellow
    Write-Host "  Age: $($User.Age)" -ForegroundColor Yellow
    Write-Host "  Email: $($User.Email)" -ForegroundColor Yellow
    Write-Host "  Created: $($User.CreatedAt)" -ForegroundColor Yellow
    Write-Host "  Valid: $($User.IsValid())" -ForegroundColor Yellow
}

# Main execution
function Main {
    Write-Host "User Service started" -ForegroundColor Cyan
    
    # Create user service
    $service = New-UserService -DbUrl "sqlite://test.db"
    
    # Create test users
    $user1 = $service.CreateUser("Alice", 30, "alice@example.com")
    $user2 = $service.CreateUser("Bob", 25, "bob@example.com")
    
    # Display user information
    Get-UserInfo -User $user1
    Get-UserInfo -User $user2
    
    # Show statistics
    Write-Host "`nStatistics:" -ForegroundColor Green
    Write-Host "Total users: $($service.GetUserCount())" -ForegroundColor Yellow
    Write-Host "Users older than 25: $($service.GetUsersOlderThan(25).Count)" -ForegroundColor Yellow
    
    Write-Host "`nUser Service completed" -ForegroundColor Cyan
}

# Run main function if script is executed directly
if ($MyInvocation.InvocationName -ne '.') {
    Main
}
