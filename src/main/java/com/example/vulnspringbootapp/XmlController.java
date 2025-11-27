package com.example.vulnspringbootapp;

import org.dom4j.Document;
import org.dom4j.io.SAXReader;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.io.StringReader;

@RestController
public class XmlController {

    @GetMapping("/parse-xml")
    public String parseXml(@RequestParam(defaultValue = "<root>test</root>") String xml) {
        try {
            SAXReader reader = new SAXReader();
            Document document = reader.read(new StringReader(xml));
            return "Parsed XML root: " + document.getRootElement().getName();
        } catch (Exception e) {
            return "Error parsing XML: " + e.getMessage();
        }
    }
}
