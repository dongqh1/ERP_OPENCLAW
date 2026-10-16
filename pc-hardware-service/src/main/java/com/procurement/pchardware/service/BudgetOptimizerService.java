package com.procurement.pchardware.service;

import com.procurement.pchardware.model.BudgetOptimizationRequest;
import com.procurement.pchardware.model.KeepComponent;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

@Service
public class BudgetOptimizerService {
    private static final List<String> BUILD_TYPES =
            List.of("CPU", "GPU", "MOTHERBOARD", "MEMORY", "STORAGE", "COOLER", "POWER", "CASE");

    private final HardwareCatalogService catalog;
    private final CompatibilityService compatibility;

    public BudgetOptimizerService(HardwareCatalogService catalog, CompatibilityService compatibility) {
        this.catalog = catalog;
        this.compatibility = compatibility;
    }

    public Map<String, Object> optimize(BudgetOptimizationRequest request) {
        if (request.budget() == null || request.budget().signum() <= 0) {
            return Map.of("status", "invalid_request", "message", "预算必须大于 0", "dataSource", "MOCK");
        }

        Map<String, Map<String, Object>> fixed = new HashMap<>();
        Set<String> ownedTypes = new HashSet<>();
        List<KeepComponent> keeps = request.keepComponents() == null ? List.of() : request.keepComponents();
        for (KeepComponent keep : keeps) {
            if (keep.type() == null || keep.keyword() == null) continue;
            String type = normalizeType(keep.type());
            if (!BUILD_TYPES.contains(type)) {
                return Map.of(
                        "status", "invalid_kept_component_type",
                        "message", "不支持保留该硬件类别：" + keep.type(),
                        "supportedTypes", BUILD_TYPES,
                        "dataSource", "MOCK"
                );
            }
            if (fixed.containsKey(type)) {
                return Map.of(
                        "status", "duplicate_kept_component_type",
                        "message", "一套配置只能保留一个 " + type + "，请明确指定要使用的型号。",
                        "dataSource", "MOCK"
                );
            }
            Map<String, Object> item = catalog.find(
                    type,
                    keep.keyword(),
                    keep.owned() ? "any" : request.conditionPreference());
            if (item == null) {
                return Map.of(
                        "status", "component_not_found",
                        "message", "无法在模拟硬件目录中找到必须保留的 " + keep.type() + "：" + keep.keyword(),
                        "dataSource", "MOCK"
                );
            }
            fixed.put(type, item);
            if (keep.owned()) ownedTypes.add(type);
        }

        Integer minGpuVramGb = request.minGpuVramGb();
        Map<String, Object> fixedGpu = fixed.get("GPU");
        if (minGpuVramGb != null && fixedGpu != null
                && HardwareCatalogService.integer(fixedGpu, "vramGb", 0) < minGpuVramGb) {
            return Map.of(
                    "status", "constraint_conflict",
                    "message", "指定显卡显存低于用户要求的下限，不能生成满足条件的配置。",
                    "minGpuVramGb", minGpuVramGb,
                    "selectedGpuVramGb", HardwareCatalogService.integer(fixedGpu, "vramGb", 0),
                    "dataSource", "MOCK"
            );
        }

        List<List<Map<String, Object>>> choices = new ArrayList<>();
        for (String type : BUILD_TYPES) {
            Map<String, Object> fixedItem = fixed.get(type);
            List<Map<String, Object>> options = fixedItem == null
                    ? catalog.byTypeAndCondition(type, request.conditionPreference())
                    : List.of(fixedItem);
            if (options.isEmpty()) {
                return Map.of("status", "catalog_incomplete",
                        "message", "模拟目录没有符合所选新旧要求的 " + type + " 候选", "dataSource", "MOCK");
            }
            choices.add(options);
        }

        Candidate best = new Candidate();
        for (Map<String, Object> cpu : choices.get(0))
        for (Map<String, Object> gpu : choices.get(1))
        for (Map<String, Object> board : choices.get(2))
        for (Map<String, Object> memory : choices.get(3))
        for (Map<String, Object> storage : choices.get(4))
        for (Map<String, Object> cooler : choices.get(5))
        for (Map<String, Object> power : choices.get(6))
        for (Map<String, Object> computerCase : choices.get(7)) {
            if (minGpuVramGb != null
                    && HardwareCatalogService.integer(gpu, "vramGb", 0) < minGpuVramGb) continue;

            Map<String, String> selected = Map.of(
                    "CPU", HardwareCatalogService.string(cpu, "id"),
                    "GPU", HardwareCatalogService.string(gpu, "id"),
                    "MOTHERBOARD", HardwareCatalogService.string(board, "id"),
                    "MEMORY", HardwareCatalogService.string(memory, "id"),
                    "STORAGE", HardwareCatalogService.string(storage, "id"),
                    "COOLER", HardwareCatalogService.string(cooler, "id"),
                    "POWER", HardwareCatalogService.string(power, "id"),
                    "CASE", HardwareCatalogService.string(computerCase, "id")
            );
            Map<String, Object> checks = compatibility.check(selected);
            // Unknown specifications remain candidates with a pending status.
            // Only a known incompatibility disqualifies a configuration.
            if ("incompatible".equals(checks.get("status"))) continue;

            BigDecimal catalogTotal = sum(selected.values().stream().map(catalog::detail).toList());
            BigDecimal purchaseTotal = BigDecimal.ZERO;
            for (String type : BUILD_TYPES) {
                if (!ownedTypes.contains(type)) {
                    purchaseTotal = purchaseTotal.add(price(catalog.detail(selected.get(type))));
                }
            }
            if (purchaseTotal.compareTo(request.budget()) > 0) continue;

            double score = score(request, cpu, gpu);
            if (isBestValue(request.conditionPreference())) {
                score = score / Math.max(0.5, purchaseTotal.doubleValue() / 1000.0);
            }
            if (score > best.score
                    || (Double.compare(score, best.score) == 0
                    && purchaseTotal.compareTo(best.purchaseTotal) < 0)) {
                best = new Candidate(selected, checks, catalogTotal, purchaseTotal, score);
            }
        }

        if (best.selected == null) {
            String message = minGpuVramGb == null
                    ? "在当前模拟目录中没有找到同时满足预算和兼容性约束的完整配置。可提高预算或调整保留硬件。"
                    : "在当前模拟目录中没有找到同时满足预算、兼容性和显卡显存下限（至少 "
                    + minGpuVramGb + "GB）的完整配置。可提高预算或调整显存要求。";
            return Map.of(
                    "status", "no_compatible_build_within_budget",
                    "message", message,
                    "budget", request.budget(),
                    "minGpuVramGb", minGpuVramGb == null ? 0 : minGpuVramGb,
                    "keepComponents", keeps,
                    "dataSource", "MOCK"
            );
        }

        List<Map<String, Object>> build = new ArrayList<>();
        for (String type : BUILD_TYPES) {
            Map<String, Object> item = catalog.detail(best.selected.get(type));
            Map<String, Object> row = new HashMap<>(item);
            boolean owned = ownedTypes.contains(type);
            row.put("owned", owned);
            row.put("purchasePrice", owned ? BigDecimal.ZERO : price(item));
            build.add(row);
        }

        Map<String, Object> result = new HashMap<>();
        result.put("status", "success");
        result.put("build", build);
        result.put("compatible", best.checks.get("compatible"));
        result.put("compatibilityStatus", best.checks.get("status"));
        result.put("compatibilityStatusLabel", best.checks.get("statusLabel"));
        result.put("verificationRequired", best.checks.get("verificationRequired"));
        result.put("compatibility", best.checks);
        result.put("catalogTotal", best.catalogTotal);
        // 向后兼容旧前端/调用方；Agent 提示词要求只展示 catalogTotal。
        result.put("marketTotal", best.catalogTotal);
        result.put("purchaseTotal", best.purchaseTotal);
        result.put("budget", request.budget());
        result.put("budgetRemaining", request.budget().subtract(best.purchaseTotal));
        result.put("useCase", request.useCase() == null ? "未指定" : request.useCase());
        result.put("resolution", request.resolution() == null ? "未指定" : request.resolution());
        result.put("targetFps", request.targetFps() == null ? 60 : request.targetFps());
        result.put("conditionPreference",
                request.conditionPreference() == null ? "any" : request.conditionPreference());
        result.put("minGpuVramGb", minGpuVramGb == null ? 0 : minGpuVramGb);
        result.put("performanceTier", performanceTier(request.useCase(), request.resolution(),
                catalog.detail(best.selected.get("GPU"))));
        result.put("performanceNote", "性能定位为模拟评分，不是实测游戏帧率、AI 训练速度或基准测试结果。");
        result.put("dataSource", "MOCK");
        return result;
    }

    private static BigDecimal sum(List<Map<String, Object>> items) {
        return items.stream().map(BudgetOptimizerService::price).reduce(BigDecimal.ZERO, BigDecimal::add);
    }

    private static BigDecimal price(Map<String, Object> item) {
        if (item == null) return BigDecimal.ZERO;
        Object value = item.get("price");
        if (value instanceof BigDecimal decimal) return decimal;
        if (value instanceof Number number) return BigDecimal.valueOf(number.doubleValue());
        try {
            return new BigDecimal(String.valueOf(value));
        } catch (Exception ignored) {
            return BigDecimal.ZERO;
        }
    }

    private static double score(BudgetOptimizationRequest request,
                                Map<String, Object> cpu,
                                Map<String, Object> gpu) {
        String usage = HardwareCatalogService.normalize(request.useCase());
        boolean gaming = isGamingUseCase(usage);
        double gpuScore = HardwareCatalogService.decimal(gpu, "gamingScore", 1);
        double cpuScore = HardwareCatalogService.decimal(cpu, gaming ? "gamingScore" : "officeScore", 1);
        if (!gaming) return cpuScore * 0.7 + gpuScore * 0.3;

        String resolution = HardwareCatalogService.normalize(request.resolution());
        double gpuWeight = resolution.contains("2k") || resolution.contains("1440")
                || resolution.contains("4k") || resolution.contains("2160") ? 0.8 : 0.72;
        int targetFps = request.targetFps() == null ? 60 : request.targetFps();
        if (targetFps >= 120) gpuWeight -= 0.06;
        double cpuWeight = 1.0 - gpuWeight;
        return gpuScore * gpuWeight + cpuScore * cpuWeight;
    }

    private static boolean isBestValue(String preference) {
        String normalized = HardwareCatalogService.normalize(preference);
        return normalized.contains("value") || normalized.contains("性价比");
    }

    private static String performanceTier(String useCase, String resolution, Map<String, Object> gpu) {
        String normalizedUseCase = HardwareCatalogService.normalize(useCase);
        boolean gaming = isGamingUseCase(normalizedUseCase);
        double score = HardwareCatalogService.decimal(gpu, "gamingScore", 1);
        if (!gaming) {
            if (normalizedUseCase.matches(".*(神经网络|ai|agent|lora|模型|训练|推理).*")) {
                return "AI 研发用途；目录未提供模型显存占用或训练速度基准";
            }
            return "日常办公演示档";
        }
        String requestedResolution = HardwareCatalogService.normalize(resolution);
        String tier = requestedResolution.contains("4k") || requestedResolution.contains("2160")
                ? "4K" : requestedResolution.contains("2k") || requestedResolution.contains("1440")
                ? "2K" : "1080p";
        String gameType = normalizedUseCase.matches(".*(瓦洛兰特|瓦罗兰特|valorant|电竞).*")
                ? "电竞游戏" : normalizedUseCase.matches(".*(大表哥|rdr|3a).*")
                ? "3A 游戏" : "游戏";
        String scoreTier = score >= 8.5 ? "高档" : score >= 7 ? "中档" : "入门档";
        return tier + "/" + gameType + "演示定位（" + scoreTier + "，非实测 FPS）";
    }

    private static boolean isGamingUseCase(String normalizedUseCase) {
        return normalizedUseCase.matches(".*(游戏|大表哥|rdr|3a|gaming|valorant|瓦洛兰特|瓦罗兰特|电竞).*");
    }

    private static String normalizeType(String type) {
        String value = type.toUpperCase(java.util.Locale.ROOT);
        return switch (value) {
            case "CPU", "处理器" -> "CPU";
            case "GPU", "显卡" -> "GPU";
            case "MOTHERBOARD", "主板" -> "MOTHERBOARD";
            case "MEMORY", "RAM", "内存" -> "MEMORY";
            case "STORAGE", "SSD", "硬盘" -> "STORAGE";
            case "COOLER", "散热", "散热器" -> "COOLER";
            case "POWER", "PSU", "电源" -> "POWER";
            case "CASE", "机箱" -> "CASE";
            default -> value;
        };
    }

    private static class Candidate {
        private Map<String, String> selected;
        private Map<String, Object> checks;
        private BigDecimal purchaseTotal = new BigDecimal("999999999");
        private double score = -1;
        private BigDecimal catalogTotal = BigDecimal.ZERO;

        private Candidate() {}

        private Candidate(Map<String, String> selected, Map<String, Object> checks,
                          BigDecimal catalogTotal, BigDecimal purchaseTotal, double score) {
            this.selected = selected;
            this.checks = checks;
            this.catalogTotal = catalogTotal;
            this.purchaseTotal = purchaseTotal;
            this.score = score;
        }
    }
}
