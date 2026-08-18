from __future__ import annotations

import os
import smtplib
import random
import string
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv


def generate_otp(length: int = 6) -> str:
    """Generate a numeric OTP of given length."""
    return "".join(random.choices(string.digits, k=length))


def send_otp_email(to_email: str, full_name: str, otp: str) -> bool:
    """
    Send an OTP verification email via Gmail SMTP.
    Returns True on success, False on failure.
    """
    load_dotenv()

    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com").strip()
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "").strip()
    smtp_password = os.getenv("SMTP_PASSWORD", "").strip()
    from_name = os.getenv("FROM_NAME", "BDNS Security Platform").strip()

    # Check if credentials are placeholders or empty
    if (
        not smtp_user
        or not smtp_password
        or smtp_user == "your-gmail@gmail.com"
        or smtp_password == "your-gmail-app-password"
    ):
        print(f"\n=======================================================")
        print(f"[EmailService Warning] Real Gmail credentials not configured in backend/.env")
        print(f"[DEV OTP VERIFICATION CODE FOR {to_email}]: {otp}")
        print(f"=======================================================\n")
        return False

    subject = "Your BDNS Account Verification Code"

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="UTF-8"/>
      <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #0a0f1e; color: #ccd6f6; margin: 0; padding: 0; }}
        .container {{ max-width: 520px; margin: 40px auto; background: #0d1b3e; border-radius: 16px; overflow: hidden; border: 1px solid rgba(108,99,255,0.25); }}
        .header {{ background: linear-gradient(135deg, #1a0a3e, #0d2060); padding: 32px 36px 24px; text-align: center; }}
        .header h1 {{ color: #ffffff; font-size: 1.5rem; margin: 0; letter-spacing: 0.05em; }}
        .header .badge {{ display: inline-block; background: rgba(108,99,255,0.2); border: 1px solid #6c63ff; color: #a78bfa; padding: 4px 12px; border-radius: 20px; font-size: 0.75rem; margin-top: 8px; letter-spacing: 0.1em; text-transform: uppercase; }}
        .body {{ padding: 32px 36px; }}
        .greeting {{ font-size: 1rem; color: #8892b0; margin-bottom: 20px; }}
        .otp-box {{ background: linear-gradient(135deg, rgba(108,99,255,0.15), rgba(0,212,170,0.08)); border: 2px solid rgba(108,99,255,0.4); border-radius: 12px; padding: 24px; text-align: center; margin: 24px 0; }}
        .otp-label {{ font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.1em; color: #8892b0; margin-bottom: 12px; }}
        .otp-code {{ font-size: 2.8rem; font-weight: 900; font-family: monospace; letter-spacing: 0.4em; color: #00d4aa; }}
        .expiry {{ font-size: 0.82rem; color: #6c63ff; margin-top: 12px; }}
        .note {{ font-size: 0.85rem; color: #64748b; margin-top: 24px; line-height: 1.6; }}
        .footer {{ background: rgba(0,0,0,0.3); padding: 18px 36px; text-align: center; font-size: 0.75rem; color: #4a5568; border-top: 1px solid rgba(255,255,255,0.05); }}
      </style>
    </head>
    <body>
      <div class="container">
        <div class="header">
          <h1>BDNS Security Platform</h1>
          <span class="badge">Email Verification</span>
        </div>
        <div class="body">
          <p class="greeting">Hello, <strong style="color:#ccd6f6">{full_name}</strong></p>
          <p style="color:#8892b0; font-size:0.92rem;">Thank you for registering on the <strong style="color:#a78bfa">BDNS Blockchain DNS Security Platform</strong>. To complete your account setup, please verify your email address using the code below.</p>
          <div class="otp-box">
            <div class="otp-label">Your Verification Code</div>
            <div class="otp-code">{otp}</div>
            <div class="expiry">Valid for <strong>10 minutes</strong></div>
          </div>
          <p class="note">Enter this code on the verification page to activate your account. If you did not create a BDNS account, please ignore this email.</p>
          <p class="note" style="color:#ef4444;">Never share this code with anyone. BDNS staff will never ask for your OTP.</p>
        </div>
        <div class="footer">
          (C) 2026 BDNS Enterprise Security Platform - Blockchain DNS Security
        </div>
      </div>
    </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{from_name} <{smtp_user}>"
    msg["To"] = to_email
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, to_email, msg.as_string())
        print(f"[EmailService] Successfully sent OTP email to {to_email}")
        return True
    except smtplib.SMTPAuthenticationError as exc:
        print(f"[EmailService] Gmail Authentication failed for {smtp_user}: {exc}")
        print(f"[HELP] Please make sure you are using a 16-character Gmail App Password (myaccount.google.com -> Security -> App Passwords).")
        print(f"[DEV OTP VERIFICATION CODE FOR {to_email}]: {otp}")
        return False
    except Exception as exc:
        print(f"[EmailService] Failed to send OTP to {to_email}: {exc}")
        print(f"[DEV OTP VERIFICATION CODE FOR {to_email}]: {otp}")
        return False


