"""
Synthetic Indian Invoice / Receipt Generator
-----------------------------------------------
Generates realistic-looking Indian GST invoices (image + ground-truth JSON)
for two purposes:
  1. A ready-to-use test set to demo/evaluate the pipeline end-to-end
     without waiting on external dataset downloads.
  2. Training data to fine-tune the LayoutLM field-extraction head so it
     learns Indian-specific patterns: GSTIN format, â‚¹ currency, Indian
     company/city names, dd/mm/yyyy dates, CGST/SGST/IGST split.

For a *real* dataset (recommended before reporting final numbers in your
project report), see data/README_datasets.md for links to:
  - Kaggle "Indian Financial Documents Dataset"
  - ICDAR SROIE (receipts, adapt currency formatting)
  - Indian GST invoice samples released by GSTN / e-invoice portal (public
    sample JSON schema, useful for validating field names)

Usage:
  python generate_synthetic_indian_invoices.py --n 200 --out synthetic_indian_invoices
"""

import argparse
import json
import os
import random
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.validation import gstin_check_digit
from datetime import datetime, timedelta

from PIL import Image, ImageDraw, ImageFont

random.seed(42)

INDIAN_COMPANIES = [
    "Shree Balaji Traders", "Ganesh Enterprises", "Reliance Digital Solutions",
    "Tata Consultancy Supplies", "Suryodaya Textiles Pvt Ltd", "Kaveri Electronics",
    "Om Sai Distributors", "Mahalaxmi Hardware Mart", "Bharat Steel Corporation",
    "Nirmal Agro Foods", "Sunrise Furniture Works", "Krishna Auto Spares",
]

INDIAN_CITIES_STATES = [
    ("Mumbai", "Maharashtra", "27"), ("Pune", "Maharashtra", "27"),
    ("Bengaluru", "Karnataka", "29"), ("Chennai", "Tamil Nadu", "33"),
    ("Delhi", "Delhi", "07"), ("Ahmedabad", "Gujarat", "24"),
    ("Kolkata", "West Bengal", "19"), ("Jaipur", "Rajasthan", "08"),
    ("Hyderabad", "Telangana", "36"), ("Lucknow", "Uttar Pradesh", "09"),
]

ITEMS = [
    "Laptop Stand", "Wireless Mouse", "A4 Paper Ream", "Office Chair",
    "LED Bulb 9W", "HDMI Cable 2m", "Steel Water Bottle", "Printer Cartridge",
    "Notebook Pack of 5", "USB Hub 4-Port", "Cotton Fabric (per meter)",
    "Ball Bearing Set", "Fertilizer Bag 25kg", "Wooden Table",
]


def random_gstin(state_code):
    letters = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=5))
    digits = "".join(random.choices("0123456789", k=4))
    entity_letter = random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    prefix = f"{state_code}{letters}{digits}{entity_letter}1Z"
    return prefix + gstin_check_digit(prefix)


def random_pan():
    letters1 = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=5))
    digits = "".join(random.choices("0123456789", k=4))
    letter2 = random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    return f"{letters1}{digits}{letter2}"


def build_invoice_record(idx):
    seller = random.choice(INDIAN_COMPANIES)
    buyer = random.choice([c for c in INDIAN_COMPANIES if c != seller])
    city, state, state_code = random.choice(INDIAN_CITIES_STATES)
    gstin = random_gstin(state_code)
    pan = gstin[2:12]
    invoice_no = f"INV-{2026}{idx:05d}"
    date = (datetime(2026, 1, 1) + timedelta(days=random.randint(0, 240))).strftime("%d/%m/%Y")
    due_date = (datetime.strptime(date, "%d/%m/%Y") + timedelta(days=15)).strftime("%d/%m/%Y")

    n_items = random.randint(2, 5)
    line_items = []
    subtotal = 0.0
    for _ in range(n_items):
        name = random.choice(ITEMS)
        qty = random.randint(1, 10)
        rate = round(random.uniform(150, 5000), 2)
        amount = round(qty * rate, 2)
        subtotal += amount
        line_items.append({"item": name, "qty": qty, "rate": rate, "amount": amount})

    gst_rate = random.choice([5, 12, 18, 28])
    tax_amount = round(subtotal * gst_rate / 100, 2)
    total = round(subtotal + tax_amount, 2)

    return {
        "invoice_number": invoice_no,
        "invoice_date": date,
        "due_date": due_date,
        "vendor_name": seller,
        "bill_to": buyer,
        "place_of_supply": f"{city}, {state}",
        "gstin": gstin,
        "pan": pan,
        "gst_rate_pct": gst_rate,
        "line_items": line_items,
        "subtotal": round(subtotal, 2),
        "tax_amount": tax_amount,
        "total_amount": total,
    }


def render_invoice_image(record, out_path, font_path=None):
    W, H = 1240, 1754  # A4 at ~150dpi
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)

    try:
        font_bold = ImageFont.truetype(font_path or ("C:/Windows/Fonts/arialbd.ttf" if os.name == "nt" else "DejaVuSans-Bold.ttf"), 28)
        font_reg = ImageFont.truetype(font_path or ("C:/Windows/Fonts/arial.ttf" if os.name == "nt" else "DejaVuSans.ttf"), 20)
        font_small = ImageFont.truetype(font_path or ("C:/Windows/Fonts/arial.ttf" if os.name == "nt" else "DejaVuSans.ttf"), 16)
    except Exception:
        font_bold = ImageFont.load_default()
        font_reg = ImageFont.load_default()
        font_small = ImageFont.load_default()

    y = 40
    draw.text((40, y), record["vendor_name"], font=font_bold, fill="black"); y += 40
    draw.text((40, y), f"GSTIN: {record['gstin']}   PAN: {record['pan']}", font=font_small, fill="black"); y += 30
    draw.text((40, y), f"Place of Supply: {record['place_of_supply']}", font=font_small, fill="black"); y += 40

    draw.line([(40, y), (W - 40, y)], fill="black", width=2); y += 20
    draw.text((40, y), "TAX INVOICE", font=font_bold, fill="black"); y += 40

    draw.text((40, y), f"Invoice No: {record['invoice_number']}", font=font_reg, fill="black")
    draw.text((650, y), f"Date: {record['invoice_date']}", font=font_reg, fill="black"); y += 30
    draw.text((40, y), f"Bill To: {record['bill_to']}", font=font_reg, fill="black")
    draw.text((650, y), f"Due Date: {record['due_date']}", font=font_reg, fill="black"); y += 40

    # Table header
    col_x = [40, 560, 720, 880, 1040]
    headers = ["Item", "Qty", "Rate", "Amount", ""]
    for x, h in zip(col_x, headers):
        draw.text((x, y), h, font=font_bold, fill="black")
    y += 28
    draw.line([(40, y), (W - 40, y)], fill="black", width=1); y += 10

    for item in record["line_items"]:
        draw.text((col_x[0], y), item["item"], font=font_small, fill="black")
        draw.text((col_x[1], y), str(item["qty"]), font=font_small, fill="black")
        draw.text((col_x[2], y), f"Rs.{item['rate']:.2f}", font=font_small, fill="black")
        draw.text((col_x[3], y), f"Rs.{item['amount']:.2f}", font=font_small, fill="black")
        y += 26

    y += 10
    draw.line([(40, y), (W - 40, y)], fill="black", width=1); y += 20
    draw.text((800, y), f"Subtotal: Rs.{record['subtotal']:.2f}", font=font_reg, fill="black"); y += 28
    draw.text((800, y), f"GST ({record['gst_rate_pct']}%): Rs.{record['tax_amount']:.2f}", font=font_reg, fill="black"); y += 28
    draw.text((800, y), f"Total: Rs.{record['total_amount']:.2f}", font=font_bold, fill="black"); y += 40

    draw.text((40, H - 60), "This is a computer-generated synthetic invoice for ML training/demo purposes.",
               font=font_small, fill="gray")

    img.save(out_path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=200, help="number of synthetic invoices")
    ap.add_argument("--out", type=str, default="synthetic_indian_invoices")
    args = ap.parse_args()

    img_dir = os.path.join(args.out, "images")
    os.makedirs(img_dir, exist_ok=True)

    all_records = []
    for i in range(1, args.n + 1):
        record = build_invoice_record(i)
        img_path = os.path.join(img_dir, f"invoice_{i:05d}.png")
        render_invoice_image(record, img_path)
        record["image_path"] = "images/" + os.path.basename(img_path)
        all_records.append(record)

    with open(os.path.join(args.out, "ground_truth.json"), "w") as f:
        json.dump(all_records, f, indent=2)

    print(f"Generated {args.n} synthetic Indian invoices in {args.out}/")


if __name__ == "__main__":
    main()
