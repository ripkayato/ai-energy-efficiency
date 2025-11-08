import { Module } from '@nestjs/common';
import { EtlController } from './etl.controller';
import { EtlService } from './etl.service';

@Module({
  controllers: [EtlController],
  providers: [EtlService],
  exports: [EtlService],
})
export class EtlModule {}

