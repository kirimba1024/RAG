// src/main/java/com/kirimba/javapg/dto/projection/UserProjection.java
package com.kirimba.javapg.dto.projection;

import java.time.LocalDateTime;

/**
 * Projection интерфейс для выборки только определенных полей из БД.
 * Spring Data автоматически реализует этот интерфейс!
 */
public interface UserProjection {
    
    Long getId();
    String getEmail();
    String getFirstName();
    String getLastName();
    LocalDateTime getCreatedAt();
    
    // Вычисляемое поле (default method)
    default String getFullName() {
        return getFirstName() + " " + getLastName();
    }

}