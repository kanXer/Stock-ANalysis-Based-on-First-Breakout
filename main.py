import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import ttk, scrolledtext
import matplotlib.pyplot as plt

def get_historical_data(ticker, start_date, end_date, interval):
    try:
        stock_data = yf.download(ticker, start=start_date, end=end_date, interval=f'{interval}m')
        print(f"Data fetched: {stock_data.head()}")
        return stock_data
    except Exception as e:
        print(f"Error fetching data: {e}")
        return pd.DataFrame()

def analyze_breakout(stock_data):
    if (stock_data.empty or len(stock_data) == 0):
        print("No data fetched.")
        return pd.DataFrame(), [], 0, 0, 0

    print("Analyzing data...")
    signals = pd.DataFrame(index=stock_data.index)
    signals['signal'] = 0.0
    signals['stop_loss'] = None
    signals['target'] = None

    breakout_details = []
    target_hit_count = 0
    stop_loss_hit_count = 0
    no_hit_count = 0

    for date in stock_data.index.normalize().unique():
        daily_data = stock_data[stock_data.index.normalize() == date]
        morning_candle = daily_data.between_time('09:15', '09:20')

        if not morning_candle.empty:
            high_price = morning_candle['High'].max()
            low_price = morning_candle['Low'].min()

            upside_detected = False
            downside_detected = False

            for idx, row in daily_data.iterrows():
                if not upside_detected and row['High'] > high_price:
                    stop_loss = morning_candle['Low'].min()
                    target = morning_candle['Low'].min() + 2 * (morning_candle['High'].max() - morning_candle['Low'].min())
                    signals.loc[idx, 'signal'] = 1
                    signals.loc[idx, 'stop_loss'] = stop_loss
                    signals.loc[idx, 'target'] = target
                    breakout_details.append((date, idx, 'upside', row['Close'], target, stop_loss, 'Target' if (daily_data['Close'] >= target).any() else 'Stoploss'))

                    if (daily_data['Close'] >= target).any():
                        target_hit_count += 1
                    elif (daily_data['Close'] <= stop_loss).any():
                        stop_loss_hit_count += 1
                    else:
                        no_hit_count += 1

                    upside_detected = True
                    break

                if not downside_detected and row['Low'] < low_price:
                    stop_loss = morning_candle['High'].max()
                    target = morning_candle['High'].max() - 2 * (morning_candle['High'].max() - morning_candle['Low'].min())
                    signals.loc[idx, 'signal'] = -1
                    signals.loc[idx, 'stop_loss'] = stop_loss
                    signals.loc[idx, 'target'] = target
                    breakout_details.append((date, idx, 'downside', row['Close'], target, stop_loss, 'Target' if (daily_data['Close'] <= target).any() else 'Stoploss'))

                    if (daily_data['Close'] <= target).any():
                        target_hit_count += 1
                    elif (daily_data['Close'] >= stop_loss).any():
                        stop_loss_hit_count += 1
                    else:
                        no_hit_count += 1

                    downside_detected = True
                    break

    return signals, breakout_details, target_hit_count, stop_loss_hit_count, no_hit_count

def run_analysis():
    ticker = ticker_entry.get()
    interval = interval_combobox.get()
    
    # Validate interval input
    try:
        interval = int(interval)
    except ValueError:
        result_text.set("Please select a valid interval.")
        return
    
    # Set date range to within the last 30 days
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')

    stock_data = get_historical_data(ticker, start_date, end_date, interval)
    
    signals, breakout_details, target_hit_count, stop_loss_hit_count, no_hit_count = analyze_breakout(stock_data)
    
    if len(breakout_details) == 0:
        result_text.set("No valid breakouts found.")
        detailed_text.config(state=tk.NORMAL)
        detailed_text.delete('1.0', tk.END)
        detailed_text.config(state=tk.DISABLED)
        plt.close()
        return
    
    # Calculate total points achieved through targets and stop-losses
    total_points_target = target_hit_count * 2  # Assuming each target hit adds 2 points
    total_points_stop_loss = stop_loss_hit_count * -1  # Assuming each stop-loss hit deducts 1 point
    total_points = total_points_target + total_points_stop_loss
    total_trades = len(breakout_details)
    
    # Update result text in GUI with points achieved and total trades
    result_summary = f"Total Points from Targets: {total_points_target}, Total Points from Stop-Losses: {total_points_stop_loss}, Total Trades: {total_trades}"
    result_text.set(result_summary)
    
    # Prepare detailed breakout results for display
    detailed_results = "\n".join([f"Date: {date.strftime('%Y-%m-%d')}, "
                                  f"Time: {idx.strftime('%H:%M')}, "
                                  f"Direction: {direction}, "
                                  f"Trigger Price: {trigger_price:.2f}, "
                                  f"Target: {target:.2f}, "
                                  f"Stop-Loss: {stop_loss:.2f}, "
                                  f"Trade Exit: {triggered_by}"
                                  for date, idx, direction, trigger_price, target, stop_loss, triggered_by in breakout_details])
    
    # Display full detailed breakout results in scrolled text widget
    detailed_text.config(state=tk.NORMAL)
    detailed_text.delete('1.0', tk.END)
    detailed_text.insert(tk.END, detailed_results)
    detailed_text.config(state=tk.DISABLED)
    
    # Update trade count label
    trade_count_text.set(f"Trades Target Hit: {target_hit_count}, Trades Stop-Loss Hit: {stop_loss_hit_count}, not SL hit or not Target: {no_hit_count}")
    
    # Plotting directly without separate function
    plt.figure(figsize=(14, 7))
    plt.plot(stock_data.index, stock_data['Close'], label='Close Price')
    
    # Plotting breakout points
    plotted_dates = set()  # To keep track of dates already plotted
    for date, idx, direction, trigger_price, target, stop_loss, hit_status in breakout_details:
        if date not in plotted_dates:
            if direction == 'upside':
                plt.scatter(idx, trigger_price, color='green', label='Target Hit', marker='o')
                plt.text(idx, trigger_price, f"Target Hit\nPrice: {trigger_price:.2f}", ha='center', va='bottom', fontsize=9, color='black')
            elif direction == 'downside':
                plt.scatter(idx, trigger_price, color='red', label='Target Hit', marker='o')
                plt.text(idx, trigger_price, f"Target Hit\nPrice: {trigger_price:.2f}", ha='center', va='top', fontsize=9, color='black')
            
            plotted_dates.add(date)

    plt.title(f'Stock Breakout Analysis for {ticker}')
    plt.xlabel('Date')
    plt.ylabel('Price')
    plt.legend()
    plt.grid()
    plt.tight_layout()
    plt.show()

def on_enter(event):
    analyze_button.configure(style="Hover.TButton")

def on_leave(event):
    analyze_button.configure(style="TButton")

# Set up GUI
root = tk.Tk()
root.title("Stock Analysis")

# Set up style
style = ttk.Style()
style.configure("TLabel", font=("Helvetica", 12), background="#f0f0f0")
style.configure("TButton", font=("Helvetica", 12), background="#4CAF50", foreground="#ffffff")
style.map("TButton",
          background=[('active', '#66BB6A')])
style.configure("TEntry", font=("Helvetica", 12))
style.configure("TFrame", background="#f0f0f0")

# Create a new style for hover effect
style.map("TButton",
          foreground=[('active', '#000000')],
          background=[('active', '#8BC34A')])

frame = ttk.Frame(root, padding="10")
frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

# Ticker input
ttk.Label(frame, text="Ticker:", style="TLabel").grid(row=0, column=0, sticky=tk.E, padx=5, pady=5)
ticker_entry = ttk.Entry(frame)
ticker_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)

# Interval input as combobox
ttk.Label(frame, text="Interval (minutes):", style="TLabel").grid(row=1, column=0, sticky=tk.E, padx=5, pady=5)
interval_combobox = ttk.Combobox(frame, values=[1, 2, 5, 15, 30, 60, 90], state='readonly')
interval_combobox.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
interval_combobox.current(2)  # Default to 5 minutes

# Result label
result_text = tk.StringVar()
result_label = ttk.Label(frame, textvariable=result_text, style="TLabel")
result_label.grid(row=2, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)

# Detailed results scrolled text
detailed_text = scrolledtext.ScrolledText(frame, height=15, wrap=tk.WORD)
detailed_text.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=5)
detailed_text.configure(state='disabled')

# Trade count label
trade_count_text = tk.StringVar()
trade_count_label = ttk.Label(frame, textvariable=trade_count_text, style="TLabel")
trade_count_label.grid(row=4, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)

# Analyze button
analyze_button = ttk.Button(frame, text="Analyze", command=run_analysis, style="TButton")
analyze_button.grid(row=5, column=0, columnspan=2, pady=10)
analyze_button.bind("<Enter>", on_enter)
analyze_button.bind("<Leave>", on_leave)

root.mainloop()