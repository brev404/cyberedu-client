"""
CyberEdu Client - Official Python client for CyberEdu CTF platform

This is the official Python client library for the CyberEdu CTF platform API.
It provides a comprehensive, well-maintained interface for interacting with all
aspects of the platform, including:

- Educational archive challenges
- Contest/event challenges and leaderboards
- Flag submissions and management
- File downloads
- Service/deployment management
- User and tenant information

This client is designed to be:
- Stateless and thread-safe
- Well-typed for AI/LLM integration
- Compatible with MCP (Model Context Protocol) servers
- Easy to extend and maintain
"""

from .cyberedu_client import CyberEduClient
from .models import Challenge, ChallengeFile, Flag, ServiceInfo

__all__ = [
    'CyberEduClient',
    'Challenge',
    'ChallengeFile',
    'Flag',
    'ServiceInfo',
]
