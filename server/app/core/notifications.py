import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import datetime
import httpx
from app.core.config import settings

def send_email_alert(recipient_email: str, subject: str, body: str):
    """
    Sends an email alert.
    If SMTP_HOST is not configured, logs/prints the email to stdout (Mock Mode).
    If SMTP_HOST is configured, uses smtplib to send the email.
    """
    if not settings.SMTP_HOST:
        # Mock mode: print to console for local development
        print("\n" + "="*50)
        print(" 📧 MOCK EMAIL ALERT SENT")
        print(f"To:      {recipient_email}")
        print(f"Subject: {subject}")
        print(f"Body:\n{body}")
        print("="*50 + "\n")
        return

    # Real SMTP email sending
    try:
        msg = MIMEMultipart()
        msg['From'] = settings.SMTP_FROM_EMAIL
        msg['To'] = recipient_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Connect to SMTP server
        server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
        server.starttls() # Secure connection
        
        if settings.SMTP_USER and settings.SMTP_PASSWORD:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            
        server.sendmail(settings.SMTP_FROM_EMAIL, recipient_email, msg.as_string())
        server.quit()
        print(f"Successfully sent live email alert to {recipient_email}")
    except Exception as e:
        print(f"Failed to send SMTP email: {str(e)}")

def send_webhook_alert(webhook_url: str, payload: dict):
    """
    Sends a POST request to the project's webhook_url using HTTPX.
    """
    try:
        response = httpx.post(webhook_url, json=payload, timeout=5.0)
        if 200 <= response.status_code < 300:
            print(f"Successfully triggered webhook: {webhook_url}")
        else:
            print(f"Webhook alert failed with status code {response.status_code}: {response.text}")
    except Exception as e:
        print(f"Failed to trigger webhook alert: {str(e)}")

def dispatch_alert(endpoint, project, owner, is_recovery: bool, error_message: str | None = None, ai_analysis: dict | None = None):
    """
    Coordinates and dispatches alerts (emails & webhooks) to the user.
    """
    status_label = "RECOVERED" if is_recovery else "CRITICAL FAILURE"
    subject = f"[{status_label}] PulseGuard Alert: {endpoint.name}"
    
    # 1. Build the email body
    if is_recovery:
        body = (
            f"Hello,\n\n"
            f"Good news! Your endpoint '{endpoint.name}' in project '{project.name}' has recovered.\n\n"
            f"Details:\n"
            f"- Endpoint Name: {endpoint.name}\n"
            f"- URL: {endpoint.url} ({endpoint.method})\n"
            f"- Status: Healthy\n\n"
            f"PulseGuard Platform"
        )
    else:
        # Build AI Analysis section if present
        ai_section = ""
        if ai_analysis:
            ai_section = (
                f"\n🤖 AI INCIDENT ANALYSIS:\n"
                f"Summary:\n{ai_analysis.get('summary', 'N/A')}\n\n"
                f"Troubleshooting Suggestions:\n{ai_analysis.get('suggestions', 'N/A')}\n"
                f"==================================================\n"
            )
            
        body = (
            f"Hello,\n\n"
            f"Alert! Your endpoint '{endpoint.name}' in project '{project.name}' is failing repeatedly.\n\n"
            f"Details:\n"
            f"- Endpoint Name: {endpoint.name}\n"
            f"- URL: {endpoint.url} ({endpoint.method})\n"
            f"- Status: Failing (Offline)\n"
            f"- Error Message: {error_message or 'Unknown connection issue'}\n\n"
            f"{ai_section}"
            f"Please check your server logs immediately.\n\n"
            f"PulseGuard Platform"
        )
        
    # 2. Dispatch Email
    send_email_alert(
        recipient_email=owner.email,
        subject=subject,
        body=body
    )
    
    # 3. Dispatch Webhook (if configured)
    if project.webhook_url:
        webhook_payload = {
            "event": "alert.recovery" if is_recovery else "alert.failure",
            "endpoint": {
                "id": endpoint.id,
                "name": endpoint.name,
                "url": endpoint.url,
                "method": endpoint.method,
                "status": endpoint.status
            },
            "project": {
                "id": project.id,
                "name": project.name
            },
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "error_message": error_message,
            "ai_analysis": ai_analysis
        }
        send_webhook_alert(project.webhook_url, webhook_payload)
