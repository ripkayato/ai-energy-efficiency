import { Controller, Post, Get, UseGuards, Body } from '@nestjs/common';
import { EtlService } from './etl.service';
import { JwtAuthGuard } from '../auth/guards/jwt-auth.guard';

@Controller('etl')
@UseGuards(JwtAuthGuard)
export class EtlController {
  constructor(private readonly etlService: EtlService) {}

  @Post('process')
  async process(@Body('filePath') filePath?: string) {
    return this.etlService.process(filePath || '/shared/raw_data.json');
  }

  @Get('status')
  getStatus() {
    return { status: 'ready' };
  }
}

