from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from PIL import Image
import pytesseract
import cv2
import numpy as np
import re
import os
from datetime import datetime, timedelta
from dateutil import parser
import tempfile

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///costco_receipts.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

db = SQLAlchemy(app)

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

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

class ReceiptProcessor:
    def __init__(self):
        # More flexible patterns for different receipt formats
        self.item_patterns = [
            # P0: Standard pattern: item_number, description, price. Price can be "12.34" or "12.34-"
            r'(\d{6,8})\s+([A-Za-z0-9\s/\-&\.\,\']+?)\s+((?:\d+\.\d{2})(?:-)?)(?:\s*[^\d\s]+)?',
            # P1: Alternative pattern with more flexible spacing. Price "12.34"
            r'(\d{6,8})\s*([A-Za-z0-9\s/\-&\.\,\']{10,50}?)\s+(\d+\.\d{2})(?:\s*[^\d\s]+)?',
            # P2: Pattern for items with asterisks or special characters. Price "12.34"
            r'(\d{6,8})\*?\s+([A-Za-z0-9\s/\-&\.\,\']+?)\s+(\d+\.\d{2})(?:\s*[^\d\s]+)?',
            # P3: Pattern for discounted items (dash before price). Price "12.34" (sign is outside group)
            r'(\d{6,8})\s+([A-Za-z0-9\s/\-&\.\,\']+?)\s+\-(\d+\.\d{2})(?:\s*[^\d\s]+)?',
            # P4: Pattern for Costco discount format (dash after price, general item). Price is "12.34-" (sign in group)
            r'(\d{6,8})\s+([A-Za-z0-9\s/\-&\.\,\']+?)\s+(\d+\.\d{2}-)(?:\s*[^\d\s]+)?',
            # P5: Pattern for Costco discount line format: "352844 1797100 3.00- |,". Price is "12.34-" (sign in group)
            r'(\d{6,8})\s+(\d{6,8})\s+(\d+\.\d{2}-)\s*(?:\|,)?',
        ]
        self.store_pattern = r'([A-Z\s]+#\d+)'
        self.address_pattern = r'(\d+\s+[A-Z\s]+(?:BLVD|AVE|ST|RD|DR|LN|CT|WAY))\s*([A-Z\s]+,\s*[A-Z]{2}\s*\d{5})'
        
    def preprocess_image(self, image_path):
        """Enhanced image preprocessing for better OCR results"""
        # Read image
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError("Could not read image file")
        
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Apply multiple preprocessing techniques
        # 1. Noise reduction
        denoised = cv2.fastNlMeansDenoising(gray)
        
        # 2. Contrast enhancement
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced = clahe.apply(denoised)
        
        # 3. Adaptive thresholding for better text extraction
        binary = cv2.adaptiveThreshold(enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                     cv2.THRESH_BINARY, 11, 2)
        
        # 4. Morphological operations to clean up text
        kernel = np.ones((1,1), np.uint8)
        cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        
        return cleaned
    
    def extract_text_from_image(self, image_path):
        """Extract text from receipt image using multiple OCR configurations"""
        try:
            # Preprocess image
            processed_image = self.preprocess_image(image_path)
            
            # Try multiple OCR configurations
            ocr_configs = [
                '--psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz .,/$-#*',
                '--psm 4 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz .,/$-#*',
                '--psm 6',
                '--psm 4',
                '--psm 3'
            ]
            
            best_text = ""
            for config in ocr_configs:
                try:
                    text = pytesseract.image_to_string(processed_image, config=config)
                    if len(text.strip()) > len(best_text.strip()):
                        best_text = text
                except:
                    continue
            
            # If no good text extracted, try with original image
            if len(best_text.strip()) < 50:
                original_image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
                best_text = pytesseract.image_to_string(original_image, config='--psm 6')
            
            # Debug: Print extracted text (remove in production)
            print(f"OCR Extracted text length: {len(best_text)}")
            print("FULL EXTRACTED TEXT:")
            print(best_text)
            print("="*50)
            
            return best_text
        except Exception as e:
            print(f"OCR Error: {e}")
            return ""
    
    def parse_receipt_text(self, text):
        """Parse extracted text to get structured data"""
        lines = text.split('\n')
        
        # Extract store information
        store_info = self.extract_store_info(text)
        
        # Extract items
        items = self.extract_items(text)
        
        # Try to extract receipt date
        receipt_date = self.extract_receipt_date(text)
        
        return {
            'store_info': store_info,
            'items': items,
            'receipt_date': receipt_date
        }
    
    def extract_store_info(self, text):
        """Extract store number and address"""
        store_info = {'store_number': '', 'address': ''}
        
        # Look for store number pattern (e.g., "HAYWARD #1061")
        store_match = re.search(r'([A-Z\s]+)#(\d+)', text)
        if store_match:
            store_info['store_number'] = f"{store_match.group(1).strip()} #{store_match.group(2)}"
        
        # Look for address pattern
        address_lines = []
        lines = text.split('\n')
        for i, line in enumerate(lines):
            # Look for street address pattern
            if re.search(r'\d+\s+[A-Z\s]+(BLVD|AVE|ST|RD|DR|LN|CT|WAY)', line):
                address_lines.append(line.strip())
                # Check next line for city, state, zip
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if re.search(r'[A-Z\s]+,\s*[A-Z]{2}\s*\d{5}', next_line):
                        address_lines.append(next_line)
                break
        
        if address_lines:
            store_info['address'] = ' '.join(address_lines)
        
        return store_info
    
    def extract_items(self, text):
        """Extract item numbers, descriptions, and prices with multiple patterns"""
        items = []
        lines = text.split('\n')
        
        print(f"Processing {len(lines)} lines for items...")
        
        raw_items = {} 
        for line_num, line in enumerate(lines):
            line = line.strip()
            if len(line) < 10:
                continue
            if line in raw_items:
                continue
                
            item_found_this_line = False
            for pattern_num, pattern in enumerate(self.item_patterns):
                if item_found_this_line:
                    break
                    
                matches = re.findall(pattern, line, re.IGNORECASE)
                for match_parts in matches:
                    # Ensure match_parts is a tuple (it will be if groups are defined)
                    current_match_tuple = match_parts if isinstance(match_parts, tuple) else (match_parts,)

                    if len(current_match_tuple) < 3: # Need at least item, desc, price
                        continue

                    item_number_candidate = current_match_tuple[0]
                    description_candidate = current_match_tuple[1].strip()
                    price_str_candidate = current_match_tuple[2].strip() # P0 captures "12.34" or "12.34-", P3 captures "12.34", P4/P5 capture "12.34-"

                    # --- Start Refined Description Filter ---
                    passes_description_filter = True # Assume valid by default
                    if pattern_num == 5: # P5: Costco specific discount r'(\d{6,8})\s+(\d{6,8})\s+(\d+\.\d{2}-)...'
                        # For P5, description_candidate *must* be a 6-8 digit item code
                        if not (description_candidate.isdigit() and 6 <= len(description_candidate) <= 8):
                            passes_description_filter = False 
                    else: # For other patterns (P0-P4)
                        # Reject if too short, or if all digits (usually not a valid description)
                        if len(description_candidate) < 3 or description_candidate.isdigit():
                            passes_description_filter = False
                    
                    if not passes_description_filter:
                        # print(f"DEBUG: Line skipped by description filter. Pattern {pattern_num}, Desc: '{description_candidate}', Line: '{line}'")
                        continue
                    # --- End Refined Description Filter ---

                    # --- Start Refined Price Parsing ---
                    price = 0.0
                    try:
                        price_numeric_part = price_str_candidate
                        is_negative = False

                        if price_str_candidate.endswith('-'): # Handles P0 (if "12.34-"), P4, P5
                            price_numeric_part = price_str_candidate[:-1]
                            is_negative = True
                        
                        # For P3 (r'... \-(\d+\.\d{2})'), price_str_candidate is "3.00", but pattern implies negative.
                        if pattern_num == 3: 
                            is_negative = True
                        
                        # Validate numeric part before float conversion
                        if not re.match(r'^\d+\.\d{2}$', price_numeric_part):
                            # print(f"DEBUG: Invalid numeric price part: '{price_numeric_part}' from '{price_str_candidate}' (Pattern {pattern_num}) line: '{line}'. Skipping.")
                            continue

                        price_abs = float(price_numeric_part)
                        price = -price_abs if is_negative else price_abs
                    except ValueError:
                        # print(f"DEBUG: ValueError converting price: '{price_str_candidate}' (numeric part: '{price_numeric_part}') (Pattern {pattern_num}) line: '{line}'. Skipping.")
                        continue
                    # --- End Refined Price Parsing ---
                    
                    raw_items[line] = {
                        'item_number': item_number_candidate,
                        'description': description_candidate,
                        'price': price,
                        'original_line': line
                    }
                    print(f"Raw item found (Pattern {pattern_num}): {item_number_candidate} - {description_candidate} - ${price:.2f}")
                    item_found_this_line = True
                    break # Found a match with this pattern, move to next line
        
        # Second pass: separate regular items from discount items
        regular_items = {}
        discount_items_raw = []
        
        print(f"=== SECOND PASS: Processing {len(raw_items)} raw items ===")
        
        for line, item_data in raw_items.items():
            item_price = item_data['price']
            item_description = item_data['description']
            item_number = item_data['item_number'] # This is the first field from regex

            print(f"Processing: {item_number} - '{item_description}' - ${item_price:.2f}")

            # Check if this is a discount line based on description or price
            is_discount_line = False
            referenced_item_for_discount = None
            discount_value = 0

            if item_description.startswith('/'): # Standard discount: /<item_num>
                match = re.search(r'/(\d{6,8})', item_description)
                if match:
                    referenced_item_for_discount = match.group(1)
                    discount_value = abs(item_price)
                    is_discount_line = True
                    print(f"  → Discount found (slash type): ${discount_value:.2f} for item {referenced_item_for_discount}")
            
            elif item_price < 0: # Price itself is negative
                discount_value = abs(item_price)
                is_discount_line = True
                # Try to find referenced item in description if it's a digit string (item code)
                if item_description.isdigit() and 6 <= len(item_description) <= 8:
                    referenced_item_for_discount = item_description
                    print(f"  → Discount found (negative price, desc is item code): ${discount_value:.2f} for item {referenced_item_for_discount}")
                else:
                    print(f"  → Discount found (negative price, general): ${discount_value:.2f}. Trying to use item_number as reference.")
                    if item_number.isdigit() and 6 <= len(item_number) <= 8:
                        referenced_item_for_discount = item_number
                        print(f"  → Using item_number {item_number} as reference")

            if is_discount_line and referenced_item_for_discount:
                discount_items_raw.append({
                    'referenced_item': referenced_item_for_discount,
                    'discount': discount_value
                })
                print(f"  → Added to discount list: ${discount_value:.2f} for item {referenced_item_for_discount}")
            elif is_discount_line and not referenced_item_for_discount:
                # This is a discount line but we couldn't directly extract a referenced item number
                if item_number.isdigit() and 6 <= len(item_number) <= 8:
                     discount_items_raw.append({
                        'referenced_item': item_number, # Use the discount's own code as a candidate for fuzzy matching
                        'discount': discount_value,
                        'is_fuzzy_candidate': True 
                    })
                     print(f"  → Added to discount list (fuzzy candidate): ${discount_value:.2f} using item_number {item_number}")
            else: # Regular item (price is positive, or not identified as discount structure)
                if item_number not in regular_items:
                    regular_items[item_number] = {
                        'item_number': item_number,
                        'description': item_description,
                        'original_price': item_price, # This is the price from receipt
                        'discount': 0
                    }
                    print(f"  → Added as regular item: {item_number} - {item_description} - ${item_price:.2f}")
                else:
                    print(f"  → Duplicate regular item skipped: {item_number}")

        print(f"=== SUMMARY: {len(regular_items)} regular items, {len(discount_items_raw)} discount items ===")
        print("Regular items:", list(regular_items.keys()))
        print("Discount items:", [f"{d['referenced_item']}(${d['discount']:.2f})" for d in discount_items_raw])
        
        # Third pass: apply discounts to regular items with fuzzy matching for OCR errors
        discount_totals = {}
        
        print(f"=== THIRD PASS: Applying {len(discount_items_raw)} discounts to {len(regular_items)} regular items ===")
        
        for discount_item in discount_items_raw:
            referenced_item_number = discount_item['referenced_item']
            discount_amount = discount_item['discount']
            
            print(f"Trying to apply ${discount_amount:.2f} discount for item {referenced_item_number}")
            
            # First try exact match
            if referenced_item_number in regular_items:
                if referenced_item_number not in discount_totals:
                    discount_totals[referenced_item_number] = 0
                discount_totals[referenced_item_number] += discount_amount
                print(f"  → Applied ${discount_amount:.2f} discount to item {referenced_item_number} (exact match)")
                continue
            
            # If no exact match, try fuzzy matching for OCR errors
            print(f"  → No exact match found, trying fuzzy matching...")
            best_match = None
            min_diff = float('inf')
            
            for existing_item in regular_items.keys():
                if len(existing_item) == len(referenced_item_number):
                    # Check if they're similar (count character differences)
                    diff_count = sum(1 for i, (a, b) in enumerate(zip(existing_item, referenced_item_number)) if a != b)
                    if diff_count <= 2 and diff_count < min_diff:  # Allow 1-2 character differences
                        min_diff = diff_count
                        best_match = existing_item
                        print(f"    → Potential match: {existing_item} (diff: {diff_count})")
            
            if best_match:
                if best_match not in discount_totals:
                    discount_totals[best_match] = 0
                discount_totals[best_match] += discount_amount
                print(f"  → Applied ${discount_amount:.2f} discount to item {best_match} (fuzzy matched from {referenced_item_number}, {min_diff} differences)")
            else:
                print(f"  → Warning: Could not find item to apply discount of ${discount_amount:.2f} for reference {referenced_item_number}")
        
        print(f"=== DISCOUNT TOTALS: {discount_totals} ===")
        
        # Apply discount totals to regular items
        for item_number, total_discount in discount_totals.items():
            if item_number in regular_items:
                regular_items[item_number]['discount'] = total_discount
                print(f"Applied total discount of ${total_discount:.2f} to item {item_number}")
        
        # Calculate final prices and create items list
        print(f"=== FINAL ITEMS LIST ===")
        for item_number, item_data in regular_items.items():
            final_price = item_data['original_price'] - item_data['discount']
            
            items.append({
                'item_number': item_number,
                'description': item_data['description'],
                'price': final_price,
                'original_price': item_data['original_price'],
                'discount': item_data['discount']
            })
            
            if item_data['discount'] > 0:
                print(f"Final item: {item_number} - {item_data['description']} - Original: ${item_data['original_price']:.2f}, Discount: ${item_data['discount']:.2f}, Final: ${final_price:.2f}")
            else:
                print(f"Final item: {item_number} - {item_data['description']} - ${final_price:.2f}")
        
        # If no items found with strict patterns, try a looser approach
        if not items:
            print("No items found with standard patterns, trying looser matching...")
            items = self.extract_items_loose(text)
        
        print(f"Total items found: {len(items)}")
        return items
    
    def extract_items_loose(self, text):
        """Looser item extraction for difficult-to-parse receipts"""
        items = []
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Look for any line with a price pattern at the end
            price_match = re.search(r'(\d+\.\d{2})[-]?\s*$', line)
            if price_match:
                price_str = price_match.group(1)
                
                # Look for item number at the beginning
                item_match = re.match(r'^(\d{6,8})', line)
                if item_match:
                    item_number = item_match.group(1)
                    
                    # Extract description (everything between item number and price)
                    description_part = line[len(item_number):line.rfind(price_str)].strip()
                    
                    # Clean up description
                    description = re.sub(r'[*\s]+', ' ', description_part).strip()
                    
                    if len(description) > 2:
                        try:
                            price = float(price_str)
                            if '-' in line:
                                price = -price
                                
                            items.append({
                                'item_number': item_number,
                                'description': description,
                                'price': price
                            })
                            print(f"Loose match found: {item_number} - {description} - ${price}")
                        except ValueError:
                            continue
        
        return items
    
    def extract_receipt_date(self, text):
        """Try to extract receipt date from text"""
        # Look for date patterns
        date_patterns = [
            r'\d{1,2}/\d{1,2}/\d{4}',
            r'\d{4}-\d{2}-\d{2}',
            r'\d{2}/\d{2}/\d{4}'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    return parser.parse(match.group(0))
                except:
                    continue
        
        return None

# Initialize the processor
processor = ReceiptProcessor()

def allowed_file(filename):
    """Check if uploaded file is allowed"""
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
                text = processor.extract_text_from_image(filepath)
                
                if len(text.strip()) < 10:
                    flash('Unable to extract text from the image. Please ensure the image is clear and try again.')
                    os.remove(filepath)
                    return redirect(request.url)
                
                receipt_data = processor.parse_receipt_text(text)
                
                # Check if we found any items
                if not receipt_data['items']:
                    flash('No items found in the receipt. The image may be unclear or not a valid Costco receipt. Please try with a clearer image or different angle.')
                    os.remove(filepath)
                    return redirect(request.url)
                
                # Save to database
                receipt = Receipt(
                    store_address=receipt_data['store_info']['address'] or 'Unknown Store',
                    store_number=receipt_data['store_info']['store_number'] or 'Unknown',
                    receipt_date=receipt_data['receipt_date']
                )
                db.session.add(receipt)
                db.session.flush()  # Get the receipt ID
                
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
            # Extract text
            text = processor.extract_text_from_image(filepath)
            receipt_data = processor.parse_receipt_text(text)
            
            # Clean up
            os.remove(filepath)
            
            return jsonify({
                'extracted_text': text[:1000],  # First 1000 characters
                'text_length': len(text),
                'items_found': len(receipt_data['items']),
                'items': receipt_data['items'][:5],  # First 5 items
                'store_info': receipt_data['store_info']
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