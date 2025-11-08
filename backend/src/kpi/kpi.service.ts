import { Injectable } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';

@Injectable()
export class KpiService {
  private readonly ENERGY_PRICE_PER_KWH = 5.0;

  constructor(private prisma: PrismaService) {}

  async calculateEnpi(periodDays: number = 30) {
    const data = await this.prisma.cleanData.findMany({
      where: {
        timestamp: {
          gte: new Date(Date.now() - periodDays * 24 * 60 * 60 * 1000),
        },
      },
    });

    if (data.length === 0) return {};

    const avgPower = data.reduce((sum, d) => sum + d.powerKwh, 0) / data.length;
    const avgLoad = data.reduce((sum, d) => sum + d.loadPercent, 0) / data.length;

    const enpi = avgLoad > 0 ? avgPower / avgLoad : 0;
    const baselineEnpi = enpi * 1.05;
    const deviationPercent = ((enpi - baselineEnpi) / baselineEnpi) * 100;

    return {
      enpi: parseFloat(enpi.toFixed(4)),
      baseline_enpi: parseFloat(baselineEnpi.toFixed(4)),
      deviation_percent: parseFloat(deviationPercent.toFixed(2)),
      period_days: periodDays,
      avg_power_kwh: parseFloat(avgPower.toFixed(2)),
      avg_load_percent: parseFloat(avgLoad.toFixed(2)),
    };
  }

  async calculateExcessConsumption(periodDays: number = 30) {
    const data = await this.prisma.cleanData.findMany({
      where: {
        timestamp: {
          gte: new Date(Date.now() - periodDays * 24 * 60 * 60 * 1000),
        },
      },
    });

    if (data.length === 0) return {};

    const totalActual = data.reduce((sum, d) => sum + d.powerKwh, 0);
    const avgActual = totalActual / data.length;
    const baselineKwh = avgActual * data.length;
    const excessKwh = totalActual - baselineKwh;
    const excessPercent = (excessKwh / baselineKwh) * 100;

    const anomalies = await this.prisma.anomaly.findMany({
      where: {
        timestamp: {
          gte: new Date(Date.now() - periodDays * 24 * 60 * 60 * 1000),
        },
      },
    });

    const anomaliesExcess = anomalies.reduce((sum, a) => sum + (a.excessKwh || 0), 0);

    return {
      total_consumption_kwh: parseFloat(totalActual.toFixed(2)),
      excess_kwh: parseFloat(excessKwh.toFixed(2)),
      excess_percent: parseFloat(excessPercent.toFixed(2)),
      anomalies_excess_kwh: parseFloat(anomaliesExcess.toFixed(2)),
      period_days: periodDays,
    };
  }

  async calculateEfficiency(periodDays: number = 30) {
    const data = await this.prisma.cleanData.findMany({
      where: {
        timestamp: {
          gte: new Date(Date.now() - periodDays * 24 * 60 * 60 * 1000),
        },
      },
    });

    if (data.length === 0) return {};

    const efficiencies = data.map((d) => d.efficiency || 0).filter((e) => e > 0);
    const avgEfficiency = efficiencies.reduce((sum, e) => sum + e, 0) / efficiencies.length;
    const minEfficiency = Math.min(...efficiencies);
    const maxEfficiency = Math.max(...efficiencies);

    return {
      avg_efficiency: parseFloat(avgEfficiency.toFixed(2)),
      min_efficiency: parseFloat(minEfficiency.toFixed(2)),
      max_efficiency: parseFloat(maxEfficiency.toFixed(2)),
      period_days: periodDays,
    };
  }

  async calculateEconomicEffect(optimizationPercent: number = 1.0, periodDays: number = 30) {
    const excessData = await this.calculateExcessConsumption(periodDays);
    const excessKwh = excessData.excess_kwh || 0;

    if (excessKwh <= 0) {
      return {
        savings_kwh: 0,
        savings_rub: 0,
        optimization_percent: optimizationPercent,
        period_days: periodDays,
      };
    }

    const savingsKwh = excessKwh * (optimizationPercent / 100);
    const savingsRub = savingsKwh * this.ENERGY_PRICE_PER_KWH;
    const annualSavingsKwh = savingsKwh * (365 / periodDays);
    const annualSavingsRub = annualSavingsKwh * this.ENERGY_PRICE_PER_KWH;

    return {
      savings_kwh: parseFloat(savingsKwh.toFixed(2)),
      savings_rub: parseFloat(savingsRub.toFixed(2)),
      annual_savings_kwh: parseFloat(annualSavingsKwh.toFixed(2)),
      annual_savings_rub: parseFloat(annualSavingsRub.toFixed(2)),
      optimization_percent: optimizationPercent,
      period_days: periodDays,
      energy_price_per_kwh: this.ENERGY_PRICE_PER_KWH,
    };
  }

  async getAllKpis(periodDays: number = 30, optimizationPercent: number = 1.0) {
    return {
      enpi: await this.calculateEnpi(periodDays),
      excess_consumption: await this.calculateExcessConsumption(periodDays),
      efficiency: await this.calculateEfficiency(periodDays),
      economic_effect: await this.calculateEconomicEffect(optimizationPercent, periodDays),
      period_days: periodDays,
      timestamp: new Date().toISOString(),
    };
  }
}

