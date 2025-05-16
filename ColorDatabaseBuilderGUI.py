import sqlite3
import csv
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.colorchooser import askcolor
from queue import Queue
import threading
import time

class ColorDatabaseBuilderGUI:
    """RGB颜色数据库构建工具 - 完整优化版（带全操作进度条）"""
    
    def __init__(self, master, db_path: str = "ColorDatabase.db"):
        self.master = master
        self.db_path = db_path
        self.task_queue = Queue()
        self.current_operation = None
        self.batch_size_var = tk.IntVar(value=1000)  # 初始化batch_size_var
        
        # 修改顺序：先设置UI再初始化数据库
        self.setup_ui()  # 先创建UI元素
        self._initialize_database()  # 然后初始化数据库
        self.check_queue()
    
    def setup_ui(self):
        """设置用户界面"""
        self.master.title("颜色数据库管理工具 (带进度监控)")
        self.master.geometry("900x650")
        self.master.minsize(700, 500)
        
        # 主布局
        main_panel = ttk.PanedWindow(self.master, orient=tk.HORIZONTAL)
        main_panel.pack(fill=tk.BOTH, expand=True)
        
        # 左侧功能面板
        left_panel = ttk.Frame(main_panel, padding=10)
        main_panel.add(left_panel, weight=1)
        
        # 右侧日志面板
        right_panel = ttk.Frame(main_panel, padding=10)
        main_panel.add(right_panel, weight=2)
        
        # ===== 左侧功能区域 =====
        ttk.Label(left_panel, text="数据库操作", font=('Arial', 12, 'bold')).pack(pady=5)
        
        # 快速操作按钮组
        btn_frame = ttk.Frame(left_panel)
        btn_frame.pack(fill=tk.X, pady=5)
        
        self.import_btn = ttk.Button(
            btn_frame, text="1. 批量导入颜色", 
            command=lambda: self.start_thread(self.import_colors), 
            style='Accent.TButton'
        )
        self.import_btn.pack(fill=tk.X, pady=2)
        
        self.export_btn = ttk.Button(
            btn_frame, text="2. 批量导出颜色", 
            command=lambda: self.start_thread(self.export_colors)
        )
        self.export_btn.pack(fill=tk.X, pady=2)
        
        self.add_btn = ttk.Button(
            btn_frame, text="3. 添加颜色", 
            command=self.add_color
        )
        self.add_btn.pack(fill=tk.X, pady=2)
        
        self.clear_btn = ttk.Button(
            btn_frame, text="4. 清空数据库", 
            command=lambda: self.start_thread(self.clear_database)
        )
        self.clear_btn.pack(fill=tk.X, pady=2)
        
        # 操作状态面板
        self.operation_panel = ttk.LabelFrame(left_panel, text="当前操作状态", padding=10)
        self.operation_panel.pack(fill=tk.X, pady=10)
        
        self.current_operation_label = ttk.Label(
            self.operation_panel, 
            text="无正在进行的操作",
            foreground="gray"
        )
        self.current_operation_label.pack(anchor=tk.W)
        
        # 性能选项
        perf_frame = ttk.LabelFrame(left_panel, text="性能选项", padding=10)
        perf_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(perf_frame, text="批量处理大小:").pack(anchor=tk.W)
        ttk.Spinbox(
            perf_frame, from_=100, to=10000, increment=100,
            textvariable=self.batch_size_var
        ).pack(fill=tk.X)
        
        # 数据库信息显示
        info_frame = ttk.LabelFrame(left_panel, text="数据库信息", padding=10)
        info_frame.pack(fill=tk.X, pady=10)
        
        self.db_info_label = ttk.Label(info_frame, text="正在加载数据库信息...")
        self.db_info_label.pack()
        
        # 颜色预览
        self.color_preview = tk.Canvas(info_frame, height=50, bg='white')
        self.color_preview.pack(fill=tk.X, pady=5)
        
        # ===== 右侧日志区域 =====
        log_frame = ttk.Frame(right_panel)
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(log_frame, text="操作日志", font=('Arial', 12, 'bold')).pack(anchor=tk.W)
        
        self.log_text = tk.Text(
            log_frame, 
            height=20, 
            wrap=tk.WORD,
            state=tk.DISABLED
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(self.log_text)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.log_text.yview)
        
        # 底部状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(
            right_panel, 
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            anchor=tk.W
        )
        status_bar.pack(fill=tk.X, pady=(5,0))
        
        # 主进度条
        self.progress = ttk.Progressbar(
            right_panel,
            orient=tk.HORIZONTAL,
            mode='determinate'
        )
        self.progress.pack(fill=tk.X, pady=(0,5))
        
        # 子进度条（用于嵌套操作）
        self.sub_progress = ttk.Progressbar(
            right_panel,
            orient=tk.HORIZONTAL,
            mode='determinate'
        )
        self.sub_progress.pack(fill=tk.X, pady=(0,5))
        self.sub_progress.pack_forget()  # 默认隐藏
        
        # 性能统计
        self.perf_stats = ttk.Label(
            right_panel,
            text="",
            relief=tk.SUNKEN
        )
        self.perf_stats.pack(fill=tk.X)
        
        # 初始化样式
        self.setup_styles()
        self.update_db_info()
    
    def setup_styles(self):
        """配置界面样式"""
        style = ttk.Style()
        style.configure('Accent.TButton', font=('Arial', 10, 'bold'))
        style.configure('Operation.TLabel', font=('Arial', 10, 'bold'))
    
    def start_thread(self, target):
        """启动后台线程执行任务"""
        if self.current_operation:
            messagebox.showwarning("警告", "已有操作正在进行，请等待完成")
            return
            
        threading.Thread(
            target=target,
            daemon=True
        ).start()
    
    def check_queue(self):
        """检查任务队列并更新UI"""
        try:
            while True:
                task = self.task_queue.get_nowait()
                task()
        except:
            pass
        finally:
            self.master.after(100, self.check_queue)
    
    def log_message(self, message: str):
        """记录日志信息"""
        self.task_queue.put(lambda: self._log_message(message))
    
    def _log_message(self, message: str):
        """实际记录日志的方法"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"• {message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
    
    def update_status(self, message: str):
        """更新状态栏"""
        self.task_queue.put(lambda: self._update_status(message))
    
    def _update_status(self, message: str):
        """实际更新状态栏的方法"""
        self.status_var.set(message)
    
    def update_operation_status(self, operation: str):
        """更新当前操作状态"""
        self.current_operation = operation
        if operation:
            self.task_queue.put(lambda: self._update_operation_status(operation, "blue"))
        else:
            self.task_queue.put(lambda: self._update_operation_status("无正在进行的操作", "gray"))
    
    def _update_operation_status(self, text: str, color: str):
        """实际更新操作状态的方法"""
        self.current_operation_label.config(text=f"当前操作: {text}", foreground=color)
        
    def update_perf_stats(self, stats: str):
        """更新性能统计"""
        self.task_queue.put(lambda: self.perf_stats.config(text=stats))
    
    def enable_buttons(self, enable: bool = True):
        """启用/禁用按钮"""
        state = tk.NORMAL if enable else tk.DISABLED
        self.task_queue.put(lambda: [
            btn.config(state=state) 
            for btn in [self.import_btn, self.export_btn, self.clear_btn, self.add_btn]
        ])
    
    def show_progress(self, show: bool = True):
        """显示/隐藏主进度条"""
        if show:
            self.progress.pack(fill=tk.X, pady=(0,5))
        else:
            self.progress.pack_forget()
    
    def show_sub_progress(self, show: bool = True):
        """显示/隐藏子进度条"""
        if show:
            self.sub_progress.pack(fill=tk.X, pady=(0,5))
        else:
            self.sub_progress.pack_forget()
    
    def _initialize_database(self):
        """初始化数据库"""
        self.update_operation_status("初始化数据库")
        self.log_message("正在初始化数据库...")
        self.show_progress(True)  # 现在可以安全调用，因为progress已创建
        self.progress.configure(mode='indeterminate')
        self.progress.start()
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 检查表是否存在
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='colors'")
            if not cursor.fetchone():
                # 表不存在，创建表
                cursor.execute("""
                    CREATE TABLE colors (
                    r SMALLINT NOT NULL CHECK(r >= 0 AND r <= 255),
                    g SMALLINT NOT NULL CHECK(g >= 0 AND g <= 255),
                    b SMALLINT NOT NULL CHECK(b >= 0 AND b <= 255),
                    name TEXT NOT NULL,
                    PRIMARY KEY (r, g, b)
                )
            """)
                cursor.execute("CREATE INDEX idx_rgb ON colors(r, g, b)")
                conn.commit()
                self.log_message("数据库表创建成功")
            else:
                self.log_message("数据库表已存在")
            
            conn.close()
            self.log_message("数据库初始化完成")
        except Exception as e:
            self.log_message(f"数据库初始化失败: {str(e)}")
            raise
        finally:
            self.progress.stop()
            self.progress.configure(mode='determinate')
            self.show_progress(False)
            self.update_operation_status(None)
            self.update_db_info()
    
    def update_db_info(self):
        """更新数据库信息显示"""
        try:
            start_time = time.time()
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 确保表存在
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='colors'")
            if not cursor.fetchone():
                self.task_queue.put(lambda: self.db_info_label.config(text="数据库未初始化"))
                return
            
            count = cursor.execute("SELECT COUNT(*) FROM colors").fetchone()[0]
            last_color = cursor.execute(
                "SELECT r, g, b, name FROM colors ORDER BY rowid DESC LIMIT 1"
            ).fetchone()
            conn.close()
            
            query_time = (time.time() - start_time) * 1000  # 毫秒
            
            self.task_queue.put(lambda: self._update_db_info(count, last_color))
        except Exception as e:
            self.log_message(f"更新数据库信息错误: {str(e)}")
    
    def _update_db_info(self, count, last_color):
        """实际更新数据库信息的方法"""
        self.db_info_label.config(text=f"当前颜色数量: {count:,} 种")
        
        if last_color:
            r, g, b, name = last_color
            self.color_preview.delete("all")
            self.color_preview.create_rectangle(
                0, 0, 300, 50,
                fill=f'#{r:02x}{g:02x}{b:02x}',
                outline=''
            )
            self.color_preview.create_text(
                150, 25,
                text=f"{name} (R:{r}, G:{g}, B:{b})",
                fill='white' if (r*0.299 + g*0.587 + b*0.114) < 150 else 'black'
            )
    
    def ask_import_mode(self):
        """询问导入模式"""
        dialog = tk.Toplevel(self.master)
        dialog.title("选择导入模式")
        dialog.resizable(False, False)
        dialog.transient(self.master)
        dialog.grab_set()
        
        ttk.Label(dialog, text="请选择导入模式:").pack(pady=10)
        
        mode = tk.StringVar(value='append')
        
        ttk.Radiobutton(
            dialog, text="追加模式 (保留现有数据)", 
            variable=mode, value='append'
        ).pack(anchor=tk.W, padx=20, pady=5)
        
        ttk.Radiobutton(
            dialog, text="替换模式 (清空后导入)", 
            variable=mode, value='replace'
        ).pack(anchor=tk.W, padx=20, pady=5)
        
        result = []
        
        def on_confirm():
            result.append(mode.get())
            dialog.destroy()
        
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)
        
        ttk.Button(btn_frame, text="确定", command=on_confirm).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="取消", command=dialog.destroy).pack(side=tk.LEFT)
        
        dialog.wait_window()
        return result[0] if result else None
    
    def import_colors(self):
        """导入颜色数据"""
        self.enable_buttons(False)
        self.update_operation_status("导入颜色")
        self.show_progress(True)
        
        try:
            # 第一步：选择文件
            file_path = filedialog.askopenfilename(
                title="选择颜色数据文件",
                filetypes=[
                    ("CSV文件", "*.csv"),
                    ("JSON文件", "*.json"),
                    ("所有文件", "*.*")
                ]
            )
            
            if not file_path:
                return
            
            # 第二步：选择导入模式
            mode = self.ask_import_mode()
            if mode is None:
                return
            
            # 第三步：执行导入
            start_time = time.time()
            self.log_message(f"开始导入文件: {file_path}")
            self.progress['value'] = 0
            self.update_status("准备导入数据...")
            
            if file_path.endswith('.csv'):
                success, total = self.import_from_csv(file_path, mode == 'replace')
            elif file_path.endswith('.json'):
                success, total = self.import_from_json(file_path, mode == 'replace')
            else:
                raise ValueError("不支持的文件格式")
            
            elapsed = time.time() - start_time
            speed = success / elapsed if elapsed > 0 else float('inf')
            
            self.log_message(
                f"导入完成! 成功 {success}/{total} 条 "
                f"(耗时: {elapsed:.2f}秒, 速度: {speed:.1f}条/秒)"
            )
            self.update_perf_stats(
                f"性能统计: 处理 {total} 条数据, 耗时 {elapsed:.2f}秒, "
                f"速度 {speed:.1f}条/秒"
            )
            
            self.update_db_info()
            messagebox.showinfo("导入成功", "颜色数据导入完成！")
        except Exception as e:
            messagebox.showerror("导入失败", f"错误: {str(e)}")
            self.log_message(f"导入错误: {str(e)}")
        finally:
            self.enable_buttons(True)
            self.progress['value'] = 0
            self.update_status("就绪")
            self.update_operation_status(None)
            self.show_progress(False)
    
    def import_from_csv(self, file_path: str, replace: bool = False) -> tuple:
        """从CSV导入颜色数据"""
        batch_size = self.batch_size_var.get()
        
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        if not rows:
            raise ValueError("CSV文件为空")
        
        # 自动检测是否有标题行
        has_header = any(cell.lower() in ('r', 'red', 'name') for cell in rows[0])
        
        total = len(rows) - (1 if has_header else 0)
        if total == 0:
            raise ValueError("没有可导入的数据行")
        
        self.progress['maximum'] = total
        self.progress['value'] = 0
        self.update_status(f"正在导入 {total:,} 条颜色数据...")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if replace:
            self.update_status("清空现有数据库...")
            cursor.execute("DELETE FROM colors")
            self.log_message("已清空现有数据库")
        
        success = 0
        batch = []
        
        for i, row in enumerate(rows):
            if has_header and i == 0:
                continue
            
            try:
                if len(row) >= 4:
                    r, g, b = int(row[0]), int(row[1]), int(row[2])
                    name = row[3].strip()
                    
                    if not all(0 <= x <= 255 for x in (r, g, b)):
                        raise ValueError(f"无效的RGB值: {r},{g},{b}")
                    
                    batch.append((r, g, b, name))
                    
                    # 批量提交
                    if len(batch) >= batch_size:
                        cursor.executemany(
                            "INSERT OR IGNORE INTO colors VALUES (?, ?, ?, ?)",
                            batch
                        )
                        success += len(batch)
                        batch = []
                    
                    # 更新进度
                    processed = i + 1 - (1 if has_header else 0)
                    if processed % 100 == 0 or processed == total:
                        self.progress['value'] = processed
                        self.update_status(
                            f"处理中: {processed:,}/{total:,} "
                            f"({processed/total*100:.1f}%)"
                        )
            
            except (ValueError, IndexError) as e:
                self.log_message(f"跳过第 {i+1} 行: {str(e)}")
        
        # 提交剩余批次
        if batch:
            cursor.executemany(
                "INSERT OR IGNORE INTO colors VALUES (?, ?, ?, ?)",
                batch
            )
            success += len(batch)
        
        conn.commit()
        conn.close()
        
        self.progress['value'] = total
        return success, total
    
    def import_from_json(self, file_path: str, replace: bool = False) -> tuple:
        """从JSON导入颜色数据"""
        batch_size = self.batch_size_var.get()
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not isinstance(data, list):
            raise ValueError("JSON文件应该包含颜色数组")
        
        total = len(data)
        if total == 0:
            raise ValueError("没有可导入的颜色数据")
        
        self.progress['maximum'] = total
        self.progress['value'] = 0
        self.update_status(f"正在导入 {total:,} 条颜色数据...")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if replace:
            self.update_status("清空现有数据库...")
            cursor.execute("DELETE FROM colors")
            self.log_message("已清空现有数据库")
        
        success = 0
        batch = []
        
        for i, item in enumerate(data):
            try:
                if isinstance(item, dict):
                    r = item.get('r', item.get('red', 0))
                    g = item.get('g', item.get('green', 0))
                    b = item.get('b', item.get('blue', 0))
                    name = item.get('name', '').strip()
                else:
                    raise ValueError("无效的颜色数据格式")
                
                r, g, b = int(r), int(g), int(b)
                
                if not all(0 <= x <= 255 for x in (r, g, b)):
                    raise ValueError(f"无效的RGB值: {r},{g},{b}")
                
                batch.append((r, g, b, name))
                
                # 批量提交
                if len(batch) >= batch_size:
                    cursor.executemany(
                        "INSERT OR IGNORE INTO colors VALUES (?, ?, ?, ?)",
                        batch
                    )
                    success += len(batch)
                    batch = []
                
                # 更新进度
                if (i + 1) % 100 == 0 or (i + 1) == total:
                    self.progress['value'] = i + 1
                    self.update_status(
                        f"处理中: {i+1:,}/{total:,} "
                        f"({(i+1)/total*100:.1f}%)"
                    )
            
            except (ValueError, KeyError) as e:
                self.log_message(f"跳过第 {i+1} 项: {str(e)}")
        
        # 提交剩余批次
        if batch:
            cursor.executemany(
                "INSERT OR IGNORE INTO colors VALUES (?, ?, ?, ?)",
                batch
            )
            success += len(batch)
        
        conn.commit()
        conn.close()
        
        self.progress['value'] = total
        return success, total
    
    def export_colors(self):
        """导出颜色数据"""
        self.enable_buttons(False)
        self.update_operation_status("导出颜色")
        self.show_progress(True)
        
        try:
            # 第一步：选择文件路径
            file_path = filedialog.asksaveasfilename(
                title="保存颜色数据",
                defaultextension=".csv",
                filetypes=[
                    ("CSV文件", "*.csv"),
                    ("JSON文件", "*.json"),
                    ("所有文件", "*.*")
                ]
            )
            
            if not file_path:
                return
            
            # 第二步：执行导出
            start_time = time.time()
            self.log_message(f"开始导出到: {file_path}")
            self.progress['value'] = 0
            self.update_status("准备导出数据...")
            
            if file_path.endswith('.csv'):
                count = self.export_to_csv(file_path)
            elif file_path.endswith('.json'):
                count = self.export_to_json(file_path)
            else:
                raise ValueError("不支持的导出格式")
            
            elapsed = time.time() - start_time
            speed = count / elapsed if elapsed > 0 else float('inf')
            
            self.log_message(
                f"导出完成! 共导出 {count:,} 条颜色数据 "
                f"(耗时: {elapsed:.2f}秒, 速度: {speed:.1f}条/秒)"
            )
            self.update_perf_stats(
                f"性能统计: 处理 {count:,} 条数据, 耗时 {elapsed:.2f}秒, "
                f"速度 {speed:.1f}条/秒"
            )
            
            messagebox.showinfo("导出成功", "颜色数据导出完成！")
        except Exception as e:
            messagebox.showerror("导出失败", f"错误: {str(e)}")
            self.log_message(f"导出错误: {str(e)}")
        finally:
            self.enable_buttons(True)
            self.progress['value'] = 0
            self.update_status("就绪")
            self.update_operation_status(None)
            self.show_progress(False)
    
    def export_to_csv(self, file_path: str) -> int:
        """导出为CSV文件"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 先获取总数
        cursor.execute("SELECT COUNT(*) FROM colors")
        total = cursor.fetchone()[0]
        
        if total == 0:
            raise ValueError("数据库中没有颜色数据")
        
        self.progress['maximum'] = total
        self.progress['value'] = 0
        self.update_status(f"正在导出 {total:,} 条颜色数据...")
        
        # 使用迭代器分批获取数据
        cursor.execute("SELECT r, g, b, name FROM colors")
        
        with open(file_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['R', 'G', 'B', '颜色名称'])
            
            batch_size = self.batch_size_var.get()
            count = 0
            
            while True:
                batch = cursor.fetchmany(batch_size)
                if not batch:
                    break
                
                writer.writerows(batch)
                count += len(batch)
                
                # 更新进度
                if count % 100 == 0 or count == total:
                    self.progress['value'] = count
                    self.update_status(
                        f"导出中: {count:,}/{total:,} "
                        f"({count/total*100:.1f}%)"
                    )
        
        conn.close()
        return count
    
    def export_to_json(self, file_path: str) -> int:
        """导出为JSON文件"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 先获取总数
        cursor.execute("SELECT COUNT(*) FROM colors")
        total = cursor.fetchone()[0]
        
        if total == 0:
            raise ValueError("数据库中没有颜色数据")
        
        self.progress['maximum'] = total
        self.progress['value'] = 0
        self.update_status(f"正在导出 {total:,} 条颜色数据...")
        
        # 使用迭代器分批获取数据
        cursor.execute("SELECT r, g, b, name FROM colors")
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('[\n')
            
            batch_size = self.batch_size_var.get()
            count = 0
            first_item = True
            
            while True:
                batch = cursor.fetchmany(batch_size)
                if not batch:
                    break
                
                for row in batch:
                    r, g, b, name = row
                    color_data = {
                        "r": r,
                        "g": g,
                        "b": b,
                        "name": name
                    }
                    
                    if not first_item:
                        f.write(',\n')
                    else:
                        first_item = False
                    
                    json.dump(color_data, f, ensure_ascii=False)
                
                count += len(batch)
                
                # 更新进度
                if count % 100 == 0 or count == total:
                    self.progress['value'] = count
                    self.update_status(
                        f"导出中: {count:,}/{total:,} "
                        f"({count/total*100:.1f}%)"
                    )
            
            f.write('\n]')
        
        conn.close()
        return count
    
    def add_color(self):
        """添加单个颜色"""
        dialog = tk.Toplevel(self.master)
        dialog.title("添加新颜色")
        dialog.resizable(False, False)
        dialog.transient(self.master)
        
        # 颜色名称
        ttk.Label(dialog, text="颜色名称:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.E)
        name_entry = ttk.Entry(dialog, width=30)
        name_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        # RGB输入
        ttk.Label(dialog, text="RGB值:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.E)
        
        rgb_frame = ttk.Frame(dialog)
        rgb_frame.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        
        ttk.Label(rgb_frame, text="R:").pack(side=tk.LEFT)
        r_spin = ttk.Spinbox(rgb_frame, from_=0, to=255, width=5)
        r_spin.pack(side=tk.LEFT, padx=2)
        
        ttk.Label(rgb_frame, text="G:").pack(side=tk.LEFT)
        g_spin = ttk.Spinbox(rgb_frame, from_=0, to=255, width=5)
        g_spin.pack(side=tk.LEFT, padx=2)
        
        ttk.Label(rgb_frame, text="B:").pack(side=tk.LEFT)
        b_spin = ttk.Spinbox(rgb_frame, from_=0, to=255, width=5)
        b_spin.pack(side=tk.LEFT, padx=2)
        
        # 颜色选择器按钮
        def choose_color():
            color = askcolor(title="选择颜色")
            if color[0]:
                r, g, b = map(int, color[0])
                r_spin.delete(0, tk.END)
                r_spin.insert(0, r)
                g_spin.delete(0, tk.END)
                g_spin.insert(0, g)
                b_spin.delete(0, tk.END)
                b_spin.insert(0, b)
        
        ttk.Button(
            dialog, 
            text="从调色板选择...", 
            command=choose_color
        ).grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)
        
        # 按钮组
        btn_frame = ttk.Frame(dialog)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=10)
        
        def confirm():
            try:
                name = name_entry.get().strip()
                if not name:
                    raise ValueError("请输入颜色名称")
                
                r = int(r_spin.get())
                g = int(g_spin.get())
                b = int(b_spin.get())
                
                if not all(0 <= x <= 255 for x in (r, g, b)):
                    raise ValueError("RGB值必须在0-255之间")
                
                # 显示添加进度
                self.enable_buttons(False)
                self.update_operation_status("添加颜色")
                self.show_progress(True)
                self.progress['value'] = 0
                self.update_status("正在添加颜色...")
                self.master.update_idletasks()
                
                # 模拟进度动画
                for i in range(1, 101):
                    time.sleep(0.01)  # 短暂延迟让进度条可见
                    self.progress['value'] = i
                    self.master.update_idletasks()
                
                # 实际添加操作
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute(
                        "INSERT OR REPLACE INTO colors VALUES (?, ?, ?, ?)",
                        (r, g, b, name)
                    )
                
                self.log_message(f"添加颜色: {name} (R:{r}, G:{g}, B:{b})")
                self.update_db_info()
                messagebox.showinfo("成功", "颜色添加成功！")
                dialog.destroy()
            except ValueError as e:
                messagebox.showerror("错误", str(e))
            finally:
                self.enable_buttons(True)
                self.progress['value'] = 0
                self.update_status("就绪")
                self.update_operation_status(None)
                self.show_progress(False)
        
        ttk.Button(btn_frame, text="确定", command=confirm).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="取消", command=dialog.destroy).pack(side=tk.LEFT)
        
        # 设置焦点
        name_entry.focus_set()
    
    def clear_database(self):
        """清空数据库"""
        self.enable_buttons(False)
        self.update_operation_status("清空数据库")
        self.show_progress(True)
        
        try:
            if not messagebox.askyesno(
                "确认清空", 
                "确定要清空所有颜色数据吗？此操作不可恢复！",
                icon='warning'
            ):
                return
            
            start_time = time.time()
            self.log_message("开始清空数据库...")
            self.progress['value'] = 0
            self.update_status("准备清空数据库...")
            
            # 模拟进度更新
            for i in range(1, 101):
                time.sleep(0.02)  # 短暂延迟让进度条可见
                self.progress['value'] = i
                self.update_status(f"清空中... {i}%")
                self.master.update_idletasks()
            
            # 实际清空操作
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM colors")
            
            elapsed = time.time() - start_time
            self.log_message(f"数据库已清空 (耗时: {elapsed:.2f}秒)")
            self.update_db_info()
            messagebox.showinfo("成功", "数据库已清空")
        except Exception as e:
            messagebox.showerror("错误", f"清空失败: {str(e)}")
            self.log_message(f"清空错误: {str(e)}")
        finally:
            self.enable_buttons(True)
            self.progress['value'] = 0
            self.update_status("就绪")
            self.update_operation_status(None)
            self.show_progress(False)


if __name__ == "__main__":
    root = tk.Tk()
    app = ColorDatabaseBuilderGUI(root)
    root.mainloop()