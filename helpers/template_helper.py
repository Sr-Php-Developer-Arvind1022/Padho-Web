# helpers/template_helper.py

from pathlib import Path

def render_template(name: str, email: str, password: str):
    file_path = Path("templates/welcome_email.html")
    html = file_path.read_text()

    html = html.replace("{{name}}", name)
    html = html.replace("{{email}}", email)
    html = html.replace("{{password}}", password)
    html = html.replace("{{password}}", "Your chosen password")


    return html