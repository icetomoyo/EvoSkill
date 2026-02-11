"""
PKCE (Proof Key for Code Exchange) Support
Equivalent to Pi Mono's packages/ai/src/utils/oauth/pkce.ts

PKCE is an extension to the OAuth 2.0 protocol that prevents authorization code interception attacks.
Used by Google, Anthropic, and other OAuth providers for secure authentication.
"""
import base64
import hashlib
import secrets
from dataclasses import dataclass
from typing import Optional


@dataclass
class PKCEChallenge:
    """
    PKCE Challenge parameters.
    
    Contains the code_challenge and code_verifier pair used in PKCE flow.
    """
    code_challenge: str
    code_verifier: str
    method: str = "S256"  # Only S256 is recommended


def generate_code_verifier(length: int = 128) -> str:
    """
    Generate a cryptographically random code verifier.
    
    The code verifier is a high-entropy cryptographically random string.
    Per RFC 7636, it must be 43-128 characters.
    
    Args:
        length: Length of the verifier (default: 128, max: 128)
        
    Returns:
        URL-safe base64-encoded random string
        
    Example:
        >>> verifier = generate_code_verifier()
        >>> len(verifier) <= 128
        True
    """
    # Ensure length is within valid range (43-128)
    length = max(43, min(length, 128))
    
    # Generate random bytes (need enough for base64 to produce desired length)
    # Each byte becomes ~1.33 base64 characters
    num_bytes = int(length * 3 / 4) + 1
    random_bytes = secrets.token_bytes(num_bytes)
    
    # Encode to URL-safe base64 and strip padding
    verifier = base64.urlsafe_b64encode(random_bytes).decode("ascii")
    verifier = verifier.rstrip("=")[:length]  # Remove padding and truncate
    
    return verifier


def generate_code_challenge(verifier: str) -> str:
    """
    Generate the code challenge from a code verifier using S256 method.
    
    Args:
        verifier: The code verifier string
        
    Returns:
        Base64URL-encoded SHA256 hash of the verifier
        
    Example:
        >>> verifier = generate_code_verifier()
        >>> challenge = generate_code_challenge(verifier)
        >>> len(challenge) > 0
        True
    """
    # SHA256 hash of the verifier
    sha256_hash = hashlib.sha256(verifier.encode("ascii")).digest()
    
    # Base64URL encode and strip padding
    challenge = base64.urlsafe_b64encode(sha256_hash).decode("ascii")
    challenge = challenge.rstrip("=")
    
    return challenge


def generate_pkce_challenge(length: int = 128) -> PKCEChallenge:
    """
    Generate a complete PKCE challenge pair.
    
    This is the main entry point for generating PKCE parameters.
    
    Args:
        length: Length of the code verifier (default: 128)
        
    Returns:
        PKCEChallenge containing code_verifier and code_challenge
        
    Example:
        >>> challenge = generate_pkce_challenge()
        >>> len(challenge.code_verifier) >= 43
        True
        >>> len(challenge.code_challenge) > 0
        True
        >>> challenge.method == "S256"
        True
    """
    verifier = generate_code_verifier(length)
    code_challenge = generate_code_challenge(verifier)
    
    return PKCEChallenge(
        code_challenge=code_challenge,
        code_verifier=verifier,
        method="S256",
    )


def verify_code_challenge(verifier: str, challenge: str) -> bool:
    """
    Verify that a code verifier matches a code challenge.
    
    This is used by the OAuth server to validate the PKCE flow.
    
    Args:
        verifier: The code verifier from the client
        challenge: The code_challenge that was sent to the server
        
    Returns:
        True if verifier matches the challenge
        
    Example:
        >>> pkce = generate_pkce_challenge()
        >>> verify_code_challenge(pkce.code_verifier, pkce.code_challenge)
        True
        >>> verify_code_challenge("invalid", pkce.code_challenge)
        False
    """
    computed_challenge = generate_code_challenge(verifier)
    return secrets.compare_digest(computed_challenge, challenge)


# Convenience functions for OAuth integration
def get_pkce_authorization_url_params(challenge: PKCEChallenge) -> dict:
    """
    Get URL parameters to add to authorization URL.
    
    Args:
        challenge: The PKCE challenge
        
    Returns:
        Dictionary of URL parameters
        
    Example:
        >>> challenge = generate_pkce_challenge()
        >>> params = get_pkce_authorization_url_params(challenge)
        >>> "code_challenge" in params
        True
        >>> "code_challenge_method" in params
        True
    """
    return {
        "code_challenge": challenge.code_challenge,
        "code_challenge_method": challenge.method,
    }


def get_pkce_token_request_params(verifier: str) -> dict:
    """
    Get parameters to add to token request.
    
    Args:
        verifier: The code verifier
        
    Returns:
        Dictionary of request parameters
        
    Example:
        >>> challenge = generate_pkce_challenge()
        >>> params = get_pkce_token_request_params(challenge.code_verifier)
        >>> "code_verifier" in params
        True
    """
    return {
        "code_verifier": verifier,
    }


__all__ = [
    "PKCEChallenge",
    "generate_code_verifier",
    "generate_code_challenge",
    "generate_pkce_challenge",
    "verify_code_challenge",
    "get_pkce_authorization_url_params",
    "get_pkce_token_request_params",
]
