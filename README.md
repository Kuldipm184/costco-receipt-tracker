# Costco Receipt Price Tracker

A web application that automatically extracts item information from Costco receipts using OCR technology and tracks prices across different locations to help you find the best deals and price match opportunities.

## Features

- 📸 **OCR Technology**: Upload receipt images and automatically extract item numbers, prices, and store information
- 💰 **Price Comparison**: Compare prices across different Costco locations within a 30-day window
- 🔔 **Price Match Alerts**: Get notified when better prices are available at other locations
- 🏪 **Store Tracking**: Track which stores offer the lowest prices for specific items
- 📱 **Responsive Design**: Beautiful, modern web interface that works on desktop and mobile
- 🔒 **Privacy Focused**: Images are processed and deleted immediately, only price data is stored

## How It Works

1. **Upload Receipt**: Take a photo of your Costco receipt or upload an existing image
2. **OCR Processing**: Advanced image processing extracts item numbers, descriptions, and prices
3. **Price Analysis**: The system compares your prices with existing data from other stores
4. **Get Results**: View price comparisons and receive alerts for better deals
5. **Price Matching**: Use the provided store information to request price matches

## Requirements

- Python 3.8+
- Tesseract OCR engine
- SQLite database (included)
- Modern web browser

## Installation

### Prerequisites

First, install Tesseract OCR on your system:

**macOS (using Homebrew):**

```bash
brew install tesseract
```

**Ubuntu/Debian:**

```bash
sudo apt-get update
sudo apt-get install tesseract-ocr
```

**Windows:**
Download and install from: https://github.com/UB-Mannheim/tesseract/wiki

### Application Setup

1. **Clone or Download** the application files to your desired directory

2. **Install Python Dependencies:**

```bash
pip install -r requirements.txt
```

3. **Run the Application:**

```bash
python app.py
```

4. **Access the Web Interface:**
   Open your browser and navigate to: `http://localhost:5000`

## Usage Guide

### Uploading a Receipt

1. Navigate to the **Upload Receipt** page
2. Drag and drop your receipt image or click to browse files
3. Supported formats: PNG, JPG, JPEG, GIF, BMP, TIFF (Max 16MB)
4. Click **Process Receipt** to analyze the image

### Understanding Results

After processing, you'll see:

- **Best Price Items** (Green): Items where your price is the lowest in the database
- **Price Match Opportunities** (Yellow): Items where better prices are available at other stores
- **Store Information**: Location details for price matching

### Price Matching Tips

- Costco offers price matching within 30 days of purchase
- Bring your receipt and proof of the lower price
- The lower price must be from another Costco location
- Visit the customer service desk at your local Costco

## Database Schema

The application uses SQLite with two main tables:

### Receipts Table

- Store address and number
- Upload and receipt dates
- Relationship to items

### Receipt Items Table

- Item number and description
- Price (including discounts)
- Date recorded
- Foreign key to receipt

## API Endpoints

- `GET /` - Home page
- `GET /upload` - Upload form
- `POST /upload` - Process receipt upload
- `GET /history` - View receipt history
- `GET /api/item/<item_number>` - Get price history for specific item

## Technical Details

### OCR Processing

The application uses:

- **OpenCV** for image preprocessing
- **Pytesseract** for text extraction
- **Regular expressions** for parsing receipt structure
- **Image enhancement** techniques for better OCR accuracy

### Price Comparison Logic

- Only compares prices within 30 days
- Handles both regular prices and discounts
- Updates database with new lowest prices
- Provides store location for price matching

## File Structure

```
costco-receipt-tracker/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── templates/            # HTML templates
│   ├── base.html         # Base template with styling
│   ├── index.html        # Home page
│   ├── upload.html       # Upload page
│   ├── results.html      # Results page
│   └── history.html      # History page
├── uploads/              # Temporary upload directory
└── costco_receipts.db    # SQLite database (created on first run)
```

## Troubleshooting

### OCR Issues

- Ensure receipt image is clear and well-lit
- Avoid shadows and glare
- Keep receipt as flat as possible
- Try different image formats if one doesn't work

### Installation Issues

- Make sure Tesseract is properly installed and in your PATH
- Verify Python 3.8+ is being used
- Check that all dependencies are installed correctly

### Performance

- Large images may take longer to process
- Consider resizing very large images before upload
- The application works best with images under 5MB

## Security Considerations

- Uploaded images are automatically deleted after processing
- Only price and store data is stored in the database
- No personal information is extracted or stored
- Database contains no sensitive receipt data

## Contributing

This is a personal project, but suggestions for improvements are welcome:

1. Better OCR accuracy for different receipt formats
2. Support for other store chains
3. Mobile app development
4. Enhanced price tracking features

## License

This project is for personal use. Please respect Costco's terms of service when using price matching features.

## Disclaimer

This application is not affiliated with Costco Wholesale Corporation. Use price matching information according to your local Costco's policies and at your own discretion.
