# 📈 AI Strategy Agent

This project is an **AI-powered trading strategy agent** that takes in natural language rules like:


...and automatically generates a complete **Python backtest script** (`generated_strategy.py`) using historical stock data.

---

## 🧠 Features

- 🗣️ Accepts strategy in plain English
- 🧠 Parses and converts it into Python condition
- 📉 Fetches dummy historical data (for stock: `NIFTY`)
- 🧪 Applies your strategy logic
- 📝 Generates a runnable script to print buy signals

---

## 📁 Project Structure
```
.
├── agent.py # Main script to take strategy input & generate code
├── data_engine.py # Function to fetch/generate dummy historical stock data
├── generated_strategy.py # Auto-generated strategy file (after running agent)
├── requirements.txt # Python dependencies
└── README.md # You're here!
```


---

## 🔧 Installation

Make sure Python is installed, then install the required libraries:

---

## 📥 Getting Started

### Clone the Repository

```bash
git clone https://github.com/ananyaprabhakarm/AI-Backtesting-Agent.git
cd AI-Backtesting-Agent
```

```bash
pip install -r requirements.txt
```
## 🚀 How to Use
### Step 1: Run the agent
```
python agent.py
```
### Step 2: Enter your strategy rule (example):
```
Buy when close > open
```
### Step 3: Output
```
A new file generated_strategy.py will be created containing:

    Data loading

    Your strategy condition

    Buy signal printing
```
### Step 4: Run the generated strategy
```
python generated_strategy.py

✅ It will show the dates and prices where your condition was met.
```
## 📊 Example Output
```
Buy signals:
         date     open    close
0  2023-01-01  105.34   110.89
3  2023-01-04  120.45   125.10
```
