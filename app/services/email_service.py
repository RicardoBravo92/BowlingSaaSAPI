from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from pydantic import EmailStr
from app.core.config import get_settings
from app.core.logging_config import get_logger
from pathlib import Path
from typing import Dict, Any

settings = get_settings()
logger = get_logger(__name__)

conf = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_STARTTLS=settings.MAIL_STARTTLS,
    MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
    USE_CREDENTIALS=settings.USE_CREDENTIALS,
    TEMPLATE_FOLDER=Path(__file__).parent.parent / 'templates' / 'email',
)

class EmailService:
    def __init__(self):
        self.fastmail = FastMail(conf)

    async def send_email(
        self, 
        email_to: EmailStr, 
        subject: str, 
        template_name: str, 
        template_body: Dict[str, Any]
    ):
        message = MessageSchema(
            subject=subject,
            recipients=[email_to],
            template_body=template_body,
            subtype=MessageType.html
        )
        try:
            await self.fastmail.send_message(message, template_name=template_name)
            logger.info(f"Email sent to {email_to} with subject: {subject}")
        except Exception as e:
            logger.error(f"Failed to send email to {email_to}: {str(e)}")

    async def send_booking_confirmation(self, email_to: EmailStr, booking_data: Dict[str, Any]):
        await self.send_email(
            email_to=email_to,
            subject="Booking Confirmation - Bowling SaaS",
            template_name="booking_confirmation.html",
            template_body=booking_data
        )

    async def send_password_reset(self, email_to: EmailStr, reset_data: Dict[str, Any]):
        await self.send_email(
            email_to=email_to,
            subject="Password Reset Request - Bowling SaaS",
            template_name="password_reset.html",
            template_body=reset_data
        )

email_service = EmailService()
