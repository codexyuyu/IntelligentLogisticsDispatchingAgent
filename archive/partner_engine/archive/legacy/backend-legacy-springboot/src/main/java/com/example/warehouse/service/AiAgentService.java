package com.example.warehouse.service;

import com.example.warehouse.entity.Inventory;
import com.example.warehouse.entity.Product;
import com.example.warehouse.entity.WarningRecord;
import com.example.warehouse.mapper.InventoryMapper;
import com.example.warehouse.mapper.ProductMapper;
import com.example.warehouse.mapper.WarningMapper;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.stream.Collectors;

@Service
public class AiAgentService {
    private final InventoryMapper inventoryMapper;
    private final ProductMapper productMapper;
    private final WarningMapper warningMapper;
    private final DeepSeekClient deepSeekClient;

    public AiAgentService(InventoryMapper inventoryMapper, ProductMapper productMapper, WarningMapper warningMapper, DeepSeekClient deepSeekClient) {
        this.inventoryMapper = inventoryMapper;
        this.productMapper = productMapper;
        this.warningMapper = warningMapper;
        this.deepSeekClient = deepSeekClient;
    }

    public Map<String, Object> chat(String question) {
        String context = buildWarehouseContext();
        String systemPrompt = "你是智能仓储系统的 AI Agent。只能基于给定仓库实时数据和规则回答。回答要短、清楚、适合高中生理解。\n" + context;
        String aiAnswer = deepSeekClient.chat(systemPrompt, question);
        if (aiAnswer != null && !aiAnswer.startsWith("DeepSeek API 调用失败")) {
            return Map.of("mode", "DEEPSEEK", "answer", aiAnswer, "context", context);
        }
        String local = localRuleAnswer(question);
        if (aiAnswer != null && aiAnswer.startsWith("DeepSeek API 调用失败")) {
            local = aiAnswer + "\n\n本地规则回答：\n" + local;
        }
        return Map.of("mode", "LOCAL_RULE_RAG", "answer", local, "context", context);
    }

    private String buildWarehouseContext() {
        List<Inventory> inventories = inventoryMapper.findAllDetail();
        List<WarningRecord> warnings = warningMapper.findOpen();
        String inventoryText = inventories.stream()
                .map(i -> i.getProductName() + "(" + i.getSku() + ") 在 " + i.getShelfCode() + " 第 " + i.getLayerNo() + " 层，数量 " + i.getQuantity())
                .collect(Collectors.joining("；"));
        String warningText = warnings.stream()
                .map(w -> w.getMessage() + "；建议：" + w.getSuggestion())
                .collect(Collectors.joining("；"));
        return "【仓库业务规则】低于安全库存要预警；入库推荐优先考虑品类匹配、容量充足、靠近出库口；出库路径采用起点-货架-出口。\n"
                + "【实时库存】" + (inventoryText.isBlank() ? "暂无库存" : inventoryText) + "\n"
                + "【当前预警】" + (warningText.isBlank() ? "暂无未处理预警" : warningText);
    }

    private String localRuleAnswer(String question) {
        String q = question.toLowerCase(Locale.ROOT);
        if (q.contains("库存") || q.contains("在哪") || q.contains("查询")) {
            List<Inventory> inventories = inventoryMapper.findAllDetail();
            return "我查到当前库存位置如下：\n" + inventories.stream()
                    .map(i -> "- " + i.getProductName() + "：" + i.getShelfCode() + " 第 " + i.getLayerNo() + " 层，数量 " + i.getQuantity())
                    .collect(Collectors.joining("\n"));
        }
        if (q.contains("补货") || q.contains("预警")) {
            List<WarningRecord> warnings = warningMapper.findOpen();
            if (warnings.isEmpty()) return "当前没有未处理预警，暂时不需要补货。";
            return "当前建议优先处理这些补货/预警：\n" + warnings.stream()
                    .map(w -> "- " + w.getMessage() + "。" + w.getSuggestion())
                    .collect(Collectors.joining("\n"));
        }
        if (q.contains("入库") || q.contains("货位") || q.contains("推荐")) {
            List<Product> products = productMapper.findAll();
            return "入库推荐规则是：先找同品类货架，再看剩余容量是否足够，最后让高周转商品靠近出库口。你可以在“入库管理”页面选择商品和数量，系统会自动给出推荐货架。当前商品包括："
                    + products.stream().map(Product::getName).collect(Collectors.joining("、"));
        }
        if (q.contains("路径") || q.contains("出库") || q.contains("agv")) {
            return "出库路径规则是：从起点出发，沿网格走到目标货架，再走到出库口。前端会用黄色线高亮路径，并用小球模拟 AGV/叉车移动。";
        }
        if (q.contains("异常") || q.contains("原因")) {
            return "异常原因通常分为三类：库存低于安全库存、货架容量不足、商品放错品类货架。本 MVP 会先实现库存低预警，后续可以加入 RFID/扫码模拟账实不符。";
        }
        return "我可以回答库存查询、补货建议、入库货位推荐、出库路径说明和异常原因分析。你可以试着问：每日鲜语低温鲜牛奶库存在哪？哪些商品需要补货？为什么系统推荐 冷链鲜食货架-F01？";
    }
}
