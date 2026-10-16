package com.procurement.pchardware.api;

import com.procurement.pchardware.model.BudgetOptimizationRequest;
import com.procurement.pchardware.model.CompatibilityRequest;
import com.procurement.pchardware.model.HardwareComparisonRequest;
import com.procurement.pchardware.service.BudgetOptimizerService;
import com.procurement.pchardware.service.CompatibilityService;
import com.procurement.pchardware.service.HardwareCatalogService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.HashMap;
import java.util.Map;

@RestController
@RequestMapping("/hardware")
public class HardwareController {
    private final HardwareCatalogService catalog;
    private final CompatibilityService compatibility;
    private final BudgetOptimizerService optimizer;

    public HardwareController(
            HardwareCatalogService catalog,
            CompatibilityService compatibility,
            BudgetOptimizerService optimizer) {
        this.catalog = catalog;
        this.compatibility = compatibility;
        this.optimizer = optimizer;
    }

    @GetMapping("/query")
    public Map<String, Object> query(
            @RequestParam(required = false) String type,
            @RequestParam(required = false) String keyword,
            @RequestParam(required = false) String condition) {
        return Map.of("items", catalog.query(type, keyword, condition), "dataSource", "MOCK");
    }

    @GetMapping("/detail")
    public Map<String, Object> detail(@RequestParam String id) {
        Map<String, Object> item = catalog.detail(id);
        if (item == null) {
            return Map.of("found", false, "message", "模拟目录中没有该硬件", "dataSource", "MOCK");
        }
        return Map.of("found", true, "item", item, "dataSource", "MOCK");
    }

    @PostMapping("/compare")
    public Map<String, Object> compare(@RequestBody HardwareComparisonRequest request) {
        return catalog.compare(request.ids());
    }

    @PostMapping("/compatibility")
    public Map<String, Object> checkCompatibility(@RequestBody CompatibilityRequest request) {
        return compatibility.check(request.components());
    }

    @PostMapping("/optimize")
    public Map<String, Object> optimize(@RequestBody BudgetOptimizationRequest request) {
        return optimizer.optimize(request);
    }

    @GetMapping("/health")
    public Map<String, Object> health() {
        Map<String, Object> result = new HashMap<>();
        result.put("status", "UP");
        result.put("dataSource", "MOCK");
        result.put("catalogSize", catalog.query(null, null, null).size());
        return result;
    }
}
