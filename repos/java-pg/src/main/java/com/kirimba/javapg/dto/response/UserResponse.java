package com.kirimba.javapg.dto.response;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;
import java.time.LocalDateTime;

/**
 * DTO для возврата данных о пользователе в API responses.
 * Содержит только те поля, которые нужно показывать клиенту.
 */
@Data
@Schema(description = "Ответ с данными пользователя")
public class UserResponse {

    @Schema(description = "Уникальный идентификатор пользователя", example = "1")
    private Long id;

    @Schema(description = "Email пользователя", example = "user@example.com")
    private String email;

    @Schema(description = "Имя пользователя", example = "Иван")
    private String firstName;

    @Schema(description = "Фамилия пользователя", example = "Иванов")
    private String lastName;

    @Schema(description = "Дата и время создания аккаунта", example = "2024-01-15T10:30:00")
    private LocalDateTime createdAt;
}