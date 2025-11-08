import { Injectable } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';

@Injectable()
export class AiService {
  constructor(private prisma: PrismaService) {}

  async runFullAnalysis(forecastPeriods: number = 7) {
    try {
      // Загрузка данных для обучения
      const trainingData = await this.prisma.cleanData.findMany({
        where: {
          timestamp: {
            gte: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000),
          },
        },
        orderBy: { timestamp: 'asc' },
      });

      if (trainingData.length === 0) {
        return { status: 'error', message: 'Недостаточно данных для обучения' };
      }

      // Обучение модели и прогнозирование
      const forecast = await this.generateForecast(trainingData, forecastPeriods);

      // Обнаружение аномалий
      const anomalies = this.detectAnomalies(trainingData);

      // Сохранение прогноза
      for (const f of forecast) {
        await this.prisma.forecast.create({ data: f });
      }

      // Сохранение аномалий
      for (const anomaly of anomalies) {
        await this.prisma.anomaly.create({ data: anomaly });
      }

      return {
        status: 'success',
        forecastPeriods,
        anomaliesCount: anomalies.length,
        forecast,
      };
    } catch (error) {
      return { status: 'error', message: error.message };
    }
  }

  async getForecast(periods: number = 7) {
    const forecast = await this.prisma.forecast.findMany({
      take: periods,
      orderBy: { timestamp: 'desc' },
    });

    return {
      status: 'success',
      forecast: forecast.map((f) => ({
        ds: f.timestamp,
        yhat: f.predictedKwh,
        yhat_lower: f.confidenceLower,
        yhat_upper: f.confidenceUpper,
      })),
    };
  }

  async getAnomalies(days: number = 30) {
    const anomalies = await this.prisma.anomaly.findMany({
      where: {
        timestamp: {
          gte: new Date(Date.now() - days * 24 * 60 * 60 * 1000),
        },
      },
    });

    return {
      status: 'success',
      anomalies: anomalies.map((a) => ({
        timestamp: a.timestamp,
        power_kwh: a.powerKwh,
        excess_kwh: a.excessKwh,
        cause: a.cause,
      })),
    };
  }

  private async generateForecast(data: any[], periods: number) {
    // Упрощённый прогноз (в реальности использовать Prophet или другую библиотеку)
    const avgPower = data.reduce((sum, d) => sum + d.powerKwh, 0) / data.length;
    const forecast = [];

    for (let i = 0; i < periods; i++) {
      const date = new Date();
      date.setDate(date.getDate() + i + 1);
      forecast.push({
        timestamp: date,
        predictedKwh: avgPower * (1 + Math.random() * 0.1 - 0.05),
        confidenceLower: avgPower * 0.9,
        confidenceUpper: avgPower * 1.1,
      });
    }

    return forecast;
  }

  private detectAnomalies(data: any[]) {
    const avgPower = data.reduce((sum, d) => sum + d.powerKwh, 0) / data.length;
    const stdPower = Math.sqrt(
      data.reduce((sum, d) => sum + Math.pow(d.powerKwh - avgPower, 2), 0) / data.length,
    );

    const threshold = 2 * stdPower;
    const anomalies = [];

    for (const record of data) {
      if (Math.abs(record.powerKwh - avgPower) > threshold) {
        anomalies.push({
          timestamp: record.timestamp,
          powerKwh: record.powerKwh,
          excessKwh: Math.max(0, record.powerKwh - avgPower),
          cause: record.powerKwh > avgPower ? 'high_consumption' : 'low_consumption',
          description: 'Anomaly detected',
        });
      }
    }

    return anomalies;
  }
}

