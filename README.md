# Weather-Aware Delivery Delay Checker

Automatically checks weather conditions for delivery locations and flags orders that may be delayed due to adverse weather.

---

## Features

- ✅ Concurrent weather fetching (all cities processed simultaneously)
- ✅ Intelligent delay detection (Rain, Snow, Extreme weather)
- ✅ AI-generated customer apology messages
- ✅ Robust error handling (invalid cities don't crash the script)
- ✅ Secure API key management
- ✅ Mock mode for testing without API keys

---

## Quick Start

### Installation

```bash
pip install -r requirements.txt
```

### Run with Mock Data (No API Key Needed)

```bash
python main.py --mock
```

### Run with Real Weather API

1. Copy `.env.example` to `.env`
2. Add your OpenWeatherMap API key to `.env`
3. Run:

```bash
python main.py
```

---

## Configuration

Create a `.env` file with your API key:

```
OPENWEATHER_API_KEY=your_actual_key_here
```

Get a free API key at: https://openweathermap.org/api

---

## How It Works

1. Reads orders from `orders.json`
2. Fetches weather for all cities concurrently using `asyncio.gather()`
3. Marks orders as "Delayed" if weather is Rain, Snow, or Extreme
4. Generates personalized apology messages
5. Handles errors gracefully (invalid cities are logged, not fatal)
6. Saves results to `orders_updated.json`

---

## Output

The script creates `orders_updated.json` showing which orders are delayed:

### Good Weather (No Delay):

```json
{
  "order_id": "1002",
  "status": "Pending",
  "weather": "Clouds (31.0°C)"
}
```

### Bad Weather (Delayed):

```json
{
  "order_id": "1001",
  "status": "Delayed",
  "weather": "Rain (heavy rain, 11.2°C)",
  "apology_message": "Hi Alice, your order to New York is delayed..."
}
```

### Invalid City (Error Handled):

```json
{
  "order_id": "1004",
  "status": "Pending",
  "weather_check": "failed: city not found"
}
```

See `OUTPUT_EXPLANATION.md` for detailed field descriptions and examples.

---

## Requirements Met

✅ Concurrent API calls (asyncio.gather)  
✅ Weather-based delay logic (Rain/Snow/Extreme)  
✅ AI-powered apology messages  
✅ Error handling (InvalidCity123 doesn't crash)  
✅ Secure API keys (.env file)

---

## Project Structure

```
.
├── main.py                 # Main script
├── orders.json            # Input data
├── orders_updated.json    # Generated output
├── requirements.txt       # Dependencies
├── .env.example          # Configuration template
├── .gitignore            # Git ignore rules
├── AI_LOG.md             # Development process
└── README.md             # This file
```

---

