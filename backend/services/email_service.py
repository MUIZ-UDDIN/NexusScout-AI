import os
import resend
from dotenv import load_dotenv

load_dotenv()

resend.api_key = os.getenv("RESEND_API_KEY")

FROM_ADDR = os.getenv("RESEND_FROM", "onboarding@resend.dev")

EMAIL_TEMPLATE = """<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
  <p>{opening}</p>
  <p>I noticed your work at <strong>{business}</strong> and would love to discuss how we can help you grow further.</p>
  <p>Would you be open to a quick call this week?</p>
  <p>Best regards,<br/>NexusScout Team</p>
</body>
</html>"""

def send_lead_email(to_email: str, business_name: str, opening: str) -> dict:
    if not os.getenv("RESEND_API_KEY"):
        print(f"[email] No RESEND_API_KEY set. Skipping send to {to_email}")
        return {"status": "skipped", "reason": "no_api_key"}

    html = EMAIL_TEMPLATE.format(business=business_name, opening=opening)

    params = {
        "from": FROM_ADDR,
        "to": [to_email],
        "subject": f"Question about {business_name}",
        "html": html,
    }

    r = resend.Emails.send(params)
    print(f"[email] Sent to {to_email} — id={r.get('id')}")
    return r
