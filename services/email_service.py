"""Email service for sending account verification and password reset emails.

This service encapsulates SMTP email delivery logic using configuration from config.py / .env.
"""
import traceback
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import Config
from logging_config.logger import logger


class EmailService:
    """Service dedicated to preparing and dispatching email notifications."""

    def __init__(self, config=None):
        self.config = config or Config

    def send_email(self, to_email, subject, body_text, body_html=None):
        """Send an email using SMTP settings configured in environment."""
        mail_server = getattr(self.config, "MAIL_SERVER", "localhost")
        mail_port = getattr(self.config, "MAIL_PORT", 587)
        mail_username = getattr(self.config, "MAIL_USERNAME", "")
        mail_password = getattr(self.config, "MAIL_PASSWORD", "")
        use_tls = getattr(self.config, "MAIL_USE_TLS", True)
        sender = getattr(self.config, "MAIL_DEFAULT_SENDER", "noreply@smartsubscriptionadvisor.com")

        # If SMTP is not configured (e.g. testing or local dev without credentials), log and return gracefully
        if not mail_username or not mail_password or mail_server in ("localhost", "127.0.0.1", ""):
            logger.info("Email delivery simulated (SMTP credentials not provided)")
            return True

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = to_email

        msg.attach(MIMEText(body_text, "plain"))
        if body_html:
            msg.attach(MIMEText(body_html, "html"))

        try:
            if use_tls:
                server = smtplib.SMTP(mail_server, mail_port, timeout=10)
                server.starttls()
            else:
                server = smtplib.SMTP(mail_server, mail_port, timeout=10)

            if mail_username and mail_password:
                server.login(mail_username, mail_password)

            server.sendmail(sender, [to_email], msg.as_string())
            server.quit()
            logger.info("Email dispatched successfully via SMTP")
            return True
        

        except Exception as exc:
            logger.exception("SMTP email dispatch failed")
            traceback.print_exc()
            return False

    def send_verification_email(self, to_email, verification_url):
        """Send an account verification email containing the verification link."""
        subject = "Welcome to Smart Subscription Advisor - Verify your email address"
        body_text = (
            f"Welcome to Smart Subscription Advisor!\n\n"
            f"Please verify your email address by clicking the link below:\n"
            f"{verification_url}\n\n"
            f"This link expires in 24 hours.\n"
        )
        body_html = f"""
        <html>
          <body style="font-family: Arial, sans-serif; background-color: #0f172a; color: #f8fafc; padding: 30px;">
            <div style="max-width: 500px; margin: 0 auto; background-color: #1e293b; border-radius: 12px; padding: 24px; border: 1px solid #334155;">
              <h2 style="color: #6366f1; margin-top: 0;">Welcome to Smart Subscription Advisor</h2>
              <p style="color: #cbd5e1; font-size: 15px;">Please verify your email address to activate your account and start managing your subscriptions.</p>
              <div style="margin: 30px 0; text-align: center;">
                <a href="{verification_url}" style="background: linear-gradient(135deg, #6366f1, #4f46e5); color: #ffffff; padding: 12px 28px; text-decoration: none; border-radius: 8px; font-weight: bold; display: inline-block;">Verify Email</a>
              </div>
              <p style="color: #94a3b8; font-size: 13px; margin-bottom: 0;">This link expires in 24 hours.</p>
            </div>
          </body>
        </html>
        """
        return self.send_email(to_email, subject, body_text, body_html)

    def send_password_reset_email(self, to_email, reset_url):
        """Send a password reset email containing the reset link."""
        subject = "Smart Subscription Advisor - Password Reset Request"
        body_text = (
            f"Password Reset Request\n\n"
            f"You requested to reset your password. Click the link below to set a new password:\n"
            f"{reset_url}\n\n"
            f"This link expires in 30 minutes.\n"
            f"If you did not request a password reset, please ignore this email.\n"
        )
        body_html = f"""
        <html>
          <body style="font-family: Arial, sans-serif; background-color: #0f172a; color: #f8fafc; padding: 30px;">
            <div style="max-width: 500px; margin: 0 auto; background-color: #1e293b; border-radius: 12px; padding: 24px; border: 1px solid #334155;">
              <h2 style="color: #6366f1; margin-top: 0;">Password Reset Request</h2>
              <p style="color: #cbd5e1; font-size: 15px;">Click the button below to reset your Smart Subscription Advisor password.</p>
              <div style="margin: 30px 0; text-align: center;">
                <a href="{reset_url}" style="background: linear-gradient(135deg, #6366f1, #4f46e5); color: #ffffff; padding: 12px 28px; text-decoration: none; border-radius: 8px; font-weight: bold; display: inline-block;">Reset Password</a>
              </div>
              <p style="color: #94a3b8; font-size: 13px; margin-bottom: 0;">This link expires in 30 minutes. If you did not request a password reset, please ignore this email.</p>
            </div>
          </body>
        </html>
        """
        return self.send_email(to_email, subject, body_text, body_html)


email_service = EmailService()
