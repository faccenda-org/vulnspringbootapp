package com.example.vulnspringbootapp;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class VulnSpringBootAppApplication {

    // private VulnSpringBootAppApplication() {
    //     // Private constructor to prevent instantiation
    // }
    public VulnSpringBootAppApplication() {
    }

    public static void main(final String[] args) {
        SpringApplication.run(VulnSpringBootAppApplication.class, args);
    }
}
