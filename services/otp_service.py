"""OTP Service interface shell for future mobile phone verification.

This service is designed as an extension point so mobile OTP verification (e.g. via Twilio or AWS SNS)
can be attached in future releases without altering authentication architecture or database models.
"""

from logging_config.logger import logger


class OTPService:
    """Service handler for mobile phone OTP dispatch and verification."""

    def send_otp(self, mobile_number: str) -> bool:
        """Send a 6-digit OTP code to the given mobile number (Future feature)."""
        logger.info("OTP service invoked (stubbed for future integration)")
        return True

    def verify_otp(self, mobile_number: str, otp_code: str) -> bool:
        """Verify an OTP code against stored/cached code (Future feature)."""
        logger.info("OTP verification invoked (stubbed for future integration)")
        return True


otp_service = OTPService()
