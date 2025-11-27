package com.example.vulnspringbootapp;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class LogController {

    private static final Logger logger = LogManager.getLogger(LogController.class);

    @GetMapping("/log")
    public String log(@RequestParam(name = "message", required = false) String message) {
        // Intentionally vulnerable: log4j 2.14.1 is susceptible to Log4Shell
        // User input is logged directly, allowing JNDI lookup injection
        String logMessage = message != null ? message : "default message";
        logger.info("User provided message: {}", logMessage);
        return "Logged: " + logMessage;
    }
}
