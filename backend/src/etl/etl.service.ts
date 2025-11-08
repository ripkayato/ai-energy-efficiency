import { Injectable } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';
import * as fs from 'fs';

@Injectable()
export class EtlService {
  constructor(private prisma: PrismaService) {}

  async process(filePath: string) {
    try {
      // Загрузка сырых данных
      const rawData = JSON.parse(fs.readFileSync(filePath, 'utf-8'));
      
      // Сохранение в raw_data
      for (const record of rawData) {
        await this.prisma.rawData.create({
          data: {
            timestamp: new Date(record.timestamp),
            installationId: record.installation_id || 'INST_001',
            powerKwh: record.power_kwh,
            loadPercent: record.load_percent,
            temperature: record.temp || record.temperature,
            pressure: record.pressure,
          },
        });
      }

      // Нормализация данных
      const cleanData = rawData
        .filter((r: any) => r.load_percent > 0 && r.power_kwh > 0)
        .map((r: any) => ({
          timestamp: new Date(r.timestamp),
          installationId: r.installation_id || 'INST_001',
          powerKwh: r.power_kwh,
          loadPercent: r.load_percent,
          temperature: r.temp || r.temperature,
          pressure: r.pressure,
          efficiency: r.load_percent / r.power_kwh * 100,
          specificConsumption: r.power_kwh / r.load_percent,
          isOutlier: false,
        }));

      // Сохранение в clean_data
      for (const record of cleanData) {
        await this.prisma.cleanData.create({ data: record });
      }

      return {
        status: 'success',
        rawRecords: rawData.length,
        cleanRecords: cleanData.length,
      };
    } catch (error) {
      return {
        status: 'error',
        message: error.message,
      };
    }
  }
}

