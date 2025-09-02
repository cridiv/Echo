import { Injectable, HttpException } from '@nestjs/common';

@Injectable()
export class LogAnalysisService {
  private readonly pythonAgentUrl = 'http://localhost:8001/analyze';

  async analyzeLogs(logs: string[]) {
    try {
      const response = await fetch(this.pythonAgentUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ logs }),
      });

      if (!response.ok) {
        throw new HttpException(
          `Python agent error: ${response.statusText}`,
          response.status,
        );
      }

      const data = await response.json();
      console.log('Analysis result from Python agent:', data);
      return data;
    } catch (error) {
      throw new HttpException(
        'Failed to reach Python agent',
        500,
      );
    }
  }
}
