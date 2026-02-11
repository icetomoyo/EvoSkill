"""
PKCE (Proof Key for Code Exchange)
Equivalent to Pi Mono's packages/ai/src/pkce.ts

OAuth PKCE challenge generation per RFC 7636.
"""
import base64
import hashlib
import secrets
from typing import Dict


def generate_code_verifier(length: int = 128) -> str:
    """
    Generate a code verifier for PKCE.
    
    Per RFC 7636, the code verifier must be 43-128 characters
    and use [A-Z] / [a-z] / [0-9] / "-" / "." / "_" / "~".
    
    Args:
        length: Length of verifier (43-128, default: 128)
        
    Returns:
        Code verifier string
        
    Raises:
        ValueError: If length is outside 43-128 range
    """
    if length < 43 or length > 128:
        raise ValueError("Code verifier must be 43-128 characters")
    
    # Generate URL-safe random string
    token = secrets.token_urlsafe(length)
    return token[:length]


def generate_code_challenge(verifier: str) -> str:
    """
    Generate a code challenge from a verifier.
    
    Uses S256 method: BASE64URL(SHA256(verifier))
    
    Args:
        verifier: Code verifier
        
    Returns:
        Code challenge string
    """
    # SHA256 hash
    digest = hashlib.sha256(verifier.encode()).digest()
    # Base64URL encoding without padding
    return base64.urlsafe_b64encode(digest).rstrip(b'=').decode()


def generate_pkce_challenge() -> Dict[str, str]:
    """
    Generate a complete PKCE challenge.
    
    Returns both the code_challenge to send in the authorization request
    and the code_verifier to send in the token request.
    
    Returns:
        Dict with "code_verifier" and "code_challenge" keys
        
    Example:
        >>> challenge = generate_pkce_challenge()
        >>> print(challenge["code_challenge"])
        'E9...'
        >>> print(challenge["code_verifier"])
        'xG...'
    """
    verifier = generate_code_verifier()
    challenge = generate_code_challenge(verifier)
    return {
        "code_verifier": verifier,
        "code_challenge": challenge
    }


__all__ = [
    "generate_code_verifier",
    "generate_code_challenge",
    "generate_pkce_challenge",
]
