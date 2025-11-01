package com.kirimba.javapg.mapper;

import com.kirimba.javapg.dto.response.UserResponse;
import com.kirimba.javapg.model.User;
import com.kirimba.javapg.dto.request.UserRequest;
import org.mapstruct.Mapper;
import org.mapstruct.Mapping;
import org.mapstruct.MappingTarget;

/**
 * Маппер для преобразования между Entity и DTO.
 * MapStruct генерирует реализацию во время компиляции - БЕЗ ОТРАЖЕНИЯ!
 */
@Mapper(componentModel = "spring")  // ✅ Интеграция со Spring
public interface UserMapper {

    /**
     * Преобразует UserRequest в User entity.
     * Игнорирует поля, которые не должны маппиться из DTO.
     */
    @Mapping(target = "id", ignore = true)
    @Mapping(target = "createdAt", ignore = true)
    User toEntity(UserRequest userRequest);

    /**
     * Преобразует User entity в UserResponse.
     * Включает все поля, которые нужно показать клиенту.
     */
    UserResponse toResponse(User user);

    /**
     * Обновляет существующую User entity из UserRequest.
     * Не затрагивает технические поля (id, createdAt).
     */
    @Mapping(target = "id", ignore = true)
    @Mapping(target = "createdAt", ignore = true)
    void updateEntity(UserRequest userRequest, @MappingTarget User user);
}