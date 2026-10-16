package com.procurement.pchardware.repository;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Repository;

import java.io.IOException;
import java.util.List;
import java.util.Map;

/** 从 classpath JSON 读取本地模拟硬件目录。 */
@Repository
public class JsonHardwareCatalogRepository implements HardwareCatalogRepository {
    private final List<Map<String, Object>> catalog;

    public JsonHardwareCatalogRepository(ObjectMapper objectMapper) {
        try {
            this.catalog = objectMapper.readValue(
                    new ClassPathResource("data/hardware-catalog.json").getInputStream(),
                    new TypeReference<>() {});
        } catch (IOException error) {
            throw new IllegalStateException("无法加载模拟硬件目录", error);
        }
    }

    @Override
    public List<Map<String, Object>> findAll() {
        return catalog;
    }
}
