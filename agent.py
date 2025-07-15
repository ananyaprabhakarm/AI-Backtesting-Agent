from data_engine import fetch_historicaldata

def get_user_rule():
    rule = input("Enter: ").strip().lower()
    return rule

def translate_rule_to_python(rule):
    rule = rule.lower()

    replacements = {
        "buy when": "",
        "enter long when": "",
        "purchase when": "",
        "close price": "row['close']",
        "open price": "row['open']",
        "high price": "row['high']",
        "low price": "row['low']",
        "volume": "row['volume']",
        "greater than": ">",
        "less than": "<",
        "equals to": "==",
        "equal to": "==",
        "above": ">",
        "below": "<",
        "crosses above": ">",
        "crosses below": "<",
        "and": "and",
        "or": "or"
    }


    for key, value in replacements.items():
        rule = rule.replace(key, value)


    rule = ' '.join(rule.split())


    if ">" in rule or "<" in rule or "==" in rule:
        return rule
    

def generate_strategy_script(condition_python):
    script = f'''# generated_strategy.py
from data_engine import fetch_historicaldata

def backtest_strategy():
    df = fetch_historicaldata()
    position = None
    signals = []

    for i in range(len(df)):
        row = df.iloc[i]

        if {condition_python}:
            if position != 'long':
                print(f"BUY SIGNAL at {{row['date']}} | Price: {{row['close']}}")
                position = 'long'
                signals.append(('buy', row['date'], row['close']))
        else:
            if position == 'long':
                print(f"SELL SIGNAL at {{row['date']}} | Price: {{row['close']}}")
                position = None
                signals.append(('sell', row['date'], row['close']))

    print("\\n=== Backtest Summary ===")
    print(f"Total signals generated: {{len(signals)}}")

if __name__ == "__main__":
    backtest_strategy()
'''
    with open("generated_strategy.py", "w") as f:
        f.write(script)
    print("✅ Strategy saved in generated_strategy.py")

def main():
    try:
        rule = get_user_rule()
        python_condition = translate_rule_to_python(rule)
        generate_strategy_script(python_condition)
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
