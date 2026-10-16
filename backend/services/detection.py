"""Detection rules as code: log line in, Event (or None) out. Pure, no I/O.

Rules are derived from the real 2026-09/10 incident (PostgreSQL COPY ... FROM PROGRAM
attempts and password guessing against project databases). Each rule has tests that feed
it real log lines. Evidence samples are scrubbed: command payloads and secrets are never
copied into an alert.
"""
import re
from dataclasses import dataclass

SAMPLE_MAX = 200


@dataclass(frozen=True)
class Event:
    rule: str
    severity: str
    source: str
    key: str
    summary: str
    sample: str


_COPY = re.compile(r'COPY\s+.*PROGRAM|COPY\s+_prog_out|pg_execute_server_program|'
                   r'permission denied to COPY to or from an external program', re.I)
_AUTH = re.compile(r'(?:(?P<user>[^\s@]+)@(?P<db>\S+)\s+(?P<host>[0-9A-Fa-f.:]+)\s+)?'
                   r'FATAL:\s+password authentication failed for user "(?P<who>[^"]+)"')
_HBA = re.compile(r'FATAL:\s+no pg_hba\.conf entry for host "(?P<host>[^"]+)"')
_PAYLOAD = re.compile(r"(PROGRAM\s+')[^']*('?)", re.I)
_SECRET = re.compile(r'(password|passwd|pwd|token|secret)\s*[=:]\s*\S+', re.I)


def scrub(line):
    """Short evidence line without payloads or secrets."""
    line = _PAYLOAD.sub(r"\1<redacted>\2", line.strip())
    line = _SECRET.sub(lambda m: m.group(1) + '=<redacted>', line)
    return line[:SAMPLE_MAX]


def detect(source, line):
    if not line or not line.strip():
        return None
    if _COPY.search(line):
        return Event('pg_copy_program', 'critical', source, f'copy:{source}',
                     f'COPY … PROGRAM / external program attempt on {source}', scrub(line))
    m = _AUTH.search(line)
    if m:
        who, host = m.group('who'), m.group('host') or 'unknown'
        return Event('pg_auth_failure', 'warning', source, f'pg_auth_failure:{source}:{who}:{host}',
                     f'Password authentication failed on {source} for "{who}" from {host}', scrub(line))
    m = _HBA.search(line)
    if m:
        host = m.group('host')
        return Event('pg_no_hba_entry', 'high', source, f'pg_no_hba_entry:{source}:{host}',
                     f'Connection from {host} rejected by pg_hba on {source}', scrub(line))
    return None
