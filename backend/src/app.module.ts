import { Module } from '@nestjs/common';
import { AppController } from './app.controller';
import { AppService } from './app.service';
import { EtlModule } from './etl/etl.module';
import { AiModule } from './ai/ai.module';
import { KpiModule } from './kpi/kpi.module';
import { AuthModule } from './auth/auth.module';
import { PrismaModule } from './prisma/prisma.module';

@Module({
  imports: [PrismaModule, EtlModule, AiModule, KpiModule, AuthModule],
  controllers: [AppController],
  providers: [AppService],
})
export class AppModule {}

