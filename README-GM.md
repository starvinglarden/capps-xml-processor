# CAPPS XML Converter - User Guide

## Quick Start

### First Time Setup

1. **Download the Application**
   - Download `CAPPS-Converter.exe` from the link provided
   - Save it to a dedicated folder (recommended: `C:\CAPPS-Converter\`)

2. **Run the Application**
   - Double-click `CAPPS-Converter.exe`

3. **Windows SmartScreen Warning** (First Run Only)
   - You may see a blue "Windows protected your PC" screen
   - Click "**More info**"
   - Click "**Run anyway**"
   - This only happens once

4. **First Time Configuration**
   - Enter your **License Number** (CA secondhand dealer license)
   - Enter **Employee Name**
   - Set **Minimum Cost** (default: $100)
   - Set **Days Lookback** (default: 5 days)
   - *(Optional)* Enter API key for better brand detection

   **These settings save automatically!** You only need to enter them once.

---

## Daily Usage

### Converting AIMsi Exports to CAPPS XML

1. **Export from AIMsi**:
   - Export your **PURCHASES** report as CSV
   - Export your **SERIALS** report as CSV (e.g., LUCASSERIALS.CSV)

2. **Open CAPPS Converter**:
   - Double-click `CAPPS-Converter.exe`

3. **Select Files**:
   - Click "Browse" next to "Purchases CSV" → select your purchases file
   - Click "Browse" next to "Serials CSV" → select your serials file

4. **Convert**:
   - Click "**Convert to XML**"
   - Watch the Conversion Log at the bottom for progress
   - When done, you'll see "Conversion successful!"

5. **Find Your XML**:
   - The file `capps_upload.xml` will be created in the same folder as the application
   - You can choose to inspect it or upload directly to CAPPS

---

## Understanding the Filters

The converter automatically filters transactions to only include:

- **Recent purchases**: From the last 5 days (configurable)
- **Minimum value**: Items >= $100 (configurable)
- **Valid serials**: Items with descriptions in the serials CSV
- **Customer purchases**: Excludes ISI-serialized inventory (configurable)

---

## Features

### Configuration Options

- **License Number**: Your CA secondhand dealer license (required)
- **Employee Name**: Name to appear in transaction records (required)
- **Minimum Cost**: Only report items worth this amount or more
- **Days Lookback**: How many days back to include purchases (default: 5)
- **Include ISI Serials**: Check this to include in-store inventory items
- **API Provider**: Groq or Gemini for automatic brand detection (free)
- **API Key**: Optional but improves brand extraction accuracy

### Conversion Log

The log at the bottom shows:
- Files being processed
- Number of transactions found
- Filters being applied
- How many items were included/excluded
- Any errors or warnings

All logs display in real-time as conversion happens.

---

## Troubleshooting

### "Please enter your license number"
- Fill in the License Number field at the top
- It will save automatically for next time

### "Purchases file not found"
- Make sure you've selected the correct CSV file
- Check that the file path doesn't have special characters

### "No transactions found" or "Filtered out all transactions"
- Check your Days Lookback setting (may need to increase)
- Verify your Minimum Cost isn't too high
- Make sure the purchases CSV has data in the correct date range
- Try unchecking "Include ISI Serials" filter

### Application won't start
- Make sure you clicked "Run anyway" on the SmartScreen warning
- Try running as administrator (right-click → Run as administrator)
- Contact your IT department if antivirus is blocking it

### Settings not saving
- Make sure you have write permissions to your user folder
- Settings are saved to: `C:\Users\[YourName]\.capps_converter_settings.json`

---

## CAPPS Upload (Optional)

If you have CAPPS API credentials:

1. Enter your **CAPPS Client ID** and **Client Secret**
2. After conversion, choose "Upload Now"
3. The app will upload directly to CAPPS
4. You'll see "Upload successful!" when complete

Otherwise, you can manually upload `capps_upload.xml` to the CAPPS website.

---

## Updates

When a new version is released:

1. Download the new `CAPPS-Converter.exe`
2. Replace the old one in your folder
3. Your settings and history are preserved

---

## Support

For issues or questions, contact your system administrator.

**Version**: 1.0.0
