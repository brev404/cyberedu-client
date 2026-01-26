"""
Data models for CyberEdu API responses.

These are type hints and data structures to help work with API responses.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ChallengeFile:
    """Represents a challenge file."""
    id: str
    name: str
    url: Optional[str] = None
    size: Optional[int] = None
    hash: Optional[str] = None


@dataclass
class Flag:
    """Represents a flag/question in a challenge."""
    id: str
    text: str
    type: str  # 'flag' or 'answer'
    solved: bool = False


@dataclass
class ServiceInfo:
    """Represents service/deployment information."""
    host: Optional[str] = None
    port: Optional[int] = None
    status: Optional[str] = None  # 'running', 'stopped', 'starting', 'error'
    expires_at: Optional[datetime] = None
    connection_string: Optional[str] = None


@dataclass
class Challenge:
    """Represents a challenge."""
    id: str
    title: str
    category: str  # web, pwn, crypto, forensics, misc, reverse
    difficulty: str  # easy, medium, hard, insane
    description: str
    points: int
    files: List[ChallengeFile]
    flags: List[Flag]
    service: Optional[ServiceInfo] = None
    solved: bool = False
    solve_count: int = 0
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Challenge':
        """Create Challenge from API response dictionary."""
        files = [
            ChallengeFile(**f) if isinstance(f, dict) else f
            for f in data.get('files', [])
        ]
        
        flags = [
            Flag(**f) if isinstance(f, dict) else f
            for f in data.get('flags', []) or data.get('questions', [])
        ]
        
        service_data = data.get('service') or data.get('deployment')
        service = None
        if service_data:
            service = ServiceInfo(**service_data)
        
        return cls(
            id=data['id'],
            title=data.get('title', ''),
            category=data.get('category', ''),
            difficulty=data.get('difficulty', ''),
            description=data.get('description', ''),
            points=data.get('points', 0),
            files=files,
            flags=flags,
            service=service,
            solved=data.get('solved', False),
            solve_count=data.get('solve_count', 0),
        )
