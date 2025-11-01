package com.kirimba.javapg;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * Главный класс Spring Boot приложения.
 * Запускает контекст Spring и инициализирует все компоненты.
 */
@SpringBootApplication
public class Application {

    /**
     * Точка входа в приложение.
     * Запускает Spring Boot приложение с автоконфигурацией.
     *
     * @param args аргументы командной строки
     */
	public static void main(String[] args) {
		SpringApplication.run(Application.class, args);
	}

}
