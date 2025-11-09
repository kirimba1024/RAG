package com.kirimba.javafw;

import org.springframework.boot.SpringApplication;

public class TestJavafwApplication {

	public static void main(String[] args) {
		SpringApplication.from(Application::main).with(TestcontainersConfiguration.class).run(args);
	}

}
