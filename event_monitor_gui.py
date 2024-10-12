import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import queue
import csv
from datetime import datetime
from web3 import Web3
import json
import os
from threading import Lock
import traceback
import time
import re
from common_utils import initialize_web3, print_contract_events, monitor_new_events, parse_attribute_dict

class EventMonitorGUI:
    def __init__(self, master):
        self.master = master
        master.title("合约事件监听器")
        master.geometry("600x950")
        
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        self.create_widgets()
        self.monitoring_thread = None
        self.stop_monitoring = threading.Event()
        self.output_queue = queue.Queue()
        self.event_data = []
        self.event_data_lock = Lock()
        self.last_update_time = 0
        self.update_interval = 100  # 更新间隔（毫秒）
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(master, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=14, column=0, columnspan=3, pady=10, sticky='ew')

    def create_widgets(self):
        frame = ttk.Frame(self.master, padding="10")
        frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.master.columnconfigure(0, weight=1)
        self.master.rowconfigure(0, weight=1)

        # 使用 ttk 组件替代 tk 组件，以获得更好的 Mac 风格外观
        frame = ttk.Frame(self.master, padding="10")
        frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.master.columnconfigure(0, weight=1)
        self.master.rowconfigure(0, weight=1)

        # 合约地址输入
        ttk.Label(frame, text="合约地址:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.contract_address_entry = ttk.Entry(frame, width=50)
        self.contract_address_entry.grid(row=0, column=1, columnspan=2, padx=5, pady=5)

        # ABI输入方式选择
        ttk.Label(frame, text="ABI:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.abi_input_var = tk.StringVar(value="file")
        ttk.Radiobutton(frame, text="选择文件", variable=self.abi_input_var, value="file", command=self.toggle_abi_input).grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        ttk.Radiobutton(frame, text="手动输入", variable=self.abi_input_var, value="manual", command=self.toggle_abi_input).grid(row=1, column=2, sticky=tk.W, padx=5, pady=5)

        # ABI文件选择
        self.abi_file_frame = ttk.Frame(frame)
        self.abi_file_frame.grid(row=2, column=0, columnspan=3, padx=5, pady=5)
        self.abi_path_entry = ttk.Entry(self.abi_file_frame, width=40)
        self.abi_path_entry.pack(side=tk.LEFT, padx=5)
        ttk.Button(self.abi_file_frame, text="浏览", command=self.browse_abi).pack(side=tk.LEFT, padx=5)

        # ABI手动输入
        self.abi_text = tk.Text(frame, height=10, width=50)
        self.abi_text.grid(row=3, column=0, columnspan=3, padx=5, pady=5)
        self.abi_text.grid_remove()  # 初始隐藏手动输入框

        # 事件名输入
        ttk.Label(frame, text="事件名:").grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
        self.event_name_entry = ttk.Entry(frame, width=50)
        self.event_name_entry.grid(row=4, column=1, columnspan=2, padx=5, pady=5)

        # RPC链接输入
        ttk.Label(frame, text="RPC链接:").grid(row=5, column=0, sticky=tk.W, padx=5, pady=5)
        self.rpc_url_entry = ttk.Entry(frame, width=50)
        self.rpc_url_entry.grid(row=5, column=1, columnspan=2, padx=5, pady=5)

        # 模式选择
        ttk.Label(frame, text="模式:").grid(row=6, column=0, sticky=tk.W, padx=5, pady=5)
        self.mode_var = tk.StringVar(value="live")
        ttk.Radiobutton(frame, text="历史模式", variable=self.mode_var, value="history", command=self.toggle_history_mode).grid(row=6, column=1, sticky=tk.W, padx=5, pady=5)
        ttk.Radiobutton(frame, text="实时监听", variable=self.mode_var, value="live", command=self.toggle_history_mode).grid(row=6, column=2, sticky=tk.W, padx=5, pady=5)

        # 历史模式选项
        self.history_frame = ttk.Frame(frame)
        self.history_frame.grid(row=7, column=0, columnspan=3, padx=5, pady=5)
        self.history_frame.grid_remove()  # 初始隐藏历史模式选项

        self.history_type_var = tk.StringVar(value="time")
        ttk.Radiobutton(self.history_frame, text="时间范围", variable=self.history_type_var, value="time", command=self.toggle_history_type).grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Radiobutton(self.history_frame, text="区块范围", variable=self.history_type_var, value="block", command=self.toggle_history_type).grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)

        # 时间范围输入
        self.time_frame = ttk.Frame(self.history_frame)
        self.time_frame.grid(row=1, column=0, columnspan=2, padx=5, pady=5)

        ttk.Label(self.time_frame, text="开始时间 (YYYY-MM-DD):").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.start_time_entry = ttk.Entry(self.time_frame, width=20)
        self.start_time_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(self.time_frame, text="结束时间 (YYYY-MM-DD):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.end_time_entry = ttk.Entry(self.time_frame, width=20)
        self.end_time_entry.grid(row=1, column=1, padx=5, pady=5)

        # 区块范围输入
        self.block_frame = ttk.Frame(self.history_frame)
        self.block_frame.grid(row=1, column=0, columnspan=2, padx=5, pady=5)
        self.block_frame.grid_remove()  # 初始隐藏区块范围输入

        ttk.Label(self.block_frame, text="开始区块:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.start_block_entry = ttk.Entry(self.block_frame, width=20)
        self.start_block_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(self.block_frame, text="结束区块:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.end_block_entry = ttk.Entry(self.block_frame, width=20)
        self.end_block_entry.grid(row=1, column=1, padx=5, pady=5)

        # 开始按钮
        self.start_button = ttk.Button(frame, text="开始监听", command=self.start_monitoring)
        self.start_button.grid(row=9, column=0, columnspan=3, pady=10)

        # 停止按钮
        self.stop_button = ttk.Button(frame, text="停止监听", command=self.stop_monitoring_thread, state="disabled")
        self.stop_button.grid(row=10, column=0, columnspan=3, pady=10)

        # 输出文本框和滚动条
        output_frame = ttk.Frame(frame)
        output_frame.grid(row=11, column=0, columnspan=3, padx=5, pady=5, sticky=(tk.W, tk.E, tk.N, tk.S))
        output_frame.columnconfigure(0, weight=1)
        output_frame.rowconfigure(0, weight=1)

        self.output_text = tk.Text(output_frame, height=20, width=70, wrap=tk.NONE)
        self.output_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        scrollbar_y = ttk.Scrollbar(output_frame, orient="vertical", command=self.output_text.yview)
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        self.output_text.configure(yscrollcommand=scrollbar_y.set)

        scrollbar_x = ttk.Scrollbar(output_frame, orient="horizontal", command=self.output_text.xview)
        scrollbar_x.grid(row=1, column=0, sticky="ew")
        self.output_text.configure(xscrollcommand=scrollbar_x.set)

        # 添加保存按钮
        self.save_button = ttk.Button(frame, text="保存到CSV", command=self.save_to_csv, state="disabled")
        self.save_button.grid(row=12, column=0, columnspan=3, pady=10)

        # 添加测试按钮
        self.test_button = ttk.Button(frame, text="填充测试数据", command=self.fill_test_data)
        self.test_button.grid(row=13, column=0, columnspan=3, pady=10)

    def toggle_abi_input(self):
        if self.abi_input_var.get() == "file":
            self.abi_file_frame.grid()
            self.abi_text.grid_remove()
        else:
            self.abi_file_frame.grid_remove()
            self.abi_text.grid()

    def browse_abi(self):
        filename = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if filename:
            self.abi_path_entry.delete(0, tk.END)
            self.abi_path_entry.insert(0, filename)

    def get_abi(self):
        if self.abi_input_var.get() == "file":
            abi_path = self.abi_path_entry.get()
            if not abi_path:
                messagebox.showerror("错误", "请选择ABI文件")
                return None
            try:
                with open(abi_path, 'r') as abi_file:
                    return json.load(abi_file)
            except Exception as e:
                messagebox.showerror("错误", f"读取ABI文件时出错: {str(e)}")
                return None
        else:
            try:
                return json.loads(self.abi_text.get("1.0", tk.END))
            except json.JSONDecodeError:
                messagebox.showerror("错误", "ABI格式不正确")
                return None

    def toggle_history_mode(self):
        if self.mode_var.get() == "history":
            self.history_frame.grid()
        else:
            self.history_frame.grid_remove()

    def toggle_history_type(self):
        if self.history_type_var.get() == "time":
            self.time_frame.grid()
            self.block_frame.grid_remove()
        else:
            self.time_frame.grid_remove()
            self.block_frame.grid()

    def start_monitoring(self):
        contract_address = self.contract_address_entry.get()
        try:
            contract_address = Web3.to_checksum_address(contract_address)
        except ValueError as e:
            messagebox.showerror("错误", f"无效的合约地址: {str(e)}")
            return

        abi = self.get_abi()
        event_name = self.event_name_entry.get()
        rpc_url = self.rpc_url_entry.get()
        mode = self.mode_var.get()

        if not all([contract_address, abi, event_name, rpc_url]):
            messagebox.showerror("错误", "请填写所有必要的信息")
            return

        self.stop_monitoring.clear()
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.event_data = []  # 在开始新的监听之前清空事件数据
        self.save_button.config(state="disabled")

        self.output_text.delete(1.0, tk.END)
        self.last_update_time = 0
        self.master.after(self.update_interval, self.update_output)

        if mode == "history":
            history_type = self.history_type_var.get()
            if history_type == "time":
                start_time = datetime.strptime(self.start_time_entry.get(), '%Y-%m-%d')
                end_time = datetime.strptime(self.end_time_entry.get(), '%Y-%m-%d')
                self.monitoring_thread = threading.Thread(target=self.run_history_mode, 
                                                          args=(contract_address, abi, start_time, end_time, rpc_url, event_name, "time"))
            else:
                start_block = int(self.start_block_entry.get())
                end_block = int(self.end_block_entry.get())
                self.monitoring_thread = threading.Thread(target=self.run_history_mode, 
                                                          args=(contract_address, abi, start_block, end_block, rpc_url, event_name, "block"))
        else:
            self.monitoring_thread = threading.Thread(target=self.run_live_mode, 
                                                      args=(contract_address, abi, rpc_url, event_name))

        self.monitoring_thread.start()

    def update_output(self):
        try:
            while not self.output_queue.empty():
                message = self.output_queue.get_nowait()
                self.output_text.insert(tk.END, message)
                self.output_text.see(tk.END)
        except queue.Empty:
            pass
        
        if not self.stop_monitoring.is_set():
            self.master.after(100, self.update_output)

    def run_history_mode(self, contract_address, abi, start, end, rpc_url, event_name, history_type):
        self.output_queue.put("开始历史模式监听...\n")
        events = print_contract_events(contract_address, abi, start, end, rpc_url, event_name, self.output_queue, self.stop_monitoring.is_set, history_type)
        with self.event_data_lock:
            self.event_data.extend(events)
        self.output_queue.put(f"历史模式监听完成，找到 {len(events)} 个事件\n")
        self.output_queue.put(f"self.event_data 更新，当前长度：{len(self.event_data)}\n")

    def run_live_mode(self, contract_address, abi, rpc_url, event_name):
        self.output_queue.put("开始实时监听...\n")
        while not self.stop_monitoring.is_set():
            new_events = monitor_new_events(contract_address, abi, rpc_url, event_name, self.output_queue, self.stop_monitoring.is_set)
            if new_events:
                with self.event_data_lock:
                    self.event_data.extend(new_events)
                    self.output_queue.put(f"新增 {len(new_events)} 个事件，总事件数：{len(self.event_data)}\n")
            time.sleep(1)

    def stop_monitoring_thread(self):
        self.stop_monitoring.set()
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=5)
        self.master.after(100, self.finalize_stop)  # 延迟执行finalize_stop

    def finalize_stop(self):
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")
        self.save_button.config(state="normal")
        with self.event_data_lock:
            event_count = len(self.event_data)
            self.output_queue.put(f"事件数据内容: {self.event_data}\n")  # 添加这行来查看事件数据的内容
        self.output_queue.put(f"监听已停止，总共收集到 {event_count} 个事件\n")
        self.update_output()

    def save_to_csv(self):
        with self.event_data_lock:
            if not self.event_data:
                messagebox.showinfo("提示", "没有数据可以保存")
                return
            local_event_data = self.event_data.copy()  # 创建一个本地副本
        
        try:
            # 定义字段顺序
            main_fields = ["时间戳", "区块号", "交易哈希", "发送者", "接收者"]
            
            # 获所有可能的字段名，包括展开的事件参数
            all_fields = set()
            args_fields = set()
            for event in local_event_data:
                all_fields.update(event.keys())
                args_str = event.get('事件参数', '{}')
                args_dict = parse_attribute_dict(args_str)
                args_fields.update(args_dict.keys())
            
            # 移除已经在main_fields中的字段和'事件参数'字段
            remaining_fields = sorted(all_fields - set(main_fields) - {'事件参数'})
            
            # 最终的字段顺序
            fieldnames = main_fields + remaining_fields + sorted(args_fields)

            # 获取合约名称
            w3 = Web3(Web3.HTTPProvider(self.rpc_url_entry.get()))
            contract_address = Web3.to_checksum_address(self.contract_address_entry.get())
            abi = self.get_abi()
            contract = w3.eth.contract(address=contract_address, abi=abi)
            try:
                contract_name = contract.functions.name().call()
            except:
                contract_name = contract_address[:8]  # 如果无法获取名称，使用地址的前8个字符

            event_name = self.event_name_entry.get()
            default_filename = f"{contract_name}_{event_name}.csv"

            filename = filedialog.asksaveasfilename(
                initialfile=default_filename,
                defaultextension=".csv",
                filetypes=[("CSV 文件", "*.csv")]
            )
            if not filename:
                return

            # 检查文件是否已存在
            file_exists = os.path.isfile(filename)
            
            # 如果文件存在，则以追加模式打开；否则以写入模式打开
            mode = 'a' if file_exists else 'w'
            
            with open(filename, mode, newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                if not file_exists:
                    writer.writeheader()
                
                for event in local_event_data:
                    # 解析事件参数
                    args_str = event.get('事件参数', '{}')
                    args_dict = parse_attribute_dict(args_str)
                    
                    # 创建新的行数据
                    row = {field: event.get(field, '') for field in fieldnames}
                    row.update(args_dict)  # 添加解析后的事件参数
                    writer.writerow(row)
            
            messagebox.showinfo("成功", f"数据已保存到 {filename}")
        except Exception as e:
            error_msg = f"保存文件时出错: {str(e)}\n{traceback.format_exc()}"
            messagebox.showerror("错误", error_msg)
            print(error_msg)  # 在控制台打印详细错误信息

    def fill_test_data(self):
        # 修改测试数据填充函数，不自动填写 RPC 地址
        # 默认的合约地址
        default_address = "0xdAC17F958D2ee523a2206206994597C13D831ec7"  # 使用校验和地址
        self.contract_address_entry.delete(0, tk.END)
        self.contract_address_entry.insert(0, default_address)

        # 默认的事件名称
        default_event = "Transfer"
        self.event_name_entry.delete(0, tk.END)
        self.event_name_entry.insert(0, default_event)

        # 默认的 ABI
        default_abi_path = "contract_abi.json"
        if os.path.exists(default_abi_path):
            with open(default_abi_path, 'r') as abi_file:
                abi_content = abi_file.read()
            if self.abi_input_var.get() == "file":
                self.abi_path_entry.delete(0, tk.END)
                self.abi_path_entry.insert(0, default_abi_path)
            else:
                self.abi_text.delete("1.0", tk.END)
                self.abi_text.insert(tk.END, abi_content)
        else:
            messagebox.showwarning("警告", f"未找到默认的 ABI 文件: {default_abi_path}")

        messagebox.showinfo("提示", "测试数据已填充（不包括 RPC 地址）")

def main():
    root = tk.Tk()
    gui = EventMonitorGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()