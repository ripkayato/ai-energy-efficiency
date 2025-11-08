import { Controller, Get, Post, Query, UseGuards } from '@nestjs/common';
import { AiService } from './ai.service';
import { JwtAuthGuard } from '../auth/guards/jwt-auth.guard';

@Controller('ai')
@UseGuards(JwtAuthGuard)
export class AiController {
  constructor(private readonly aiService: AiService) {}

  @Post('analyze')
  async analyze(@Query('forecastPeriods') forecastPeriods: string = '7') {
    return this.aiService.runFullAnalysis(parseInt(forecastPeriods));
  }

  @Get('forecast')
  async getForecast(@Query('periods') periods: string = '7') {
    return this.aiService.getForecast(parseInt(periods));
  }

  @Get('anomalies')
  async getAnomalies(@Query('days') days: string = '30') {
    return this.aiService.getAnomalies(parseInt(days));
  }
}

