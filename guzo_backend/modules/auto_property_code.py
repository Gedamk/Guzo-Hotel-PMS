# -*- coding: utf-8 -*-
"""
auto_property_code.py – Auto-generate property codes for Hotel Contacts Master
"""

import re
from guzo_backend.modules import google_sheets


def generate_property_code(hotel_name: str, existing_codes: list) -> str:
    """Generate a unique property code (e.g., SOFI01, SKYL02)."""
    base = re.sub(r'[^A-Za-z]', '', hotel_name)[:4].upper()
    similar = [c for c in existing_codes if c.startswith(base)]
    next_num = len(similar) + 1
    return f"{base}{next_num:02d}"


def auto_assign_property_codes():
    """Automatically fill in missing Property Codes in the Hotel Master Sheet."""
    print("Loading Hotel Contacts Master Sheet...")
    client = google_sheets.init_client()
    sheet_id = google_sheets.get_hotel_contact_sheet_id()
    sheet = client.open_by_key(sheet_id).sheet1

    data = sheet.get_all_records()
    existing = [r["Property Code"] for r in data if r.get("Property Code")]

    updates = []
    for i, row in enumerate(data, start=2):
        if not row.get("Property Code"):
            new_code = generate_property_code(row["Hotel Name"], existing)
            updates.append((i, new_code))
            existing.append(new_code)
            print(f"New code assigned → {row['Hotel Name']}: {new_code}")

    for row_idx, code in updates:
        sheet.update_cell(row_idx, 2, code)  # Column 2 = Property Code

    print(f"{len(updates)} property codes auto-assigned.")


if __name__ == "__main__":
    auto_assign_property_codes()
