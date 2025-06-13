from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from PIL import Image


import re
import os
import json
from datetime import datetime, timedelta
from dateutil import parser
import tempfile
import base64
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables from .env file
load_dotenv()

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
        # Check if OpenAI API key is available
        if not os.environ.get('OPENAI_API_KEY'):
            print("WARNING: OPENAI_API_KEY not found. Receipt processing will not work.")
            print("Please set your OpenAI API key in .env file")
            self.client = None
            self.agent_available = False
            return
        
        try:
            self.client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
            self.agent_available = True
            print("OpenAI client initialized successfully!")
        except Exception as e:
            print(f"Error initializing OpenAI client: {e}")
            self.client = None
            self.agent_available = False
    
    def encode_image(self, image_path):
        """Encode image to base64"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    def extract_text_from_image(self, image_path):
        """Extract structured data from receipt image using OpenAI Vision"""
        if not self.agent_available or not self.client:
            raise Exception("OpenAI client is not available. Please check your API key.")
        
        try:
            print(f"Processing receipt with OpenAI Vision: {image_path}")
            
            # Encode the image
            base64_image = self.encode_image(image_path)
            
            # Create the prompt
            prompt = """
            You are a meticulous data extraction agent specializing in Costco receipts. Your task is to analyze the receipt image and convert it into a structured JSON object. You must follow the processing logic below with absolute precision.

            **CRITICAL: Costco receipts have a specific discount pattern that you MUST identify:**

            1. **Primary Item Lines**: Lines with item numbers (6-8 digits), descriptions, and prices
            2. **Discount Lines**: Separate lines with negative amounts and forward slash patterns like "/1234567"

            **Processing Instructions:**

            **Step 1: Extract Store Information**
            - Store number and name (e.g., "HAYWARD #1061")
            - Complete address

            **Step 2: Extract Receipt Date**
            - Find and extract the transaction date

            **Step 3: Two-Pass Item Processing (CRITICAL FOR DISCOUNTS)**

            **Pass 1 - Identify Primary Items:**
            - Find lines with: [ITEM_NUMBER] [DESCRIPTION] [PRICE]
            - Example: "1865480 AM PLISSETOP 14.99"
            - Record the original price from this line
            - Initially set discount to 0

            **Pass 2 - Apply Discounts:**
            - Look for discount lines with patterns like: "[REF_NUMBER] /[ITEM_NUMBER] [AMOUNT]-"
            - Example: "354966 /1865480 3.00-"
            - The number after "/" is the target item number
            - The amount with "-" is the discount amount
            - **IMPORTANT**: Discount lines may appear anywhere on the receipt - scan the entire receipt text
            - Apply this discount to the matching item from Pass 1

            **Example Processing:**
            ```
            Receipt lines:
            1865480 AM PLISSETOP 14.99 Y
            354966 /1865480 3.00-

            Result:
            Item 1865480: original_price=14.99, discount=3.00, price=11.99
            ```

            **JSON Output Format:**
            Return ONLY a valid JSON object:
            ```json
            {
                "store_info": {
                    "store_number": "STRING",
                    "address": "STRING"
                },
                "receipt_date": "YYYY-MM-DD",
                "items": [
                    {
                        "item_number": "STRING",
                        "description": "STRING",
                        "original_price": FLOAT,
                        "discount": FLOAT,
                        "price": FLOAT
                    }
                ]
            }
            ```

            **Critical Rules:**
            - Discount lines do NOT create new items - they only modify existing items
            - If no discount line exists for an item, set discount to 0
            - Use 0 instead of null for numeric values
            - **SCAN ENTIRE RECEIPT**: Discount lines can appear anywhere - before, after, or mixed with item lines
            - **COMMON PATTERNS**: Look for lines containing "/" followed by numbers, or lines with negative amounts
            - Focus on accuracy - better to miss a discount than create incorrect data
            """
            
            # Make the API call
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=2000,
                temperature=0.1
            )
            
            agent_response = response.choices[0].message.content
            print("OpenAI Response:")
            print(agent_response)
            print("="*50)
            
            return agent_response
            
        except Exception as e:
            print(f"OpenAI API Error: {e}")
            raise Exception(f"Failed to process receipt with OpenAI: {e}")
    
    def parse_receipt_text(self, agent_response):
        """Parse OpenAI response to get structured data"""
        try:
            # Try to extract JSON from the response
            import re
            
            # Look for JSON block in the response
            json_match = re.search(r'\{.*\}', agent_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                # Try to parse the entire response as JSON
                json_str = agent_response.strip()
            
            # Parse the JSON
            data = json.loads(json_str)
            
            # Ensure the data has the expected structure
            receipt_data = {
                'store_info': data.get('store_info', {'store_number': '', 'address': ''}),
                'items': [],
                'receipt_date': None
            }
            
            # Parse receipt date
            if data.get('receipt_date'):
                try:
                    receipt_data['receipt_date'] = parser.parse(data['receipt_date'])
                except:
                    receipt_data['receipt_date'] = None
            
            # Process items
            for item in data.get('items', []):
                # Extract all price fields with proper fallbacks and null handling
                price = item.get('price', 0)
                original_price = item.get('original_price', price)
                discount = item.get('discount', 0)
                
                # Handle null values by converting to 0
                if price is None:
                    price = 0
                if original_price is None:
                    original_price = 0
                if discount is None:
                    discount = 0
                
                # Convert to float
                price = float(price)
                original_price = float(original_price)
                discount = float(discount)
                
                # Validate price consistency
                if discount > 0 and original_price == price:
                    # If discount exists but original_price equals price, calculate original_price
                    original_price = price + discount
                elif discount > 0 and abs((original_price - discount) - price) > 0.01:
                    # If price calculation doesn't match, recalculate price
                    price = original_price - discount
                
                processed_item = {
                    'item_number': str(item.get('item_number', '')),
                    'description': item.get('description', ''),
                    'price': price,  # Final price after discount
                    'original_price': original_price,  # Original price before discount
                    'discount': discount  # Discount amount
                }
                receipt_data['items'].append(processed_item)
                
            print(f"Parsed {len(receipt_data['items'])} items from OpenAI response")
            for item in receipt_data['items']:
                if item['discount'] > 0:
                    print(f"Item: {item['item_number']} - {item['description']} - ${item['price']:.2f} (was ${item['original_price']:.2f}, saved ${item['discount']:.2f})")
                else:
                    print(f"Item: {item['item_number']} - {item['description']} - ${item['price']:.2f}")
            
            return receipt_data
            
        except Exception as e:
            print(f"Error parsing OpenAI response: {e}")
            print(f"OpenAI response was: {agent_response}")
            return {
                'store_info': {'store_number': '', 'address': ''},
                'items': [],
                'receipt_date': None
            }

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
                        'original_price': item_data['original_price'],  # Now guaranteed to exist
                        'discount': item_data['discount'],  # Now guaranteed to exist
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
                        original_price=item_data['original_price'],  # Now guaranteed to exist
                        discount=item_data['discount']  # Now guaranteed to exist
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