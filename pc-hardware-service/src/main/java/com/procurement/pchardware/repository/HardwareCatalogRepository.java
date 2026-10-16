package com.procurement.pchardware.repository;

import java.util.List;
import java.util.Map;

/** 数据访问边界；未来可替换为 MySQL、ERP API 或外部商品源实现。 */
public interface HardwareCatalogRepository {
    List<Map<String, Object>> findAll();
}
