import { Controller, Post, Body } from '@nestjs/common';
import { LogAnalysisService } from '../service/log-analysis.service';

@Controller('logs')
export class LogAnalysisController {
  constructor(private readonly logService: LogAnalysisService) {}

  @Post('upload')
  async uploadLogs(@Body() body: { logs: string[] }) {
    console.log('Received logs:', body.logs);
    return this.logService.analyzeLogs(body.logs);
  }
}
