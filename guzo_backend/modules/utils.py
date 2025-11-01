# guzo_backend/modules/utils.py
def validate_phone_number(number: str) -> str:
    if not number:
        return None
    number = number.strip().replace(" ", "")
    if number.startswith("+"):
        return number
    elif number.isdigit() and len(number) > 8:
        return f"+{number}"  # add country code if missing
    return None
