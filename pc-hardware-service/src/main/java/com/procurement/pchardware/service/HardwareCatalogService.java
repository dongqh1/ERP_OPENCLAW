package com.procurement.pchardware.service;

import com.procurement.pchardware.repository.HardwareCatalogRepository;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Map;

@Service
public class HardwareCatalogService {
    private final List<Map<String, Object>> catalog;

    public HardwareCatalogService(HardwareCatalogRepository repository) {
        this.catalog = repository.findAll();
    }

    public List<Map<String, Object>> query(String type, String keyword, String condition) {
        String normalizedType = canonicalType(type);
        String normalizedKeyword = normalize(keyword);
        List<Map<String, Object>> results = new ArrayList<>();
        for (Map<String, Object> item : catalog) {
            if (!normalizedType.isBlank() && !canonicalType(string(item, "type")).equals(normalizedType)) {
                continue;
            }
            String desiredCondition = canonicalCondition(condition);
            if (!desiredCondition.isBlank()
                    && !desiredCondition.equals("any")
                    && !normalize(string(item, "condition")).equals(desiredCondition)) {
                continue;
            }
            String searchable = String.join(" ",
                    string(item, "id"), string(item, "name"), string(item, "brand"),
                    string(item, "description"), string(item, "chipset"));
            if (normalizedKeyword.isBlank() || normalize(searchable).contains(normalizedKeyword)) {
                results.add(item);
            }
        }
        return results;
    }

    public Map<String, Object> detail(String id) {
        return catalog.stream()
                .filter(item -> string(item, "id").equalsIgnoreCase(id))
                .findFirst()
                .orElse(null);
    }

    public List<Map<String, Object>> byType(String type) {
        String normalizedType = canonicalType(type);
        return catalog.stream()
                .filter(item -> canonicalType(string(item, "type")).equals(normalizedType))
                .toList();
    }

    public List<Map<String, Object>> byTypeAndCondition(String type, String conditionPreference) {
        List<Map<String, Object>> items = byType(type);
        String preference = normalize(conditionPreference);
        if (preference.isBlank() || preference.equals("any") || preference.equals("bestvalue")
                || preference.equals("性价比") || preference.equals("都可以")) {
            return items;
        }
        String desired = switch (preference) {
            case "new", "全新", "只要全新" -> "new";
            case "used", "二手", "只要二手" -> "used";
            default -> "";
        };
        return desired.isBlank() ? items : items.stream()
                .filter(item -> normalize(string(item, "condition")).equals(desired))
                .toList();
    }

    public Map<String, Object> find(String type, String idOrName) {
        return find(type, idOrName, "any");
    }

    public Map<String, Object> find(String type, String idOrName, String conditionPreference) {
        String keyword = normalize(idOrName);
        return byTypeAndCondition(type, conditionPreference).stream()
                .filter(item -> normalize(string(item, "id")).equals(keyword)
                        || normalize(string(item, "name")).contains(keyword))
                .findFirst()
                .orElse(null);
    }

    public Map<String, Object> compare(List<String> ids) {
        List<Map<String, Object>> items = ids == null ? List.of()
                : ids.stream().map(this::detail).filter(item -> item != null).toList();
        List<Map<String, Object>> comparisons = new ArrayList<>();
        if (items.size() > 1) {
            Map<String, Object> baseline = items.get(0);
            for (int index = 1; index < items.size(); index++) {
                Map<String, Object> candidate = items.get(index);
                Map<String, Object> difference = new java.util.LinkedHashMap<>();
                difference.put("baseline", string(baseline, "id"));
                difference.put("candidate", string(candidate, "id"));
                difference.put("priceDifference",
                        decimal(candidate, "price", 0) - decimal(baseline, "price", 0));
                difference.put("gamingScoreDifference",
                        decimal(candidate, "gamingScore", 0) - decimal(baseline, "gamingScore", 0));
                difference.put("officeScoreDifference",
                        decimal(candidate, "officeScore", 0) - decimal(baseline, "officeScore", 0));
                difference.put("vramDifference",
                        integer(candidate, "vramGb", 0) - integer(baseline, "vramGb", 0));
                difference.put("powerDifference",
                        integer(candidate, "powerW", 0) - integer(baseline, "powerW", 0));
                comparisons.add(difference);
            }
        }
        return Map.of("items", items, "comparisons", comparisons, "dataSource", "MOCK");
    }

    public static String string(Map<String, Object> item, String field) {
        Object value = item.get(field);
        return value == null ? "" : String.valueOf(value);
    }

    public static int integer(Map<String, Object> item, String field, int fallback) {
        Object value = item.get(field);
        if (value instanceof Number number) return number.intValue();
        try {
            return value == null ? fallback : Integer.parseInt(String.valueOf(value));
        } catch (NumberFormatException ignored) {
            return fallback;
        }
    }

    public static double decimal(Map<String, Object> item, String field, double fallback) {
        Object value = item.get(field);
        if (value instanceof Number number) return number.doubleValue();
        try {
            return value == null ? fallback : Double.parseDouble(String.valueOf(value));
        } catch (NumberFormatException ignored) {
            return fallback;
        }
    }

    public static String normalize(String value) {
        return value == null ? "" : value.toLowerCase(Locale.ROOT).replace(" ", "").trim();
    }

    private static String canonicalCondition(String value) {
        return switch (normalize(value)) {
            case "new", "全新", "只要全新" -> "new";
            case "used", "二手", "只要二手" -> "used";
            case "any", "都可以", "不限", "" -> "any";
            default -> normalize(value);
        };
    }

    public static String canonicalType(String value) {
        return switch (normalize(value)) {
            case "cpu", "处理器" -> "cpu";
            case "gpu", "显卡", "graphicscard" -> "gpu";
            case "motherboard", "主板", "mb" -> "motherboard";
            case "memory", "ram", "内存" -> "memory";
            case "storage", "ssd", "硬盘", "固态硬盘" -> "storage";
            case "cooler", "散热", "散热器" -> "cooler";
            case "power", "psu", "电源" -> "power";
            case "case", "机箱" -> "case";
            default -> normalize(value);
        };
    }
}
