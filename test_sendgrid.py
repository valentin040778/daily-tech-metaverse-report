import os
import sendgrid
from sendgrid.helpers.mail import Mail

sg = sendgrid.SendGridAPIClient(api_key="SG.твой_ключ_целиком")
message = Mail(
    from_email="твой_email@домен.com",
    to_emails="тот_же_email@домен.com",
    subject="Test SendGrid",
    html_content="<strong>It works!</strong>"
)
response = sg.send(message)
print(response.status_code)
