package com.kirimba.javapg.repository;

import com.kirimba.javapg.dto.projection.UserProjection;
import com.kirimba.javapg.model.User;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

public interface UserRepository extends JpaRepository<User, Long> {

    Optional<User> findByEmail(String email);

    List<UserProjection> findByFirstNameIgnoreCase(String firstName);
    
    List<User> findByLastNameContainingIgnoreCase(String lastName);
    
    @Query("SELECT u FROM User u WHERE u.createdAt >= :startDate")
    List<User> findRecentUsers(@Param("startDate") LocalDateTime startDate);
}