package com.example.vulnspringbootapp;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class JsonEchoController {

    private final ObjectMapper mapper = new ObjectMapper();

    // Intentionally simplistic deserialization using vulnerable jackson-databind
    @PostMapping(value = "/echo", consumes = MediaType.APPLICATION_JSON_VALUE, produces = MediaType.APPLICATION_JSON_VALUE)
    public String echo(@RequestBody String body) throws Exception {
        JsonNode node = mapper.readTree(body);
        return mapper.writeValueAsString(node);
    }
}
