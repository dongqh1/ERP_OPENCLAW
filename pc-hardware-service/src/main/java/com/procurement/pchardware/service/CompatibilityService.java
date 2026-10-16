package com.procurement.pchardware.service;

import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Service
public class CompatibilityService {
    private static final String PASSED = "PASSED";
    private static final String INCOMPATIBLE = "INCOMPATIBLE";
    private static final String NEEDS_VERIFICATION = "NEEDS_VERIFICATION";

    private final HardwareCatalogService catalog;

    public CompatibilityService(HardwareCatalogService catalog) {
        this.catalog = catalog;
    }

    public Map<String, Object> check(Map<String, String> selected) {
        List<Map<String, Object>> checks = new ArrayList<>();
        Map<String, Map<String, Object>> parts = new HashMap<>();
        if (selected == null) selected = Map.of();
        for (Map.Entry<String, String> entry : selected.entrySet()) {
            String type = HardwareCatalogService.canonicalType(entry.getKey()).toUpperCase();
            Map<String, Object> item = catalog.find(type, entry.getValue());
            if (item != null) {
                parts.put(type, item);
            } else {
                checks.add(check("component_exists", NEEDS_VERIFICATION,
                        "模拟目录未找到硬件：" + entry.getKey() + " / " + entry.getValue() + "，无法核实兼容性"));
            }
        }

        Map<String, Object> cpu = parts.get("CPU");
        Map<String, Object> gpu = parts.get("GPU");
        Map<String, Object> board = parts.get("MOTHERBOARD");
        Map<String, Object> memory = parts.get("MEMORY");
        Map<String, Object> cooler = parts.get("COOLER");
        Map<String, Object> power = parts.get("POWER");
        Map<String, Object> computerCase = parts.get("CASE");
        for (String required : List.of(
                "CPU", "GPU", "MOTHERBOARD", "MEMORY", "STORAGE", "COOLER", "POWER", "CASE")) {
            if (!parts.containsKey(required)) {
                checks.add(check("component_required", NEEDS_VERIFICATION, "配置缺少必需部件：" + required));
            }
        }

        if (cpu != null && board != null) {
            String cpuSocket = HardwareCatalogService.string(cpu, "socket");
            String boardSocket = HardwareCatalogService.string(board, "socket");
            if (cpuSocket.isBlank() || boardSocket.isBlank()) {
                checks.add(check("cpu_motherboard_socket", NEEDS_VERIFICATION,
                        "CPU 或主板插槽参数缺失，待核实"));
            } else {
                boolean socketMatch = cpuSocket.equalsIgnoreCase(boardSocket);
                checks.add(check("cpu_motherboard_socket", socketMatch ? PASSED : INCOMPATIBLE,
                        socketMatch ? "CPU 与主板插槽匹配" : "CPU 与主板插槽不匹配"));
            }
            Object supported = cpu.get("supportedChipsets");
            String chipset = HardwareCatalogService.string(board, "chipset");
            if (chipset.isBlank() || !(supported instanceof List<?> list) || list.isEmpty()) {
                checks.add(check("cpu_chipset", NEEDS_VERIFICATION,
                        "CPU 支持芯片组或主板芯片组参数缺失，待核实"));
            } else {
                boolean chipsetMatch = list.stream().anyMatch(value -> String.valueOf(value)
                        .equalsIgnoreCase(chipset));
                checks.add(check("cpu_chipset", chipsetMatch ? PASSED : INCOMPATIBLE,
                        chipsetMatch ? "主板芯片组在 CPU 支持范围内" : "CPU 不支持该主板芯片组"));
            }
        }

        if (board != null && memory != null) {
            String boardMemory = HardwareCatalogService.string(board, "memoryType");
            String memoryType = HardwareCatalogService.string(memory, "memoryType");
            if (boardMemory.isBlank() || memoryType.isBlank()) {
                checks.add(check("memory_generation", NEEDS_VERIFICATION,
                        "主板或内存代际参数缺失，待核实"));
            } else {
                boolean memoryMatch = boardMemory.equalsIgnoreCase(memoryType);
                checks.add(check("memory_generation", memoryMatch ? PASSED : INCOMPATIBLE,
                        memoryMatch ? "主板与内存代际匹配" : "主板与内存 DDR 代际不匹配"));
            }
        }

        if (gpu != null && computerCase != null) {
            if (!hasPositiveInteger(gpu, "lengthMm")
                    || !hasPositiveInteger(computerCase, "maxGpuLengthMm")) {
                checks.add(check("gpu_case_clearance", NEEDS_VERIFICATION,
                        "显卡长度或机箱显卡限长缺失，尺寸适配待核实；保留该配置"));
            } else {
                int gpuLength = HardwareCatalogService.integer(gpu, "lengthMm", 0);
                int maxGpuLength = HardwareCatalogService.integer(computerCase, "maxGpuLengthMm", 0);
                boolean sizeMatch = gpuLength <= maxGpuLength;
                checks.add(check("gpu_case_clearance", sizeMatch ? PASSED : INCOMPATIBLE,
                        sizeMatch ? "显卡长度满足机箱限长" : "显卡长度超过机箱限长"));
            }
        }

        if (board != null && computerCase != null) {
            String formFactor = HardwareCatalogService.string(board, "formFactor");
            Object supported = computerCase.get("supportedFormFactors");
            if (formFactor.isBlank() || !(supported instanceof List<?> list) || list.isEmpty()) {
                checks.add(check("motherboard_case_form_factor", NEEDS_VERIFICATION,
                        "主板板型或机箱支持板型参数缺失，待核实"));
            } else {
                boolean formMatch = list.stream()
                        .anyMatch(value -> String.valueOf(value).equalsIgnoreCase(formFactor));
                checks.add(check("motherboard_case_form_factor", formMatch ? PASSED : INCOMPATIBLE,
                        formMatch ? "主板板型适配机箱" : "主板板型不在机箱支持范围内"));
            }
        }

        if (cpu != null && gpu != null && power != null) {
            if (!hasPositiveInteger(cpu, "tdpW") || !hasPositiveInteger(gpu, "powerW")
                    || !hasPositiveInteger(power, "ratedPowerW")) {
                checks.add(check("power_headroom", NEEDS_VERIFICATION,
                        "CPU TDP、显卡功耗或电源额定功率缺失，功率余量待核实"));
            } else {
                int estimatedPower = HardwareCatalogService.integer(cpu, "tdpW", 0)
                        + HardwareCatalogService.integer(gpu, "powerW", 0) + 150;
                int safePower = (int) Math.ceil(estimatedPower * 1.3);
                int ratedPower = HardwareCatalogService.integer(power, "ratedPowerW", 0);
                int recommendedPower = HardwareCatalogService.integer(gpu, "recommendedPsuW", safePower);
                int requiredPower = Math.max(safePower, recommendedPower);
                boolean powerMatch = ratedPower >= requiredPower;
                checks.add(check("power_headroom", powerMatch ? PASSED : INCOMPATIBLE,
                        powerMatch ? "电源额定功率满足模拟负载估算与余量"
                                : "电源额定功率不足，建议至少 " + requiredPower + "W"));
            }
        }

        if (cpu != null && gpu != null) {
            double cpuScore = HardwareCatalogService.decimal(cpu, "gamingScore", 1);
            double gpuScore = HardwareCatalogService.decimal(gpu, "gamingScore", 1);
            double ratio = cpuScore / Math.max(gpuScore, 0.1);
            String balance = ratio < 0.75 ? "CPU相对偏弱，游戏场景可能受CPU限制"
                    : ratio > 1.35 ? "GPU相对偏弱，游戏场景可能受显卡限制"
                    : "CPU 与 GPU 的模拟游戏评分较均衡";
            checks.add(check("performance_balance", PASSED,
                    balance + "；该判断基于目录演示评分，不是实测瓶颈结论"));
        }

        if (cpu != null && cooler != null) {
            if (!hasPositiveInteger(cpu, "tdpW") || !hasPositiveInteger(cooler, "maxTdpW")) {
                checks.add(check("cooling_capacity", NEEDS_VERIFICATION,
                        "CPU TDP 或散热器标称能力缺失，散热能力待核实"));
            } else {
                int cpuTdp = HardwareCatalogService.integer(cpu, "tdpW", 0);
                int coolerTdp = HardwareCatalogService.integer(cooler, "maxTdpW", 0);
                boolean coolerMatch = coolerTdp >= cpuTdp;
                checks.add(check("cooling_capacity", coolerMatch ? PASSED : INCOMPATIBLE,
                        coolerMatch ? "散热器标称能力覆盖 CPU TDP" : "散热器标称能力低于 CPU TDP"));
            }
            Object supported = cooler.get("supportedSockets");
            String socket = HardwareCatalogService.string(cpu, "socket");
            if (socket.isBlank() || !(supported instanceof List<?> list) || list.isEmpty()) {
                checks.add(check("cooler_socket", NEEDS_VERIFICATION,
                        "CPU 插槽或散热器支持插槽参数缺失，扣具适配待核实"));
            } else {
                boolean socketMatch = list.stream()
                        .anyMatch(value -> String.valueOf(value).equalsIgnoreCase(socket));
                checks.add(check("cooler_socket", socketMatch ? PASSED : INCOMPATIBLE,
                        socketMatch ? "散热器扣具适配 CPU 插槽" : "散热器未声明支持该 CPU 插槽"));
            }
        }

        boolean incompatible = checks.stream().anyMatch(item -> INCOMPATIBLE.equals(item.get("status")));
        boolean needsVerification = checks.stream()
                .anyMatch(item -> NEEDS_VERIFICATION.equals(item.get("status")));
        String status = incompatible ? "incompatible"
                : needsVerification ? "needs_verification" : "compatible";
        return Map.of(
                "status", status,
                "statusLabel", statusLabel(status),
                "compatible", "compatible".equals(status),
                "verificationRequired", needsVerification,
                "checks", checks,
                "components", parts,
                "dataSource", "MOCK"
        );
    }

    private static boolean hasPositiveInteger(Map<String, Object> item, String field) {
        Object value = item.get(field);
        if (value instanceof Number number) return number.intValue() > 0;
        try {
            return value != null && Integer.parseInt(String.valueOf(value)) > 0;
        } catch (NumberFormatException ignored) {
            return false;
        }
    }

    private static Map<String, Object> check(String name, String status, String message) {
        return Map.of(
                "name", name,
                "status", status,
                "statusLabel", statusLabel(status),
                "passed", PASSED.equals(status),
                "message", message
        );
    }

    private static String statusLabel(String status) {
        return switch (status) {
            case PASSED, "compatible" -> "已验证兼容";
            case INCOMPATIBLE, "incompatible" -> "明确不兼容";
            case NEEDS_VERIFICATION, "needs_verification" -> "待核实";
            default -> "待核实";
        };
    }
}
