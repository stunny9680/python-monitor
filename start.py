import psutil
from cpuinfo import get_cpu_info
import datetime
import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import time

def get_cpu_speed():
    info = get_cpu_info()
    hz_actual = info.get('hz_actual_friendly', 'Unknown')
    return hz_actual

def get_cpu_temp():
    temps = psutil.sensors_temperatures()
    for key in ('coretemp', 'cpu-thermal', 'k10temp', 'acpitz'):
        if key in temps:
            entries = temps[key]
            if entries:
                return entries[0].current
    return 'Unavailable'

def log_status(log_line):
    with open('cpu_log.txt', 'a') as f:
        f.write(log_line + '\n')

def update_widget():
    cpu_speed = get_cpu_speed()
    cpu_temp = get_cpu_temp()
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # Get per-core CPU usage
    per_core = psutil.cpu_percent(percpu=True)
    per_core_str = ', '.join([f"Core {i}: {usage}%" for i, usage in enumerate(per_core)])
    # Get RAM usage
    ram = psutil.virtual_memory()
    ram_str = f"RAM: {ram.percent}% ({ram.used // (1024**2)}MB/{ram.total // (1024**2)}MB)"
    log_line = f"[{now}] CPU Speed: {cpu_speed}, CPU Temp: {cpu_temp}°C\n{per_core_str}\n{ram_str}"
    label_var.set(log_line)
    threading.Thread(target=log_status, args=(log_line,), daemon=True).start()
    root.after(5000, update_widget)  # update every 5 seconds


"""
CPU Monitor & Process Manager
--------------------------------
This app provides a real-time widget for monitoring CPU speed, temperature, per-core usage, and RAM usage. It also features a process manager tab where you can:
 - Search running processes by name
 - View CPU%, memory%, and memory usage in KB
 - See the current CPU clock speed
 - Kill processes by PID

The main window stays on top and logs all status updates to cpu_log.txt.
"""
# --- GUI with Tabs ---
root = tk.Tk()
root.title("CPU Monitor")
root.attributes('-topmost', True)
root.resizable(False, False)
root.configure(bg='#23272e')

tab_control = ttk.Notebook(root)

# --- Main Monitor Tab ---
main_tab = tk.Frame(tab_control, bg='#23272e')
tab_control.add(main_tab, text='Monitor')

label_var = tk.StringVar()
label = tk.Label(
    main_tab,
    textvariable=label_var,
    font=("Consolas", 13, "bold"),
    padx=24,
    pady=18,
    bg='#23272e',
    fg='#00ff99',
    justify='left',
    anchor='w',
    relief='groove',
    bd=3,
    width=48,
    height=7
)
label.pack(padx=10, pady=10)


# --- Processes Tab ---
proc_tab = tk.Frame(tab_control, bg='#23272e')
tab_control.add(proc_tab, text='Processes')

proc_text = scrolledtext.ScrolledText(proc_tab, font=("Consolas", 11), bg='#181a20', fg='#00ff99', width=80, height=18)
proc_text.pack(padx=10, pady=(10,0), fill='both', expand=True)


# --- Search and Kill Controls ---
search_kill_frame = tk.Frame(proc_tab, bg='#23272e')
search_kill_frame.pack(padx=10, pady=10, fill='x')

# Search bar
search_label = tk.Label(search_kill_frame, text="Search:", font=("Consolas", 11), bg='#23272e', fg='#00ff99')
search_label.pack(side='left', padx=(0,5))

search_var = tk.StringVar()
search_entry = tk.Entry(search_kill_frame, textvariable=search_var, font=("Consolas", 11), width=18, bg='#181a20', fg='#00ff99', insertbackground='#00ff99')
search_entry.pack(side='left', padx=(0,15))

def on_search_key(event=None):
    update_process_list()

search_entry.bind('<KeyRelease>', on_search_key)

# PID kill controls
pid_label = tk.Label(search_kill_frame, text="PID to kill:", font=("Consolas", 11), bg='#23272e', fg='#00ff99')
pid_label.pack(side='left', padx=(10,5))

pid_entry = tk.Entry(search_kill_frame, font=("Consolas", 11), width=10, bg='#181a20', fg='#00ff99', insertbackground='#00ff99')
pid_entry.pack(side='left', padx=(0,10))

kill_msg_var = tk.StringVar()
kill_msg_label = tk.Label(search_kill_frame, textvariable=kill_msg_var, font=("Consolas", 11), bg='#23272e', fg='#ff5555')
kill_msg_label.pack(side='left', padx=(10,0))

def kill_process():
    pid = pid_entry.get().strip()
    if not pid.isdigit():
        kill_msg_var.set("Enter valid PID")
        return
    try:
        p = psutil.Process(int(pid))
        p.terminate()
        gone, alive = psutil.wait_procs([p], timeout=2)
        if alive:
            p.kill()
        kill_msg_var.set(f"Process {pid} killed")
    except psutil.NoSuchProcess:
        kill_msg_var.set("No such process")
    except psutil.AccessDenied:
        kill_msg_var.set("Access denied")
    except Exception as e:
        kill_msg_var.set(f"Error: {e}")

kill_btn = tk.Button(search_kill_frame, text="Kill", font=("Consolas", 11, "bold"), bg='#ff5555', fg='white', command=kill_process, activebackground='#ff8888', activeforeground='black')
kill_btn.pack(side='left', padx=(10,0))

tab_control.pack(expand=1, fill='both')

def set_rounded_corners(window):
    try:
        window.wm_attributes('-type', 'dialog')
    except Exception:
        pass

set_rounded_corners(root)

def update_process_list():
    search_term = search_var.get().strip().lower()
    num_cpus = psutil.cpu_count(logical=True) or 1
    # Get the current CPU clock speed (MHz) for the header only
    try:
        freq = psutil.cpu_freq()
        cpu_clock = f"CPU Clock: {freq.current:.0f} MHz" if freq else "CPU Clock: N/A"
    except Exception:
        cpu_clock = "CPU Clock: N/A"
    lines = [cpu_clock, f"{'PID':>6}  {'Name':<25}  {'CPU%':>6}  {'Mem%':>6}  {'Mem(KB)':>10}"]
    for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'memory_info']):
        try:
            name = p.info['name'] or ''
            if search_term and search_term not in name.lower():
                continue
            mem_kb = p.info['memory_info'].rss // 1024 if p.info.get('memory_info') else 0
            # Normalize CPU% to total system (100% = all cores)
            cpu_percent = (p.info['cpu_percent'] or 0.0) / num_cpus
            lines.append(f"{p.info['pid']:>6}  {name[:25]:<25}  {cpu_percent:>6.1f}  {p.info['memory_percent']:>6.1f}  {mem_kb:>10}")
        except (psutil.NoSuchProcess, psutil.AccessDenied, KeyError):
            continue
    proc_text.delete(1.0, tk.END)
    proc_text.insert(tk.END, '\n'.join(lines))
    proc_text.after(5000, update_process_list)

update_widget()
update_process_list()
root.mainloop()
