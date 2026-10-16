package com.procurement.pchardware.service;

import com.procurement.pchardware.model.BudgetOptimizationRequest;
import com.procurement.pchardware.repository.HardwareCatalogRepository;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

class CompatibilityServiceTest {
    @Test
    void missingGpuLengthIsMarkedForVerification() {
        CompatibilityService service = service(List.of(
                part("id", "GPU-UNKNOWN-LENGTH", "type", "GPU"),
                part("id", "CASE-KNOWN-LIMIT", "type", "CASE", "maxGpuLengthMm", 320)
        ));

        Map<String, Object> result = service.check(Map.of(
                "GPU", "GPU-UNKNOWN-LENGTH",
                "CASE", "CASE-KNOWN-LIMIT"
        ));

        assertEquals("needs_verification", result.get("status"));
        assertEquals("待核实", result.get("statusLabel"));
        assertFalse((Boolean) result.get("compatible"));
        assertEquals("NEEDS_VERIFICATION", check(result, "gpu_case_clearance").get("status"));
        assertEquals("待核实", check(result, "gpu_case_clearance").get("statusLabel"));
    }

    @Test
    void missingCaseGpuLimitIsMarkedForVerification() {
        CompatibilityService service = service(List.of(
                part("id", "GPU-KNOWN-LENGTH", "type", "GPU", "lengthMm", 300),
                part("id", "CASE-UNKNOWN-LIMIT", "type", "CASE")
        ));

        Map<String, Object> result = service.check(Map.of(
                "GPU", "GPU-KNOWN-LENGTH",
                "CASE", "CASE-UNKNOWN-LIMIT"
        ));

        assertEquals("needs_verification", result.get("status"));
        assertEquals("待核实", result.get("statusLabel"));
        assertEquals("NEEDS_VERIFICATION", check(result, "gpu_case_clearance").get("status"));
    }

    @Test
    void knownGpuCaseDimensionConflictIsIncompatible() {
        CompatibilityService service = service(List.of(
                part("id", "GPU-TOO-LONG", "type", "GPU", "lengthMm", 350),
                part("id", "CASE-LIMIT-320", "type", "CASE", "maxGpuLengthMm", 320)
        ));

        Map<String, Object> result = service.check(Map.of(
                "GPU", "GPU-TOO-LONG",
                "CASE", "CASE-LIMIT-320"
        ));

        assertEquals("incompatible", result.get("status"));
        assertFalse((Boolean) result.get("compatible"));
        assertEquals("INCOMPATIBLE", check(result, "gpu_case_clearance").get("status"));
    }

    @Test
    void optimizerKeepsBuildWhenOnlyClearanceDimensionsAreUnknown() {
        List<Map<String, Object>> items = completeBuildCatalog(null, null);
        HardwareCatalogService catalog = new HardwareCatalogService(() -> items);
        CompatibilityService compatibility = new CompatibilityService(catalog);
        BudgetOptimizerService optimizer = new BudgetOptimizerService(catalog, compatibility);

        Map<String, Object> result = optimizer.optimize(new BudgetOptimizationRequest(
                new BigDecimal("8000"), "游戏", "1080p", 60, null, "new", List.of()
        ));

        assertEquals("success", result.get("status"));
        assertEquals("needs_verification", result.get("compatibilityStatus"));
        assertEquals("待核实", result.get("compatibilityStatusLabel"));
        assertEquals(Boolean.TRUE, result.get("verificationRequired"));
        assertEquals(Boolean.FALSE, result.get("compatible"));
        assertNotNull(result.get("build"));
        assertTrue(((List<?>) result.get("build")).stream().anyMatch(row ->
                "GPU-TEST".equals(((Map<?, ?>) row).get("id"))));
    }

    @Test
    void optimizerRejectsKnownGpuCaseDimensionConflict() {
        List<Map<String, Object>> items = completeBuildCatalog(350, 320);
        HardwareCatalogService catalog = new HardwareCatalogService(() -> items);
        CompatibilityService compatibility = new CompatibilityService(catalog);
        BudgetOptimizerService optimizer = new BudgetOptimizerService(catalog, compatibility);

        Map<String, Object> result = optimizer.optimize(new BudgetOptimizationRequest(
                new BigDecimal("8000"), "游戏", "1080p", 60, null, "new", List.of()
        ));

        assertEquals("no_compatible_build_within_budget", result.get("status"));
    }

    private static CompatibilityService service(List<Map<String, Object>> items) {
        HardwareCatalogService catalog = new HardwareCatalogService(() -> items);
        return new CompatibilityService(catalog);
    }

    private static List<Map<String, Object>> completeBuildCatalog(Integer gpuLength, Integer caseLimit) {
        Map<String, Object> gpu = part("id", "GPU-TEST", "type", "GPU", "price", 2000, "condition", "new",
                "vramGb", 8, "powerW", 150, "recommendedPsuW", 550, "gamingScore", 8.0);
        if (gpuLength != null) gpu.put("lengthMm", gpuLength);

        Map<String, Object> computerCase = part("id", "CASE-TEST", "type", "CASE", "price", 300,
                "condition", "new", "supportedFormFactors", List.of("mATX"));
        if (caseLimit != null) computerCase.put("maxGpuLengthMm", caseLimit);

        return List.of(
                part("id", "CPU-TEST", "type", "CPU", "price", 1000, "condition", "new",
                        "socket", "AM5", "supportedChipsets", List.of("B650"), "tdpW", 65,
                        "gamingScore", 7.0, "officeScore", 7.0),
                gpu,
                part("id", "BOARD-TEST", "type", "MOTHERBOARD", "price", 700, "condition", "new",
                        "socket", "AM5", "chipset", "B650", "memoryType", "DDR5", "formFactor", "mATX"),
                part("id", "MEMORY-TEST", "type", "MEMORY", "price", 400, "condition", "new",
                        "memoryType", "DDR5", "capacityGb", 32),
                part("id", "STORAGE-TEST", "type", "STORAGE", "price", 500, "condition", "new"),
                part("id", "COOLER-TEST", "type", "COOLER", "price", 200, "condition", "new",
                        "maxTdpW", 150, "supportedSockets", List.of("AM5")),
                part("id", "POWER-TEST", "type", "POWER", "price", 400, "condition", "new",
                        "ratedPowerW", 650),
                computerCase
        );
    }

    private static Map<?, ?> check(Map<String, Object> result, String name) {
        Object checksValue = result.get("checks");
        assertTrue(checksValue instanceof List<?>);
        for (Object item : (List<?>) checksValue) {
            if (item instanceof Map<?, ?> check && name.equals(check.get("name"))) return check;
        }
        throw new AssertionError("找不到检查项：" + name);
    }

    private static Map<String, Object> part(Object... fields) {
        Map<String, Object> item = new HashMap<>();
        for (int index = 0; index < fields.length; index += 2) {
            item.put((String) fields[index], fields[index + 1]);
        }
        return item;
    }
}
