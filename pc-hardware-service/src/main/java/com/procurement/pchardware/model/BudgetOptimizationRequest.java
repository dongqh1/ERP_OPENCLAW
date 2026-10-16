package com.procurement.pchardware.model;

import java.math.BigDecimal;
import java.util.List;

public record BudgetOptimizationRequest(
        BigDecimal budget,
        String useCase,
        String resolution,
        Integer targetFps,
        Integer minGpuVramGb,
        String conditionPreference,
        List<KeepComponent> keepComponents) {}
