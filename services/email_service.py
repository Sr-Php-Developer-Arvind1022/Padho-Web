import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

SMTP_HOST = "mail.sahilmoney.in"
SMTP_PORT = 465
SMTP_USER = "boloapp@sahilmoney.in"
SMTP_PASS = "BoloApp@321"

def send_email(to_email: str, subject: str, html_content: str):
    try:
        # 👇 IMPORTANT: use 'alternative'
        msg = MIMEMultipart("alternative")
        msg["From"] = SMTP_USER
        msg["To"] = to_email
        msg["Subject"] = subject

        # 👇 Plain text fallback (important for delivery)
        text_part = MIMEText("Welcome to BoloApp", "plain", "utf-8")

        # 👇 HTML with UTF-8 (FIX)
        html_part = MIMEText(html_content, "html", "utf-8")

        msg.attach(text_part)
        msg.attach(html_part)

        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)

        return True

    except Exception as e:
        print("Email Error:", str(e))
        return False