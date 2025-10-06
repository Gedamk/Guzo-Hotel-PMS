# guzo_booking_bot/modules/template_loader.py

import os

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "../../email_templates")

def load_template(template_name, placeholders=None):
    """
    Load an HTML template and replace placeholders.
    :param template_name: e.g. 'booking_confirmation.html'
    :param placeholders: dict of { "{{ placeholder }}": "value" }
    """
    file_path = os.path.join(TEMPLATE_DIR, template_name)

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        return f"❌ Template {template_name} not found."

    if placeholders:
        for key, value in placeholders.items():
            content = content.replace("{{ " + key + " }}", str(value))

    return content
