"""Sends email only if SMTP is set up. Otherwise it returns a mailto: link for the user to open."""
import smtplib
from email.message import EmailMessage
from urllib.parse import quote

from core.config import settings


def send_or_link(to: str, subject: str, body: str) -> dict:
    if settings.smtp_configured:
        msg = EmailMessage()
        msg["From"], msg["To"], msg["Subject"] = settings.smtp_from or settings.smtp_user, to, subject
        msg.set_content(body)
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
            server.starttls()
            server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)
        return {"message": f"Email sent to {to}"}
    return {"url": f"mailto:{quote(to)}?subject={quote(subject)}&body={quote(body)}", "message": "SMTP is not set up, so your email app opens with the draft."}
