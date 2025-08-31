import os
import re
import json
from typing import List, Dict, Union
from datetime import datetime


class LogIngestor:
    def __init__(self, file_paths: Union[str, List[str]]):
        """
        :param file_paths: Either a single directory path (str) or
                           a list of log file paths (List[str]).
        """
        if isinstance(file_paths, str) and os.path.isdir(file_paths):
            # Load all files in a directory
            self.files = [
                os.path.join(file_paths, f)
                for f in os.listdir(file_paths)
                if f.endswith((".log", ".json"))
            ]
        elif isinstance(file_paths, list):
            self.files = file_paths
        else:
            raise ValueError("Pass a directory path or a list of file paths.")

    def ingest_logs(self) -> List[Dict]:
        """
        Reads logs from multiple files and normalizes them.
        Returns a list of structured log entries.
        """
        all_logs = []
        for file_path in self.files:
            if file_path.endswith(".json"):
                all_logs.extend(self._parse_json_logs(file_path))
            elif file_path.endswith(".log") or file_path.endswith(".txt"):
                all_logs.extend(self._parse_plain_logs(file_path))
            else:
                print(f"Skipping unsupported file: {file_path}")
        return all_logs

    def _parse_json_logs(self, file_path: str) -> List[Dict]:
        logs = []
        with open(file_path, "r") as f:
            for line in f:
                try:
                    logs.append(json.loads(line.strip()))
                except json.JSONDecodeError:
                    print(f"Invalid JSON in {file_path}: {line}")
        return logs

    def _parse_plain_logs(self, file_path: str) -> List[Dict]:
        logs = []
        with open(file_path, "r") as f:
            for line in f:
                logs.append(
                    {"raw": line.strip(), "source_file": os.path.basename(file_path)}
                )
        return logs


class LogCleaner:
    def __init__(self, redact_secrets=True):
        self.redact_secrets = redact_secrets

    def clean_line(self, line: str) -> str:
        # 1. Strip ANSI escape sequences (color codes)
        line = re.sub(r"\x1B\[[0-?]*[ -/]*[@-~]", "", line)

        # 2. Normalize whitespace
        line = re.sub(r"\s+", " ", line).strip()

        # 3. Redact sensitive tokens (optional)
        if self.redact_secrets:
            line = re.sub(r"Bearer\s+\S+", "Bearer [REDACTED]", line)
            line = re.sub(r"api[_-]?key=\S+", "api_key=[REDACTED]", line)
            line = re.sub(
                r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "[EMAIL]", line
            )

        return line

    def clean_logs(self, logs: str) -> str:
        """Takes raw log text and cleans it line by line."""
        cleaned_lines = [self.clean_line(line) for line in logs.splitlines()]
        return "\n".join([line for line in cleaned_lines if line])  # remove empty lines


class LogParser:
    def __init__(self):
        pass

    def parse_logs(self, line: str):
        pattern = r"^(?P<timestamp>\S+ \S+)\s+(?P<level>[A-Z]+)\s+(?P<message>.+)$"
        match = re.match(pattern, line)

        if not match:
            return None

        timestamp = datetime.strptime(match.group("timestamp"), "%Y-%m-%d %H:%M:%S")
        level = match.group("level")
        message = match.group("message")

        return {"timestamp": timestamp, "level": level, "message": message}

    def score_log(self, parsed_log: Dict):
        # Basic scoring based on log level
        level = parsed_log["level"]

        if level == "ERROR":
            score = 0.9
        elif level == "WARN":
            score = 0.6
        elif level == "INFO":
            score = 0.2
        else:
            score = 0.1

        parsed_log["score"] = score
        return parsed_log

    def batch_parse_and_score(self, log_lines: List[str]):
        results = []
        for line in log_lines:
            parsed = self.parse_logs(line)
            if parsed:
                scored = self.score_log(parsed)
                results.append(scored)
        return results


def LogAgent():
    log_files = [...]
    log_ingester = LogIngestor(log_files)
    logs = log_ingester.ingest_logs()

    log_cleaner = LogCleaner()
    cleaned_logs = [log_cleaner.clean_logs(log) for log in logs]

    log_parser = LogParser()
    parsed_logs = log_parser.batch_parse_and_score(cleaned_logs)
    print(f"{len(parsed_logs)} logs parsed and scored.")
    return parsed_logs
