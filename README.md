# Costco Receipt Tracker

A web application that automatically extracts item information from Costco receipts using **OpenAI Vision API** and tracks prices across different locations to help you find the best deals and price match opportunities.

## Features

- 🤖 **AI-Powered Processing**: Uses OpenAI Vision API (GPT-4o-mini) for intelligent receipt analysis
- 📱 **Easy Upload**: Simple web interface for uploading receipt images
- 💰 **Price Tracking**: Automatically compares prices and identifies lowest prices
- 🏪 **Store Tracking**: Tracks which stores offer the best prices for each item
- 📊 **Discount Detection**: Identifies and tracks discount amounts and savings
- 🔍 **Search History**: View price history for specific items across stores

## How It Works

1. **Upload Receipt**: Take a photo or scan your Costco receipt and upload it through the web interface
2. **AI Analysis**: OpenAI Vision API analyzes the image and extracts structured data
3. **Price Comparison**: System compares current prices with historical data from the last 30 days
4. **Results Display**: Shows items, prices, discounts, and alerts you to better deals found at other locations

## Technology Stack

- **Backend**: Python Flask with SQLAlchemy
- **AI Processing**: OpenAI Vision API (GPT-4o-mini)
- **Database**: SQLite for development (PostgreSQL ready for production)
- **Frontend**: Bootstrap 5 with responsive design
- **Image Processing**: Pillow for basic image handling
- **Deployment**: Docker and Heroku ready

## Installation

### Prerequisites

- Python 3.9+
- OpenAI API key

### Local Development Setup

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd costco-receipt-tracker
   ```

2. **Create virtual environment**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   Create a `.env` file in the project root:

   ```
   OPENAI_API_KEY=your_openai_api_key
   ```

5. **Run the application**

   ```bash
   python run.py
   ```

6. **Access the application**
   Open your browser and navigate to `http://localhost:5002`

## OpenAI Vision API Architecture

The application uses OpenAI Vision API with the following components:

- **Image Processing**: Direct base64 encoding for API submission
- **Prompt Engineering**: Specialized prompts for Costco receipt structure and discount patterns
- **Two-Pass Processing**: Advanced algorithm to identify primary items and apply discounts correctly
- **Structured Output**: JSON-formatted extraction with validation

### Receipt Processing Flow

```
Receipt Image → Base64 Encoding → OpenAI Vision API → Structured JSON → Database Storage
```

## Database Schema

### Receipt Table

- Store address and number
- Upload date and receipt date
- Relationship to receipt items

### ReceiptItem Table

- Item number (Costco's internal SKU)
- Product description
- Original price (before discounts)
- Final price (after discounts)
- Discount amount
- Date recorded

## API Endpoints

- `GET /` - Home page
- `POST /upload` - Upload and process receipt
- `GET /history` - View receipt history
- `GET /api/item/<item_number>` - Get price history for specific item
- `POST /debug/ocr` - Debug endpoint for testing processing

## Production Deployment

### Environment Variables Required

```bash
OPENAI_API_KEY=your_openai_api_key
DATABASE_URL=your_database_url  # For production
DEBUG=False
```

### Docker Deployment

```bash
docker build -t costco-receipt-tracker .
docker run -p 5002:5002 --env-file .env costco-receipt-tracker
```

### Heroku Deployment

The application includes `Procfile`, `runtime.txt`, and `Dockerfile` for easy Heroku deployment.

## Processing Accuracy

The OpenAI Vision API implementation provides:

- **High accuracy** for text recognition across various receipt conditions
- **Intelligent discount detection** using pattern recognition
- **Robust error handling** for unclear or damaged receipts
- **Cost-effective processing** at approximately $0.01-0.05 per receipt

## Usage Tips

1. **Image Quality**: Ensure receipts are clearly visible and well-lit
2. **Full Receipt**: Include the entire receipt in the image for best results
3. **Flat Surface**: Lay receipt flat to minimize distortion
4. **Good Lighting**: Avoid shadows and glare

## Troubleshooting

### Common Issues

1. **API Key Error**: Ensure your OpenAI API key is correctly set in the `.env` file
2. **Poor Recognition**: Try retaking the photo with better lighting or less distortion
3. **No Items Found**: Verify the image contains a valid Costco receipt

### Debug Mode

Run with debug logging:

```bash
DEBUG=True python run.py
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Cost Considerations

- OpenAI Vision API costs approximately $0.01-0.05 per receipt
- Highly cost-effective compared to traditional OCR solutions
- No additional infrastructure requirements for vision processing

## Support

For issues or questions, please open an issue on the GitHub repository.
