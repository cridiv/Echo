import os
import re
import json
import uuid
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
        print(f"Ingested logs from {len(all_logs)} files.")
        return all_logs

    def _parse_json_logs(self, file_path: str) -> List[Dict]:
        logs = []
        with open(file_path, "r") as f:
            for line in f:
                try:
                    log_entry = json.loads(line.strip())
                    # Add unique ID if not present
                    if "id" not in log_entry:
                        log_entry["id"] = str(uuid.uuid4())
                    # Add source file info
                    log_entry["source_file"] = os.path.basename(file_path)
                    logs.append(log_entry)
                except json.JSONDecodeError:
                    print(f"Invalid JSON in {file_path}: {line}")
        print(f"Parsed {len(logs)} JSON logs from {file_path}")
        return logs

    def _parse_plain_logs(self, file_path: str) -> List[Dict]:
        logs = []
        with open(file_path, "r") as f:
            for line in f:
                logs.append(
                    {
                        "id": str(uuid.uuid4()),  # Add unique ID
                        "raw": line.strip(),
                        "source_file": os.path.basename(file_path),
                    }
                )
        print(f"Parsed {len(logs)} plain logs from {file_path}")
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

        print(f"Cleaned line: {line}")
        return line

    def clean_logs(self, log_entry: Dict) -> Dict:
        """Takes a log entry dict and cleans the raw content."""
        cleaned_entry = log_entry.copy()

        if "raw" in cleaned_entry:
            cleaned_entry["raw"] = self.clean_line(cleaned_entry["raw"])

        return cleaned_entry


class LogParser:
    def __init__(self):
        pass

    def parse_logs(self, log_entry: Dict) -> Dict:
        """Parse a log entry and extract structured data."""
        if "raw" not in log_entry:
            return log_entry

        line = log_entry["raw"]
        pattern = r"^(?P<timestamp>\S+ \S+)\s+(?P<level>[A-Z]+)\s+(?P<message>.+)$"
        match = re.match(pattern, line)

        # Start with the original log entry
        parsed_entry = log_entry.copy()

        if match:
            try:
                parsed_entry["timestamp"] = datetime.strptime(
                    match.group("timestamp"), "%Y-%m-%d %H:%M:%S"
                )
                parsed_entry["level"] = match.group("level")
                parsed_entry["message"] = match.group("message")
                parsed_entry["parsed"] = True
            except ValueError:
                # If timestamp parsing fails, mark as unparsed
                parsed_entry["parsed"] = False
                parsed_entry["timestamp"] = datetime.now()  # Default timestamp
                parsed_entry["level"] = "UNKNOWN"
                parsed_entry["message"] = line
        else:
            # If pattern doesn't match, mark as unparsed
            parsed_entry["parsed"] = False
            parsed_entry["timestamp"] = datetime.now()  # Default timestamp
            parsed_entry["level"] = "UNKNOWN"
            parsed_entry["message"] = line
        print(f"Parsed log entry: {parsed_entry}")
        return parsed_entry

    def score_log(self, parsed_log: Dict) -> Dict:
        """Add scoring based on log level."""
        level = parsed_log.get("level", "UNKNOWN")

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

    def batch_parse_and_score(self, log_entries: List[Dict]) -> List[Dict]:
        """Process multiple log entries."""
        results = []
        for log_entry in log_entries:
            parsed = self.parse_logs(log_entry)
            scored = self.score_log(parsed)
            results.append(scored)
        print(f"Processed {len(results)} log entries.")
        return results


def LogAgent():
    log_files = [...]

    # Step 1: Ingest logs (now with IDs)
    log_ingester = LogIngestor(log_files)
    logs = log_ingester.ingest_logs()

    # Step 2: Clean logs
    log_cleaner = LogCleaner()
    cleaned_logs = [log_cleaner.clean_logs(log) for log in logs]

    # Step 3: Parse and score logs
    log_parser = LogParser()
    parsed_logs = log_parser.batch_parse_and_score(cleaned_logs)

    print(f"{len(parsed_logs)} logs parsed and scored.")
    return parsed_logs
