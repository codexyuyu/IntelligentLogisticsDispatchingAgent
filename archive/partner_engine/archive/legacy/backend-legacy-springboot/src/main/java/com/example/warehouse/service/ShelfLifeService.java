package com.example.warehouse.service;

import com.example.warehouse.entity.Product;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.math.RoundingMode;

@Service
public class ShelfLifeService {

    public PredictionResult predict(Product product,
                                    BigDecimal initialQualityScore,
                                    BigDecimal temperature,
                                    BigDecimal humidity,
                                    BigDecimal storedDays) {
        BigDecimal baseDays = BigDecimal.valueOf(product.getBaseShelfLifeDays() == null ? 3 : product.getBaseShelfLifeDays());
        BigDecimal factor = BigDecimal.ONE;

        if (initialQualityScore != null) {
            BigDecimal qualityFactor = initialQualityScore.divide(new BigDecimal("100"), 4, RoundingMode.HALF_UP);
            factor = factor.multiply(qualityFactor.min(BigDecimal.ONE).max(new BigDecimal("0.30")));
        }

        boolean tempAbnormal = false;
        if (temperature != null && product.getMinTemperature() != null && product.getMaxTemperature() != null) {
            if (temperature.compareTo(product.getMinTemperature()) < 0 || temperature.compareTo(product.getMaxTemperature()) > 0) {
                tempAbnormal = true;
                factor = factor.multiply(new BigDecimal("0.70"));
            }
        }

        if (humidity != null && product.getMinHumidity() != null && product.getMaxHumidity() != null) {
            if (humidity.compareTo(product.getMinHumidity()) < 0 || humidity.compareTo(product.getMaxHumidity()) > 0) {
                factor = factor.multiply(new BigDecimal("0.85"));
            }
        }

        BigDecimal predictedDays = baseDays.multiply(factor).setScale(2, RoundingMode.HALF_UP);
        BigDecimal usedDays = storedDays == null ? BigDecimal.ZERO : storedDays;
        BigDecimal remainingDays = predictedDays.subtract(usedDays).setScale(2, RoundingMode.HALF_UP);
        BigDecimal freshnessScore = remainingDays.divide(baseDays, 4, RoundingMode.HALF_UP)
                .multiply(new BigDecimal("100"))
                .min(new BigDecimal("100"))
                .max(BigDecimal.ZERO)
                .setScale(2, RoundingMode.HALF_UP);

        String status;
        if (tempAbnormal) {
            status = "TEMP_ABNORMAL";
        } else if (remainingDays.compareTo(BigDecimal.ZERO) <= 0) {
            status = "EXPIRED";
        } else if (remainingDays.compareTo(new BigDecimal("1.5")) <= 0) {
            status = "EXPIRING";
        } else {
            status = "NORMAL";
        }
        return new PredictionResult(predictedDays, remainingDays, freshnessScore, status);
    }

    public static class PredictionResult {
        private final BigDecimal predictedStorageDays;
        private final BigDecimal remainingDays;
        private final BigDecimal freshnessScore;
        private final String status;

        public PredictionResult(BigDecimal predictedStorageDays, BigDecimal remainingDays, BigDecimal freshnessScore, String status) {
            this.predictedStorageDays = predictedStorageDays;
            this.remainingDays = remainingDays;
            this.freshnessScore = freshnessScore;
            this.status = status;
        }

        public BigDecimal getPredictedStorageDays() { return predictedStorageDays; }
        public BigDecimal getRemainingDays() { return remainingDays; }
        public BigDecimal getFreshnessScore() { return freshnessScore; }
        public String getStatus() { return status; }
    }
}
