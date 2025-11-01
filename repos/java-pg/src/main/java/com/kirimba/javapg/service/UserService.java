package com.kirimba.javapg.service;

import com.kirimba.javapg.dto.projection.UserProjection;
import com.kirimba.javapg.dto.request.UserRequest;
import com.kirimba.javapg.dto.response.UserResponse;
import com.kirimba.javapg.mapper.UserMapper;
import com.kirimba.javapg.model.User;
import com.kirimba.javapg.repository.UserRepository;

import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Optional;

@Service
@RequiredArgsConstructor
@Transactional
public class UserService {
    
    private final UserRepository userRepository;
    private final UserMapper userMapper;

    /**
     * Находит пользователей по имени (без учета регистра) используя projection.
     * Возвращает только необходимые поля через Spring Data Projection.
     *
     * @param firstName имя для поиска
     * @return список проекций пользователей
     */
    @Transactional(readOnly = true)
    public List<UserProjection> findUsersByFirstName(String firstName) {
        return userRepository.findByFirstNameIgnoreCase(firstName);
    }

    /**
     * Находит первого пользователя по имени через projection.
     *
     * @param firstName имя для поиска
     * @return проекция пользователя или empty если не найден
     */
    @Transactional(readOnly = true)
    public Optional<UserProjection> findFirstUserByFirstName(String firstName) {
        return userRepository.findByFirstNameIgnoreCase(firstName)
                .stream()
                .findFirst();
    }
    
    public UserResponse createUser(UserRequest userRequest) {
        // Проверка на уникальность email
        if (userRepository.findByEmail(userRequest.getEmail()).isPresent()) {
            throw new IllegalArgumentException("User with this email already exists");
        }
        User user = userMapper.toEntity(userRequest);
        User savedUser = userRepository.save(user);
        return userMapper.toResponse(savedUser);
    }
    
    @Transactional(readOnly = true)
    public List<User> searchUsers(String searchTerm) {
        return userRepository.findByLastNameContainingIgnoreCase(searchTerm);
    }

    public Optional<User> getUserById(Long id) {
        return userRepository.findById(id);
    }
    
    public void deleteUser(Long id) {
        userRepository.deleteById(id);
    }
}