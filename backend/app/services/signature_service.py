import hmac
import hashlib
import logging

logger = logging.getLogger("signature_service")
logger.setLevel(logging.INFO)

class SignatureService:
    @staticmethod
    def verify_signature(payload: bytes, signature_header: str, app_secret: str) -> bool:
        """
        Verify the signature of incoming webhooks to ensure authenticity.
        Computes HMAC-SHA256 of payload with app_secret and compares it to X-Hub-Signature-256.
        """
        if not signature_header:
            logger.warning("Signature header (X-Hub-Signature-256) is missing.")
            return False
            
        if not signature_header.startswith("sha256="):
            logger.warning("Signature header does not start with 'sha256='.")
            return False
            
        # Extract the signature from the header
        expected_sig = signature_header.split("sha256=")[1].strip()
        
        # Calculate signature
        calculated_sig = hmac.new(
            app_secret.encode("utf-8"),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        # Safe comparison to avoid timing attacks
        is_valid = hmac.compare_digest(calculated_sig, expected_sig)
        
        if not is_valid:
            logger.warning(f"Signature mismatch. Calculated: {calculated_sig}, Expected: {expected_sig}")
        else:
            logger.info("Signature verified successfully.")
            
        return is_valid
