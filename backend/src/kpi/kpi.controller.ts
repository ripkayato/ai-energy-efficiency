import { Controller, Get, Query, UseGuards } from '@nestjs/common';
import { KpiService } from './kpi.service';
import { JwtAuthGuard } from '../auth/guards/jwt-auth.guard';

@Controller('kpi')
@UseGuards(JwtAuthGuard)
export class KpiController {
  constructor(private readonly kpiService: KpiService) {}

  @Get('enpi')
  async getEnpi(@Query('period_days') periodDays: string = '30') {
    return this.kpiService.calculateEnpi(parseInt(periodDays));
  }

  @Get('excess')
  async getExcess(@Query('period_days') periodDays: string = '30') {
    return this.kpiService.calculateExcessConsumption(parseInt(periodDays));
  }

  @Get('efficiency')
  async getEfficiency(@Query('period_days') periodDays: string = '30') {
    return this.kpiService.calculateEfficiency(parseInt(periodDays));
  }

  @Get('economic')
  async getEconomic(
    @Query('optimization_percent') optimizationPercent: string = '1.0',
    @Query('period_days') periodDays: string = '30',
  ) {
    return this.kpiService.calculateEconomicEffect(
      parseFloat(optimizationPercent),
      parseInt(periodDays),
    );
  }

  @Get('all')
  async getAll(
    @Query('period_days') periodDays: string = '30',
    @Query('optimization_percent') optimizationPercent: string = '1.0',
  ) {
    return this.kpiService.getAllKpis(parseInt(periodDays), parseFloat(optimizationPercent));
  }
}

