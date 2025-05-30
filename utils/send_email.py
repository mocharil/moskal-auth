import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from dotenv import load_dotenv
from typing import Optional, List
load_dotenv()

def create_html_message(content: str) -> str:
    """Create a standard HTML email template with the given content"""
    return f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .button {{ 
                display: inline-block; 
                padding: 12px 24px; 
                background-color: #5d98f0; 
                color: #ffffff; 
                text-decoration: none; 
                border-radius: 6px; 
                margin: 20px 0;
                font-weight: 500;
                letter-spacing: 0.5px;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
                transition: all 0.3s ease;
            }}
            .button:hover {{
                background-color: #0052cc;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
            }}
            .footer {{ 
                margin-top: 30px; 
                padding-top: 20px; 
                border-top: 1px solid #eee; 
                font-size: 0.9em; 
                color: #666; 
            }}
        </style>
    </head>
    <body>
        <div class="container">
            {content}
            <div class="footer">
                <p>Best regards,<br>The Moskal Team<br>
                <i>Insight that matters.</i></p>
            </div>
        </div>
    </body>
    </html>
    """

def send_verification_email(to: str, verification_url: str, cc: Optional[str] = None) -> None:
    """Send an email verification link to the user"""
    sender_email = os.getenv('EMAIL_SENDER')
    sender_password = os.getenv("EMAIL_PASSWORD")
    
    # Validate required environment variables
    if not sender_email or not sender_password:
        raise ValueError("Missing required environment variables: EMAIL_SENDER or EMAIL_PASSWORD")

    subject = "Verify Your Email Address"
    
    content = f"""
        <h2>Welcome to Moskal!</h2>
        <p>Thank you for registering. Please verify your email address to complete your registration.</p>
        <p>
            <a href="{verification_url}" class="button">Verify Email Address</a>
        </p>
        <p>Or copy and paste this link in your browser:</p>
        <p style="word-break: break-all;">{verification_url}</p>
        <p>This verification link will expire in 24 hours.</p>
        <p>If you didn't create an account with us, please ignore this email.</p>
    """
    
    # Construct message
    message = MIMEMultipart()
    message['Subject'] = subject
    message['From'] = sender_email
    message['To'] = to
    if cc:
        message['Cc'] = cc
    
    html_content = create_html_message(content)
    html_part = MIMEText(html_content, "html")
    message.attach(html_part)
    
    # Send email using Zoho SMTP with TLS
    try:
        server = smtplib.SMTP('smtp.zoho.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, [to] + ([cc] if cc else []), message.as_string())
        server.quit()
    except Exception as e:
        raise Exception(f"Failed to send email: {str(e)}")

def send_reset_password_email(to: str, reset_url: str, cc: Optional[str] = None) -> None:
    """Send a password reset link to the user"""
    sender_email = os.getenv('EMAIL_SENDER')
    sender_password = os.getenv("EMAIL_PASSWORD")
    
    # Validate required environment variables
    if not sender_email or not sender_password:
        raise ValueError("Missing required environment variables: EMAIL_SENDER or EMAIL_PASSWORD")

    subject = "Reset Your Password"
    
    content = f"""
        <h2>Password Reset Request</h2>
        <p>We received a request to reset your password. Click the button below to create a new password:</p>
        <p>
            <a href="{reset_url}" class="button">Reset Password</a>
        </p>
        <p>Or copy and paste this link in your browser:</p>
        <p style="word-break: break-all;">{reset_url}</p>
        <p>This reset link will expire in 24 hours.</p>
        <p>If you didn't request a password reset, please ignore this email.</p>
    """
    
    # Construct message
    message = MIMEMultipart()
    message['Subject'] = subject
    message['From'] = sender_email
    message['To'] = to
    if cc:
        message['Cc'] = cc
    
    html_content = create_html_message(content)
    html_part = MIMEText(html_content, "html")
    message.attach(html_part)
    
    # Send email using Zoho SMTP with TLS
    try:
        server = smtplib.SMTP('smtp.zoho.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, [to] + ([cc] if cc else []), message.as_string())
        server.quit()
    except Exception as e:
        raise Exception(f"Failed to send email: {str(e)}")

def send_report_email(to: str, file_path: str, topic: str, date_range: str, cc: Optional[str] = None) -> None:
    """Send an email with a report attachment"""
    sender_email = os.getenv('EMAIL_SENDER')
    sender_password = os.getenv("EMAIL_PASSWORD")
    
    # Validate required environment variables
    if not sender_email or not sender_password:
        raise ValueError("Missing required environment variables: EMAIL_SENDER or EMAIL_PASSWORD")
    
    subject = f"Your {topic} Report from {date_range} is Ready!"
    
    content = f"""
        <h2>Your Report is Ready</h2>
        <p>We're happy to let you know that your report on <b>{topic}</b> for the period <b>{date_range}</b> is now ready!</p>
        <p>You'll find the file attached below.</p>
        <p>If you have any questions or need any adjustments, feel free to reach out — we're here to help.</p>
    """
    
    # Construct message
    message = MIMEMultipart()
    message['Subject'] = subject
    message['From'] = sender_email
    message['To'] = to
    if cc:
        message['Cc'] = cc
    
    html_content = create_html_message(content)
    html_part = MIMEText(html_content, "html")
    message.attach(html_part)
    
    # Attach file
    with open(file_path, "rb") as attachment:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f"attachment; filename= {os.path.basename(file_path)}"
        )
        message.attach(part)
    
    # Send email using Zoho SMTP with TLS
    try:
        server = smtplib.SMTP('smtp.zoho.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, [to] + ([cc] if cc else []), message.as_string())
        server.quit()
    except Exception as e:
        raise Exception(f"Failed to send email: {str(e)}")
