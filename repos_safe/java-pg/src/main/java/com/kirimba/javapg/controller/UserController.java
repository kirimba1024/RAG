package com.kirimba.javapg.controller;

import com.kirimba.javapg.dto.projection.UserProjection;
import com.kirimba.javapg.dto.request.UserRequest;
import com.kirimba.javapg.dto.response.UserResponse;
import com.kirimba.javapg.model.User;
import com.kirimba.javapg.service.UserService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/users")
@RequiredArgsConstructor
public class UserController {
    
    private final UserService userService;

    /**
     * Ищет пользователей по имени (без учета регистра).
     * Возвращает lightweight проекции с ограниченным набором полей.
     *
     * @param firstName имя для поиска
     * @return список пользователей в формате projection
     */
    @Operation(summary = "Поиск пользователей по имени")
    @GetMapping("/by-firstname")
    public ResponseEntity<List<UserProjection>> getUsersByFirstName(
            @Parameter(description = "Имя для поиска") @RequestParam String firstName
    ) {
        List<UserProjection> users = userService.findUsersByFirstName(firstName);
        if (users.isEmpty()) {
            return ResponseEntity.noContent().build();  // 204 No Content
        }
        return ResponseEntity.ok(users);  // 200 OK с проекциями
    }

    /**
     * Находит первого пользователя с указанным именем.
     *
     * @param firstName имя для поиска
     * @return пользователь или 404 если не найден
     */
    @Operation(summary = "Найти первого пользователя по имени")
    @GetMapping("/first-by-name")
    public ResponseEntity<UserProjection> getFirstUserByFirstName(
            @Parameter(description = "Имя для поиска") @RequestParam String firstName
    ) {
        return userService.findFirstUserByFirstName(firstName)
                .map(ResponseEntity::ok)  // 200 OK
                .orElse(ResponseEntity.notFound().build());  // 404 Not Found
    }

    @Operation(summary = "Создать нового пользователя")
    @PostMapping
    public ResponseEntity<UserResponse> createUser(
            @Parameter(description = "Данные нового пользователя")
            @Valid @RequestBody UserRequest request
    ) {
        UserResponse userResponse = userService.createUser(request);
        return ResponseEntity.status(HttpStatus.CREATED).body(userResponse);
    }

    @Operation(summary = "Поиск пользователей по части имени")
    @GetMapping("/search")
    public ResponseEntity<List<User>> searchUsers(
            @Parameter(description = "Поисковый запрос")
            @RequestParam String searchTerm
    ) {
        List<User> users = userService.searchUsers(searchTerm);
        return users.isEmpty()
                ? ResponseEntity.noContent().build()
                : ResponseEntity.ok(users);
    }

    @Operation(summary = "Получить пользователя по ID")
    @GetMapping("/{id}")
    public ResponseEntity<User> getUser(
            @Parameter(description = "ID пользователя")
            @PathVariable Long id
    ) {
        return userService.getUserById(id)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @Operation(summary = "Удалить пользователя по ID")
    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteUser(
            @Parameter(description = "ID пользователя")
            @PathVariable Long id
    ) {
        userService.deleteUser(id);
        return ResponseEntity.noContent().build();
    }
}