import json
import logging
from typing import Dict, Any, Optional
from app.core.config import settings

logger = logging.getLogger("session_service")
logger.setLevel(logging.INFO)

# Global in-memory fallback cache
_memory_sessions: Dict[str, Dict[str, Any]] = {}
_redis_available: Optional[bool] = None
_redis_client: Optional[Any] = None

class SessionService:
    @classmethod
    def _get_redis(cls) -> Optional[Any]:
        global _redis_available, _redis_client
        if _redis_available is False:
            return None
            
        if _redis_client is not None:
            return _redis_client
            
        try:
            import redis
            logger.info(f"Connecting to Redis at {settings.REDIS_URL}...")
            client = redis.from_url(settings.REDIS_URL, decode_responses=True)
            # Ping to verify active connection
            client.ping()
            _redis_client = client
            _redis_available = True
            logger.info("Successfully connected to Redis. Sessions will be persisted in Redis.")
            return _redis_client
        except Exception as e:
            logger.warning(f"Redis not available ({e}). Falling back to thread-safe in-memory session store.")
            _redis_available = False
            _redis_client = None
            return None

    @classmethod
    async def get_session(cls, phone_number: str, clinic_id: int) -> Dict[str, Any]:
        """
        Retrieves the user's active session, scoped by clinic_id.
        Returns a default empty session if none exists.
        """
        # Normalize phone number by removing any plus sign
        phone = phone_number.replace("+", "")
        
        redis_client = cls._get_redis()
        if redis_client:
            try:
                data = redis_client.get(f"session:{clinic_id}:{phone}")
                if data:
                    return json.loads(data)
            except Exception as e:
                logger.error(f"Failed to load session from Redis for {clinic_id}:{phone}: {e}")
                
        # In-memory fallback
        return _memory_sessions.get(f"{clinic_id}:{phone}", {"step": "idle", "data": {}})

    @classmethod
    async def save_session(cls, phone_number: str, session: Dict[str, Any], clinic_id: int, expiry: int = 3600) -> None:
        """
        Saves the user session, scoped by clinic_id. Expires after 1 hour by default.
        """
        phone = phone_number.replace("+", "")
        redis_client = cls._get_redis()
        if redis_client:
            try:
                redis_client.setex(f"session:{clinic_id}:{phone}", expiry, json.dumps(session))
                return
            except Exception as e:
                logger.error(f"Failed to save session to Redis for {clinic_id}:{phone}: {e}")
                
        # In-memory fallback
        _memory_sessions[f"{clinic_id}:{phone}"] = session

    @classmethod
    async def clear_session(cls, phone_number: str, clinic_id: int) -> None:
        """
        Clears/deletes the session state for the given clinic.
        """
        phone = phone_number.replace("+", "")
        redis_client = cls._get_redis()
        if redis_client:
            try:
                redis_client.delete(f"session:{clinic_id}:{phone}")
                return
            except Exception as e:
                logger.error(f"Failed to clear session in Redis for {clinic_id}:{phone}: {e}")
                
        # In-memory fallback
        _memory_sessions.pop(f"{clinic_id}:{phone}", None)
