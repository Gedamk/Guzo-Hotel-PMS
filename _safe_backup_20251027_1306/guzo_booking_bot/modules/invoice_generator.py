# -*- coding: utf-8 -*-
"""
invoice_generator.py — PDF Invoice Generator
--------------------------------------------
Generates branded invoice for Guzo Guest Assist.
"""

import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

def generate_invoice_pdf(guest_name, amount, currency, confirmation_id, hotel_name):
    """Generate a simple professional invoice PDF."""
    os.makedirs("invoices", exist_ok=True)
    filename = f"invoices/invoice_{confirmation_id}.pdf"

    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4

    # Header
    c.setFont("Helvetica-Bold", 18)
    c.drawString(170, height - 80, "Guzo Guest Assist Invoice")

    # Details
    c.setFont("Helvetica", 12)
    y = height - 130
    c.drawString(50, y, f"Hotel: {hotel_name}");  y -= 20
    c.drawString(50, y, f"Guest: {guest_name}");  y -= 20
    c.drawString(50, y, f"Amount: {amount} {currency}");  y -= 20
    c.drawString(50, y, f"Confirmation ID: {confirmation_id}");  y -= 20
    c.drawString(50, y, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}");  y -= 40

    c.line(50, y, 550, y)
    y -= 60
    c.setFont("Helvetica-Oblique", 10)
    c.drawString(50, y, "Thank you for booking with Guzo Guest Assist.")
    c.save()

    return filename
