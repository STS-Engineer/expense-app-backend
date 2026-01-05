# app/services/email_service.py

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings


def send_responsible_email(
    to_email: str,
    concerned_person: str,
    total_eur: float,
    approval_token: str,
):
    approval_link = (
        f"{settings.FRONTEND_BASE_URL}"
        f"/responsible/reports/{approval_token}"
    )

    subject = "Expense report pending approval"

    html_body = f"""
    <html>
      <body style="font-family: Arial, sans-serif;">
        <p>Hello,</p>
        <p>
          An expense report for <strong>{concerned_person}</strong>
          with a total of <strong>{total_eur:.2f} EUR</strong>
          is pending your approval.
        </p>
        <p>
          <a href="{approval_link}"
             style="
               display:inline-block;
               padding:10px 16px;
               background:#2563eb;
               color:#ffffff;
               text-decoration:none;
               border-radius:4px;
             ">
            Review expense report
          </a>
        </p>
        <p style="font-size:12px;color:#666;">
          This link is single-use.
        </p>
      </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(html_body, "html"))

    # ✅ RELAY MODE — NO AUTH, NO TLS (MATCHES NODEJS)
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
        server.sendmail(
            settings.SMTP_FROM,
            [to_email],
            msg.as_string(),
        )
