from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from PIL import Image
import easyocr
import pytesseract
import cv2
import numpy as np
import re
import os
from datetime import datetime, timedelta
from dateutil import parser
import tempfile
from abc import ABC, abstractmethod

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///costco_receipts.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

db = SQLAlchemy(app)

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

class OCREngine(ABC):
    @abstractmethod
    def extract_text(self, image_path):
        """Extract text from image using the OCR engine"""
        pass

class EasyOCREngine(OCREngine):
    def __init__(self):
        self.reader = easyocr.Reader(['en'])
    
    def extract_text(self, image_path):
        try:
            # Preprocess image
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError("Could not read image file")
            
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Apply preprocessing
            denoised = cv2.fastNlMeansDenoising(gray)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            enhanced = clahe.apply(denoised)
            binary = cv2.adaptiveThreshold(enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                         cv2.THRESH_BINARY, 11, 2)
            
            # Extract text using EasyOCR
            results = self.reader.readtext(binary)
            text = '\n'.join([result[1] for result in results])
            
            print(f"EasyOCR Extracted text length: {len(text)}")
            print("FULL EXTRACTED TEXT:")
            print(text)
            print("="*50)
            
            return text
        except Exception as e:
            print(f"EasyOCR Error: {e}")
            return ""

class TesseractEngine(OCREngine):
    def __init__(self):
        self.configs = [
            '--oem 3 --psm 6',  # Assume uniform text
            '--oem 3 --psm 4',  # Assume single column of text
            '--oem 3 --psm 3'   # Auto page segmentation
        ]
    
    def extract_text(self, image_path):
        try:
            # Preprocess image
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError("Could not read image file")
            
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Apply preprocessing
            denoised = cv2.fastNlMeansDenoising(gray)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            enhanced = clahe.apply(denoised)
            binary = cv2.adaptiveThreshold(enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                         cv2.THRESH_BINARY, 11, 2)
            
            # Try different Tesseract configurations
            best_text = ""
            for config in self.configs:
                text = pytesseract.image_to_string(binary, config=config)
                if len(text) > len(best_text):
                    best_text = text
            
            print(f"Tesseract Extracted text length: {len(best_text)}")
            print("FULL EXTRACTED TEXT:")
            print(best_text)
            print("="*50)
            
            return best_text
        except Exception as e:
            print(f"Tesseract Error: {e}")
            return ""

class MultiAttemptOCREngine(OCREngine):
    def __init__(self):
        self.easy_ocr = EasyOCREngine()
        self.tesseract = TesseractEngine()
    
    def extract_text(self, image_path):
        # First attempt with EasyOCR
        text = self.easy_ocr.extract_text(image_path)
        if self._is_valid_text(text):
            return text
        
        # Second attempt with EasyOCR (different preprocessing)
        text = self._try_easy_ocr_alternative(image_path)
        if self._is_valid_text(text):
            return text
        
        # Third attempt with Tesseract
        text = self.tesseract.extract_text(image_path)
        if self._is_valid_text(text):
            return text
        
        # Fourth attempt with Tesseract (different preprocessing)
        text = self._try_tesseract_alternative(image_path)
        if self._is_valid_text(text):
            return text
        
        return text  # Return the last attempt's result
    
    def _is_valid_text(self, text):
        """Check if the extracted text is valid"""
        if not text:
            return False
        
        # Check for minimum content
        if len(text) < 50:  # Minimum length threshold
            return False
        
        # Check for common receipt elements
        receipt_indicators = ['RECEIPT', 'TOTAL', 'SUBTOTAL', 'TAX', 'ITEM']
        if not any(indicator in text.upper() for indicator in receipt_indicators):
            return False
        
        return True
    
    def _try_easy_ocr_alternative(self, image_path):
        """Alternative EasyOCR attempt with different preprocessing"""
        try:
            image = cv2.imread(image_path)
            if image is None:
                return ""
            
            # Alternative preprocessing
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
            
            # Extract text
            results = self.easy_ocr.reader.readtext(thresh)
            text = '\n'.join([result[1] for result in results])
            
            print("EasyOCR Alternative attempt text length:", len(text))
            return text
        except Exception as e:
            print(f"EasyOCR Alternative Error: {e}")
            return ""
    
    def _try_tesseract_alternative(self, image_path):
        """Alternative Tesseract attempt with different preprocessing"""
        try:
            image = cv2.imread(image_path)
            if image is None:
                return ""
            
            # Alternative preprocessing
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
            
            # Try different Tesseract configurations
            configs = [
                '--oem 1 --psm 6',  # Legacy engine
                '--oem 2 --psm 6',  # Legacy + LSTM
                '--oem 3 --psm 6'   # Default
            ]
            
            best_text = ""
            for config in configs:
                text = pytesseract.image_to_string(thresh, config=config)
                if len(text) > len(best_text):
                    best_text = text
            
            print("Tesseract Alternative attempt text length:", len(best_text))
            return best_text
        except Exception as e:
            print(f"Tesseract Alternative Error: {e}")
            return ""

class ReceiptParser:
    def __init__(self, ocr_engine):
        self.ocr_engine = ocr_engine
        self.item_patterns = [
            # Pattern for standard item format: item_number, description, price
            r'(\d{6,8})\s+([A-Za-z0-9\s/\-&\.\,\']+?)\s+(\d+\.\d{2})(?:\s*[^\d\s]+)?',
            # Pattern for items with asterisks
            r'(\d{6,8})\*?\s+([A-Za-z0-9\s/\-&\.\,\']+?)\s+(\d+\.\d{2})(?:\s*[^\d\s]+)?',
            # Pattern for discounted items
            r'(\d{6,8})\s+([A-Za-z0-9\s/\-&\.\,\']+?)\s+\-(\d+\.\d{2})(?:\s*[^\d\s]+)?',
            # Pattern for items with dash after price
            r'(\d{6,8})\s+([A-Za-z0-9\s/\-&\.\,\']+?)\s+(\d+\.\d{2}-)(?:\s*[^\d\s]+)?',
        ]
        self.store_pattern = r'([A-Z\s]+#\d+)'
        self.address_pattern = r'(\d+\s+[A-Z\s]+(?:BLVD|AVE|ST|RD|DR|LN|CT|WAY))\s*([A-Z\s]+,\s*[A-Z]{2}\s*\d{5})'
    
    def parse_receipt(self, image_path):
        """Parse receipt image and extract structured data"""
        # Extract text using OCR
        text = self.ocr_engine.extract_text(image_path)
        if not text:
            return None
        
        # Parse the extracted text
        lines = text.split('\n')
        store_info = self._extract_store_info(text)
        
        # Use Costco-specific format parsing
        print("Using Costco format parsing...")
        items = self._parse_costco_format(lines)
        
        # If no items found, try looser matching
        if not items:
            print("No items found with Costco format, trying looser matching...")
            items = self._loose_item_matching(lines)
        
        # Validate items before returning
        valid_items = []
        for item in items:
            if self._is_valid_item(item):
                valid_items.append(item)
        
        print(f"Final valid items found: {len(valid_items)}")
        for item in valid_items:
            if item.get('discount', 0) > 0:
                print(f"  - {item['item_number']}: {item['description']} - Original: ${item.get('original_price', item['price']):.2f}, Discount: ${item['discount']:.2f}, Final: ${item['price']:.2f}")
            else:
                print(f"  - {item['item_number']}: {item['description']} - ${item['price']:.2f}")
        
        return {
            'store_info': store_info,
            'items': valid_items
        }
    
    def _parse_costco_format(self, lines):
        """Parse Costco-specific receipt format with E indicators and various discount patterns"""
        items = []
        parsed_entries = []
        i = 0
        
        # First pass: Parse all entries into structured format
        while i < len(lines):
            line = lines[i].strip()
            
            # Look for 'E' indicator (start of item)
            if line == 'E' and i + 3 < len(lines):
                try:
                    item_number_line = lines[i + 1].strip()
                    description_line = lines[i + 2].strip()
                    price_line = lines[i + 3].strip()
                    
                    # Validate item number (6-8 digits)
                    if re.match(r'^\d{6,8}$', item_number_line):
                        # Extract price and currency indicator
                        price_match = re.match(r'^(\d+\.\d{2})\s*([NY-]?)$', price_line)
                        if price_match:
                            amount = float(price_match.group(1))
                            currency_indicator = price_match.group(2) or 'N'
                            
                            # Determine entry type based on description and currency indicator
                            if description_line.startswith('/'):
                                # This is a discount entry
                                parsed_entries.append({
                                    "type": "discount",
                                    "discount_code": item_number_line,
                                    "referenced_product": description_line[1:],  # Remove the '/' prefix
                                    "discount_amount": amount,
                                    "currency_indicator": currency_indicator
                                })
                            else:
                                # This is a regular item
                                parsed_entries.append({
                                    "type": "item",
                                    "product_code": item_number_line,
                                    "description": description_line,
                                    "amount": amount,
                                    "currency_indicator": currency_indicator
                                })
                            
                            i += 4
                            continue
                except (ValueError, IndexError):
                    pass
            
            # Handle discount pattern: discount_code, product_code, discount_amount- (CHECK THIS FIRST!)
            elif (re.match(r'^\d{6,8}$', line) and i + 2 < len(lines) and
                  re.match(r'^\d{6,8}$', lines[i + 1].strip()) and
                  re.match(r'^\d+\.\d{2}-$', lines[i + 2].strip())):
                try:
                    discount_code = line
                    product_code = lines[i + 1].strip()
                    discount_amount_str = lines[i + 2].strip()
                    
                    # Extract discount amount (remove the '-' at the end)
                    discount_amount = float(discount_amount_str[:-1])
                    
                    parsed_entries.append({
                        "type": "standalone_discount",
                        "discount_code": discount_code,
                        "referenced_product": product_code,
                        "discount_amount": discount_amount
                    })
                    
                    print(f"Found discount pattern: Discount code {discount_code}, Product {product_code}, Amount ${discount_amount:.2f}")
                    
                    i += 3
                    continue
                except (ValueError, IndexError):
                    pass
            
            # Handle items without 'E' prefix - look for product code, description, price pattern
            elif (re.match(r'^\d{4,8}$', line) and i + 2 < len(lines) and
                  not re.match(r'^\d+\.\d{2}', lines[i + 1].strip()) and  # Description shouldn't start with price
                  (re.match(r'^\d+\.\d{2}\s*[NY]?$', lines[i + 2].strip()) or  # Regular price
                   re.match(r'^\d+\.\d{2}-$', lines[i + 2].strip()))):  # OR discount amount with dash
                try:
                    item_number_line = line
                    description_line = lines[i + 1].strip()
                    price_line = lines[i + 2].strip()
                    
                    # Check if this is a discount amount (ends with -)
                    if re.match(r'^\d+\.\d{2}-$', price_line):
                        # This is a discount entry
                        discount_amount = float(price_line[:-1])  # Remove the '-'
                        
                        if description_line.startswith('/'):
                            # This is an inline discount
                            parsed_entries.append({
                                "type": "discount",
                                "discount_code": item_number_line,
                                "referenced_product": description_line[1:],  # Remove the '/' prefix
                                "discount_amount": discount_amount,
                                "currency_indicator": "-"
                            })
                            print(f"Found inline discount: Discount code {item_number_line}, Product {description_line[1:]}, Amount ${discount_amount:.2f}")
                        else:
                            # This might be a standalone discount without the 3-line pattern
                            parsed_entries.append({
                                "type": "standalone_discount",
                                "discount_code": item_number_line,
                                "referenced_product": description_line,  # Description is the product code
                                "discount_amount": discount_amount
                            })
                            print(f"Found standalone discount (2-line): Discount code {item_number_line}, Product {description_line}, Amount ${discount_amount:.2f}")
                    else:
                        # Regular item
                        price_match = re.match(r'^(\d+\.\d{2})\s*([NY-]?)$', price_line)
                        if price_match:
                            amount = float(price_match.group(1))
                            currency_indicator = price_match.group(2) or 'N'
                            
                            # This is a regular item
                            parsed_entries.append({
                                "type": "item",
                                "product_code": item_number_line,
                                "description": description_line,
                                "amount": amount,
                                "currency_indicator": currency_indicator
                            })
                    
                    i += 3
                    continue
                except (ValueError, IndexError):
                    pass
            
            # Handle quantity-based items (like "3" for WHOLE MILK)
            elif re.match(r'^\d{1,2}$', line) and i + 2 < len(lines):
                try:
                    quantity = int(line)
                    description_line = lines[i + 1].strip()
                    price_line = lines[i + 2].strip()
                    
                    price_match = re.match(r'^(\d+\.\d{2})\s*([NY]?)$', price_line)
                    if price_match and quantity <= 10:
                        amount = float(price_match.group(1))
                        currency_indicator = price_match.group(2) or 'N'
                        
                        # Look for item number in nearby lines
                        item_number = None
                        for j in range(max(0, i-3), min(len(lines), i+1)):
                            if re.match(r'^\d{6,8}$', lines[j].strip()):
                                item_number = lines[j].strip()
                                break
                        
                        if item_number:
                            parsed_entries.append({
                                "type": "item",
                                "product_code": item_number,
                                "description": f"{description_line} (Qty: {quantity})",
                                "amount": amount,
                                "currency_indicator": currency_indicator
                            })
                            
                            i += 3
                            continue
                except (ValueError, IndexError):
                    pass
            
            i += 1
        
        # Second pass: Process parsed entries and apply discounts
        print(f"Parsed {len(parsed_entries)} entries from receipt")
        for entry in parsed_entries:
            print(f"  Entry: {entry['type']} - Product: {entry.get('product_code', entry.get('referenced_product', 'N/A'))}, Amount: {entry.get('amount', entry.get('discount_amount', 'N/A'))}")
        
        print("\n=== PROCESSING ITEMS AND APPLYING DISCOUNTS ===")
        
        for i, entry in enumerate(parsed_entries):
            if entry["type"] == "item":
                product_info = {
                    "item_number": entry["product_code"],
                    "description": entry["description"],
                    "price": entry["amount"],
                    "original_price": entry["amount"],
                    "discount": 0.0
                }
                
                print(f"\nProcessing item: {entry['product_code']} - {entry['description']} - ${entry['amount']:.2f}")
                
                # Look for discounts that apply to this item
                discount_amount = 0.0
                
                # Check for inline discount (next entry with "/" prefix)
                if (i + 1 < len(parsed_entries) and 
                    parsed_entries[i + 1]["type"] == "discount" and
                    parsed_entries[i + 1]["referenced_product"] == entry["product_code"]):
                    discount_amount = parsed_entries[i + 1]["discount_amount"]
                    print(f"  → Found inline discount: ${discount_amount:.2f} for {entry['product_code']}")
                
                # Check for standalone discount by matching product codes
                print(f"  → Checking for standalone discounts for product {entry['product_code']}...")
                for j, discount_entry in enumerate(parsed_entries):
                    if discount_entry["type"] == "standalone_discount":
                        print(f"    Discount entry {j}: code={discount_entry['discount_code']}, product={discount_entry['referenced_product']}, amount=${discount_entry['discount_amount']:.2f}")
                        if discount_entry["referenced_product"] == entry["product_code"]:
                            discount_amount += discount_entry["discount_amount"]
                            print(f"    ✓ MATCH! Found standalone discount: ${discount_entry['discount_amount']:.2f} for product {entry['product_code']} (discount code: {discount_entry['discount_code']})")
                        else:
                            print(f"    ✗ No match: {discount_entry['referenced_product']} != {entry['product_code']}")
                
                # Apply discount and calculate final price
                if discount_amount > 0:
                    product_info["discount"] = discount_amount
                    product_info["price"] = max(0, entry["amount"] - discount_amount)  # Ensure price doesn't go negative
                    print(f"  → Applied discount: Original ${entry['amount']:.2f} - Discount ${discount_amount:.2f} = Final ${product_info['price']:.2f}")
                else:
                    print(f"  → No discount applied")
                
                if self._is_valid_item(product_info):
                    items.append(product_info)
                    if discount_amount > 0:
                        print(f"✓ Item with discount: {product_info['item_number']} - {product_info['description']} - Original: ${product_info['original_price']:.2f}, Discount: ${discount_amount:.2f}, Final: ${product_info['price']:.2f}")
                    else:
                        print(f"✓ Regular item: {product_info['item_number']} - {product_info['description']} - ${product_info['price']:.2f}")
                else:
                    print(f"✗ Item failed validation: {product_info}")
        
        print(f"\n=== FINAL SUMMARY ===")
        print(f"Total valid items: {len(items)}")
        for item in items:
            if item['discount'] > 0:
                print(f"  {item['item_number']}: {item['description']} - Original: ${item['original_price']:.2f}, Discount: ${item['discount']:.2f}, Final: ${item['price']:.2f}")
            else:
                print(f"  {item['item_number']}: {item['description']} - ${item['price']:.2f}")
        
        return items
    
    def _is_valid_item(self, item):
        """Validate an item has all required fields with valid values"""
        try:
            # Check required fields exist and are not empty
            if not item.get('item_number') or not item.get('description'):
                return False
            
            # Validate item number format (6-8 digits)
            if not re.match(r'^\d{6,8}$', item['item_number']):
                return False
            
            # Validate price is a positive number
            price = item.get('price')
            if not isinstance(price, (int, float)) or price <= 0:
                return False
            
            # Validate description is not too short and contains letters
            description = item['description'].strip()
            if len(description) < 2 or not re.search(r'[A-Za-z]', description):
                return False
            
            return True
        except Exception:
            return False
    
    def _extract_store_info(self, text):
        """Extract store information from text"""
        store_info = {'store_number': '', 'address': ''}
        
        # Look for store number
        store_match = re.search(self.store_pattern, text)
        if store_match:
            store_info['store_number'] = store_match.group(1).strip()
        
        # Look for address
        address_match = re.search(self.address_pattern, text)
        if address_match:
            store_info['address'] = f"{address_match.group(1).strip()} {address_match.group(2).strip()}"
        
        return store_info
    
    def _loose_item_matching(self, lines):
        """Try to match items using looser patterns"""
        items = []
        current_item = None
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines or lines that are too short
            if not line or len(line) < 5:
                continue
            
            # Try to find item number
            item_match = re.search(r'(\d{6,8})', line)
            if item_match:
                # If we have a current item, validate and save it
                if current_item and self._is_valid_item(current_item):
                    items.append(current_item)
                
                # Start new item
                current_item = {
                    'item_number': item_match.group(1),
                    'description': '',
                    'price': None
                }
                continue
            
            # Try to find price
            price_match = re.search(r'(\d+\.\d{2})', line)
            if price_match and current_item:
                try:
                    price = float(price_match.group(1))
                    if price > 0:  # Only set price if it's positive
                        current_item['price'] = price
                        # Use the line as description if we don't have one
                        if not current_item['description']:
                            current_item['description'] = line.replace(price_match.group(1), '').strip()
                except ValueError:
                    continue
                continue
            
            # If we have a current item and no description, use this line
            if current_item and not current_item['description']:
                current_item['description'] = line
        
        # Add the last item if it's valid
        if current_item and self._is_valid_item(current_item):
            items.append(current_item)
        
        return items

# Initialize the OCR engine and parser
ocr_engine = MultiAttemptOCREngine()
receipt_parser = ReceiptParser(ocr_engine)

# Database Models
class Receipt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    store_address = db.Column(db.String(500), nullable=False)
    store_number = db.Column(db.String(50), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    receipt_date = db.Column(db.DateTime, nullable=True)
    items = db.relationship('ReceiptItem', backref='receipt', lazy=True, cascade="all, delete-orphan")

class ReceiptItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    receipt_id = db.Column(db.Integer, db.ForeignKey('receipt.id'), nullable=False)
    item_number = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(200), nullable=True)
    price = db.Column(db.Float, nullable=False)  # Final price after discount
    original_price = db.Column(db.Float, nullable=True)  # Original price before discount
    discount = db.Column(db.Float, default=0)  # Discount amount
    date_recorded = db.Column(db.DateTime, default=datetime.utcnow)

@app.route('/')
def index():
    """Home page"""
    return render_template('index.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload_receipt():
    """Handle receipt upload and processing"""
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
            filename = timestamp + filename
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            try:
                # Process the receipt
                print(f"Processing receipt: {filepath}")
                receipt_data = receipt_parser.parse_receipt(filepath)
                
                if not receipt_data or not receipt_data['items']:
                    flash('No items found in the receipt. The image may be unclear or not a valid Costco receipt. Please try with a clearer image or different angle.')
                    os.remove(filepath)
                    return redirect(request.url)
                
                # Save to database
                receipt = Receipt(
                    store_address=receipt_data['store_info']['address'] or 'Unknown Store',
                    store_number=receipt_data['store_info']['store_number'] or 'Unknown'
                )
                db.session.add(receipt)
                db.session.flush()
                
                # Process each item
                price_comparisons = []
                for item_data in receipt_data['items']:
                    # Check for existing lower prices within 30 days
                    thirty_days_ago = datetime.now() - timedelta(days=30)
                    existing_item = ReceiptItem.query.filter(
                        ReceiptItem.item_number == item_data['item_number'],
                        ReceiptItem.date_recorded >= thirty_days_ago
                    ).order_by(ReceiptItem.price.asc()).first()
                    
                    comparison = {
                        'item_number': item_data['item_number'],
                        'description': item_data['description'],
                        'current_price': item_data['price'],
                        'original_price': item_data.get('original_price', item_data['price']),
                        'discount': item_data.get('discount', 0),
                        'is_lowest': True,
                        'existing_price': None,
                        'existing_store': None
                    }
                    
                    if existing_item and existing_item.price < item_data['price']:
                        comparison['is_lowest'] = False
                        comparison['existing_price'] = existing_item.price
                        comparison['existing_store'] = existing_item.receipt.store_address
                    
                    price_comparisons.append(comparison)
                    
                    # Add item to database
                    new_item = ReceiptItem(
                        receipt_id=receipt.id,
                        item_number=item_data['item_number'],
                        description=item_data['description'],
                        price=item_data['price'],
                        original_price=item_data.get('original_price', item_data['price']),
                        discount=item_data.get('discount', 0)
                    )
                    db.session.add(new_item)
                
                db.session.commit()
                
                # Clean up uploaded file
                os.remove(filepath)
                
                flash(f'Successfully processed receipt with {len(receipt_data["items"])} items!', 'success')
                return render_template('results.html', 
                                     comparisons=price_comparisons,
                                     store_info=receipt_data['store_info'])
                
            except Exception as e:
                db.session.rollback()
                if os.path.exists(filepath):
                    os.remove(filepath)
                print(f"Error processing receipt: {str(e)}")
                flash(f'Error processing receipt. Please try with a clearer image. Technical details: {str(e)}')
                return redirect(url_for('upload_receipt'))
        
        else:
            flash('Invalid file type. Please upload an image file.')
            return redirect(request.url)
    
    return render_template('upload.html')

def allowed_file(filename):
    """Check if uploaded file is allowed"""
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/debug/ocr', methods=['POST'])
def debug_ocr():
    """Debug endpoint to test OCR extraction"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
        filename = timestamp + filename
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            # Extract text and parse receipt
            receipt_data = receipt_parser.parse_receipt(filepath)
            
            # Clean up
            os.remove(filepath)
            
            return jsonify({
                'items_found': len(receipt_data['items']) if receipt_data else 0,
                'items': receipt_data['items'] if receipt_data else [],
                'store_info': receipt_data['store_info'] if receipt_data else {}
            })
            
        except Exception as e:
            if os.path.exists(filepath):
                os.remove(filepath)
            return jsonify({'error': str(e)}), 500
    
    return jsonify({'error': 'Invalid file type'}), 400

@app.route('/history')
def history():
    """View receipt history"""
    receipts = Receipt.query.order_by(Receipt.upload_date.desc()).all()
    return render_template('history.html', receipts=receipts)

@app.route('/api/item/<item_number>')
def get_item_history(item_number):
    """API endpoint to get price history for an item"""
    thirty_days_ago = datetime.now() - timedelta(days=30)
    items = ReceiptItem.query.filter(
        ReceiptItem.item_number == item_number,
        ReceiptItem.date_recorded >= thirty_days_ago
    ).order_by(ReceiptItem.date_recorded.desc()).all()
    
    history = []
    for item in items:
        history.append({
            'price': item.price,
            'date': item.date_recorded.isoformat(),
            'store': item.receipt.store_address,
            'store_number': item.receipt.store_number
        })
    
    return jsonify(history)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    port = int(os.environ.get('PORT', 5002))
    app.run(debug=os.environ.get('DEBUG', 'False').lower() == 'true', 
            host='0.0.0.0', port=port) 