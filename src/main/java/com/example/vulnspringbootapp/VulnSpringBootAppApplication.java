package com.example.vulnspringbootapp;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public final class VulnSpringBootAppApplication {

    private VulnSpringBootAppApplication() {
        // Private constructor to prevent instantiation
    }

    public static void main(final String[] args) {
        SpringApplication.run(VulnSpringBootAppApplication.class, args);
    }
}




