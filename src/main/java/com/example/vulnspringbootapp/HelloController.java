package com.example.vulnspringbootapp;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.apache.commons.text.StringSubstitutor;
import org.apache.commons.text.StringEscapeUtils;
import java.util.HashMap;
import java.util.Map;

@RestController
public class HelloController {

    @GetMapping("/")
    public String hello(@RequestParam(name = "template", required = false) String template) {
        // Intentionally unsafe: allows arbitrary variable interpolation via commons-text vulnerable version
        String base = template != null ? template : "Hello, ${user}!";
        Map<String, String> values = new HashMap<>();
        values.put("user", "World");
        // In vulnerable versions, certain lookup patterns (like script, dns, url) could be exploited
        return StringEscapeUtils.escapeHtml4(new StringSubstitutor(values).replace(base));
    }
}


