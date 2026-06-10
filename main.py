import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import sqlite3
from datetime import datetime


class WineManagementSystem:
    def __init__(self, root):
        self.root = root
        self.root.title("酒水管理系统")
        self.root.geometry("1000x700")

        # 创建数据库连接
        self.conn = sqlite3.connect('wine_system.db')
        self.create_tables()

        # 创建界面
        self.create_widgets()

        # 加载数据
        self.load_customers()
        self.load_wines()
        self.load_consumption_records()

    def create_tables(self):
        """创建数据库表"""
        cursor = self.conn.cursor()

        # 客户表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS customers (
                customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_name TEXT NOT NULL,
                phone_tail TEXT NOT NULL,
                points INTEGER DEFAULT 0,
                total_consumption REAL DEFAULT 0,
                register_time TEXT,
                update_time TEXT,
                UNIQUE(customer_name, phone_tail)
            )
        ''')

        # 酒水表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS wines (
                wine_id INTEGER PRIMARY KEY AUTOINCREMENT,
                wine_name TEXT NOT NULL,
                wine_type TEXT,
                price REAL,
                stock INTEGER DEFAULT 0,
                description TEXT,
                create_time TEXT,
                update_time TEXT
            )
        ''')

        # 积分记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS points_records (
                record_id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER,
                points_change INTEGER,
                change_type TEXT,
                reason TEXT,
                record_time TEXT,
                FOREIGN KEY (customer_id) REFERENCES customers (customer_id)
            )
        ''')

        # 消费记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS consumption_records (
                record_id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER,
                wine_id INTEGER,
                quantity INTEGER,
                total_amount REAL,
                points_earned INTEGER,
                record_time TEXT,
                FOREIGN KEY (customer_id) REFERENCES customers (customer_id),
                FOREIGN KEY (wine_id) REFERENCES wines (wine_id)
            )
        ''')

        self.conn.commit()

    def create_widgets(self):
        """创建界面组件"""
        # 创建标签页
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill='both', expand=True, padx=5, pady=5)

        # 客户管理页面
        self.customer_frame = ttk.Frame(notebook)
        notebook.add(self.customer_frame, text="客户管理")
        self.create_customer_management()

        # 酒水管理页面
        self.wine_frame = ttk.Frame(notebook)
        notebook.add(self.wine_frame, text="酒水管理")
        self.create_wine_management()

        # 积分管理页面
        self.points_frame = ttk.Frame(notebook)
        notebook.add(self.points_frame, text="积分管理")
        self.create_points_management()

        # 消费记录页面
        self.consumption_frame = ttk.Frame(notebook)
        notebook.add(self.consumption_frame, text="消费记录")
        self.create_consumption_management()

    def create_customer_management(self):
        """创建客户管理界面"""
        # 左右布局
        left_frame = ttk.Frame(self.customer_frame)
        left_frame.pack(side='left', fill='both', expand=True, padx=5, pady=5)

        right_frame = ttk.Frame(self.customer_frame)
        right_frame.pack(side='right', fill='both', expand=True, padx=5, pady=5)

        # 左侧：客户列表
        ttk.Label(left_frame, text="客户列表", font=('Arial', 12, 'bold')).pack(pady=5)

        # 搜索框
        search_frame = ttk.Frame(left_frame)
        search_frame.pack(fill='x', pady=5)

        ttk.Label(search_frame, text="搜索:").pack(side='left', padx=5)
        self.search_var = tk.StringVar()
        self.search_var.trace('w', lambda *args: self.search_customers())
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=30)
        self.search_entry.pack(side='left', padx=5)

        ttk.Button(search_frame, text="清除", command=self.clear_search).pack(side='left', padx=5)

        # 客户列表
        columns = ("客户姓名", "手机尾号", "积分", "总消费", "注册时间")
        self.customer_tree = ttk.Treeview(left_frame, columns=columns, show='headings', height=15)

        col_widths = [120, 100, 100, 120, 150]
        for col, width in zip(columns, col_widths):
            self.customer_tree.heading(col, text=col)
            self.customer_tree.column(col, width=width)

        self.customer_tree.pack(fill='both', expand=True)
        self.customer_tree.bind('<<TreeviewSelect>>', self.on_customer_select)

        # 滚动条
        scrollbar = ttk.Scrollbar(left_frame, orient='vertical', command=self.customer_tree.yview)
        scrollbar.pack(side='right', fill='y')
        self.customer_tree.configure(yscrollcommand=scrollbar.set)

        # 右侧：表单区域
        form_frame = ttk.LabelFrame(right_frame, text="客户信息", padding=10)
        form_frame.pack(fill='both', expand=True, padx=5, pady=5)

        ttk.Label(form_frame, text="客户姓名:").grid(row=0, column=0, sticky='e', pady=5, padx=5)
        self.customer_name_entry = ttk.Entry(form_frame, width=20)
        self.customer_name_entry.grid(row=0, column=1, pady=5, padx=5)

        ttk.Label(form_frame, text="手机尾号:").grid(row=1, column=0, sticky='e', pady=5, padx=5)
        self.phone_tail_entry = ttk.Entry(form_frame, width=20)
        self.phone_tail_entry.grid(row=1, column=1, pady=5, padx=5)
        ttk.Label(form_frame, text="(4位数字)", foreground='gray').grid(row=1, column=2, sticky='w')

        ttk.Label(form_frame, text="积分:").grid(row=2, column=0, sticky='e', pady=5, padx=5)
        self.points_display = ttk.Label(form_frame, text="0", foreground='green')
        self.points_display.grid(row=2, column=1, sticky='w', pady=5, padx=5)

        ttk.Label(form_frame, text="总消费:").grid(row=3, column=0, sticky='e', pady=5, padx=5)
        self.consumption_display = ttk.Label(form_frame, text="0.00", foreground='blue')
        self.consumption_display.grid(row=3, column=1, sticky='w', pady=5, padx=5)

        # 按钮区域
        button_frame = ttk.Frame(form_frame)
        button_frame.grid(row=4, column=0, columnspan=3, pady=10)

        ttk.Button(button_frame, text="添加客户", command=self.add_customer).pack(side='left', padx=5)
        ttk.Button(button_frame, text="更新客户", command=self.update_customer).pack(side='left', padx=5)
        ttk.Button(button_frame, text="删除客户", command=self.delete_customer).pack(side='left', padx=5)

    def create_wine_management(self):
        """创建酒水管理界面"""
        left_frame = ttk.Frame(self.wine_frame)
        left_frame.pack(side='left', fill='both', expand=True, padx=5, pady=5)

        right_frame = ttk.Frame(self.wine_frame)
        right_frame.pack(side='right', fill='both', expand=True, padx=5, pady=5)

        # 左侧：酒水列表
        ttk.Label(left_frame, text="酒水列表", font=('Arial', 12, 'bold')).pack(pady=5)

        columns = ("酒水名称", "类型", "价格", "库存", "描述")
        self.wine_tree = ttk.Treeview(left_frame, columns=columns, show='headings', height=15)

        col_widths = [150, 100, 100, 100, 200]
        for col, width in zip(columns, col_widths):
            self.wine_tree.heading(col, text=col)
            self.wine_tree.column(col, width=width)

        self.wine_tree.pack(fill='both', expand=True)
        self.wine_tree.bind('<<TreeviewSelect>>', self.on_wine_select)

        # 右侧：表单区域
        form_frame = ttk.LabelFrame(right_frame, text="酒水信息", padding=10)
        form_frame.pack(fill='both', expand=True, padx=5, pady=5)

        ttk.Label(form_frame, text="酒水名称:").grid(row=0, column=0, sticky='e', pady=5, padx=5)
        self.wine_name_entry = ttk.Entry(form_frame, width=20)
        self.wine_name_entry.grid(row=0, column=1, pady=5, padx=5)

        ttk.Label(form_frame, text="类型:").grid(row=1, column=0, sticky='e', pady=5, padx=5)
        self.wine_type_entry = ttk.Entry(form_frame, width=20)
        self.wine_type_entry.grid(row=1, column=1, pady=5, padx=5)

        ttk.Label(form_frame, text="价格:").grid(row=2, column=0, sticky='e', pady=5, padx=5)
        self.price_entry = ttk.Entry(form_frame, width=20)
        self.price_entry.grid(row=2, column=1, pady=5, padx=5)

        ttk.Label(form_frame, text="库存:").grid(row=3, column=0, sticky='e', pady=5, padx=5)
        self.stock_entry = ttk.Entry(form_frame, width=20)
        self.stock_entry.grid(row=3, column=1, pady=5, padx=5)

        ttk.Label(form_frame, text="描述:").grid(row=4, column=0, sticky='ne', pady=5, padx=5)
        self.description_text = scrolledtext.ScrolledText(form_frame, width=20, height=5)
        self.description_text.grid(row=4, column=1, pady=5, padx=5)

        # 按钮区域
        button_frame = ttk.Frame(form_frame)
        button_frame.grid(row=5, column=0, columnspan=2, pady=10)

        ttk.Button(button_frame, text="添加酒水", command=self.add_wine).pack(side='left', padx=5)
        ttk.Button(button_frame, text="更新酒水", command=self.update_wine).pack(side='left', padx=5)
        ttk.Button(button_frame, text="删除酒水", command=self.delete_wine).pack(side='left', padx=5)

    def create_points_management(self):
        """创建积分管理界面"""
        left_frame = ttk.Frame(self.points_frame)
        left_frame.pack(side='left', fill='both', expand=True, padx=5, pady=5)

        right_frame = ttk.Frame(self.points_frame)
        right_frame.pack(side='right', fill='both', expand=True, padx=5, pady=5)

        # 左侧：积分操作区域
        operation_frame = ttk.LabelFrame(left_frame, text="积分操作", padding=10)
        operation_frame.pack(fill='both', expand=True, pady=5)

        # 客户搜索框
        ttk.Label(operation_frame, text="搜索客户:").grid(row=0, column=0, sticky='e', pady=5, padx=5)
        self.points_search_var = tk.StringVar()
        self.points_search_var.trace('w', lambda *args: self.update_points_customer_list())
        self.points_search_entry = ttk.Entry(operation_frame, textvariable=self.points_search_var, width=30)
        self.points_search_entry.grid(row=0, column=1, pady=5, padx=5)
        ttk.Label(operation_frame, text="(输入姓名或手机尾号)").grid(row=0, column=2, sticky='w', padx=5)

        ttk.Label(operation_frame, text="选择客户:").grid(row=1, column=0, sticky='e', pady=5, padx=5)
        self.customer_combobox = ttk.Combobox(operation_frame, width=30)
        self.customer_combobox.grid(row=1, column=1, pady=5, padx=5)
        self.customer_combobox.bind('<<ComboboxSelected>>', self.on_customer_combo_select)

        ttk.Label(operation_frame, text="当前积分:").grid(row=2, column=0, sticky='e', pady=5, padx=5)
        self.current_points_label = ttk.Label(operation_frame, text="0", foreground='green')
        self.current_points_label.grid(row=2, column=1, sticky='w', pady=5, padx=5)

        ttk.Label(operation_frame, text="操作类型:").grid(row=3, column=0, sticky='e', pady=5, padx=5)
        self.points_type = ttk.Combobox(operation_frame, values=["增加积分", "减少积分"], width=28)
        self.points_type.grid(row=3, column=1, pady=5, padx=5)
        self.points_type.set("增加积分")

        ttk.Label(operation_frame, text="积分数值:").grid(row=4, column=0, sticky='e', pady=5, padx=5)
        self.points_value_entry = ttk.Entry(operation_frame, width=30)
        self.points_value_entry.grid(row=4, column=1, pady=5, padx=5)

        ttk.Label(operation_frame, text="原因说明:").grid(row=5, column=0, sticky='ne', pady=5, padx=5)
        self.reason_text = scrolledtext.ScrolledText(operation_frame, width=32, height=5)
        self.reason_text.grid(row=5, column=1, pady=5, padx=5)

        button_frame = ttk.Frame(operation_frame)
        button_frame.grid(row=6, column=0, columnspan=2, pady=10)
        ttk.Button(button_frame, text="执行积分操作", command=self.update_points).pack()

        # 右侧：积分记录
        ttk.Label(right_frame, text="积分记录", font=('Arial', 12, 'bold')).pack(pady=5)

        columns = ("变更积分", "操作类型", "原因", "操作时间")
        self.record_tree = ttk.Treeview(right_frame, columns=columns, show='headings', height=20)

        col_widths = [100, 100, 200, 150]
        for col, width in zip(columns, col_widths):
            self.record_tree.heading(col, text=col)
            self.record_tree.column(col, width=width)

        self.record_tree.pack(fill='both', expand=True)

    def create_consumption_management(self):
        """创建消费记录管理界面"""
        left_frame = ttk.Frame(self.consumption_frame)
        left_frame.pack(side='left', fill='both', expand=True, padx=5, pady=5)

        right_frame = ttk.Frame(self.consumption_frame)
        right_frame.pack(side='right', fill='both', expand=True, padx=5, pady=5)

        # 左侧：消费记录列表
        ttk.Label(left_frame, text="消费记录", font=('Arial', 12, 'bold')).pack(pady=5)

        columns = ("客户姓名", "手机尾号", "酒水名称", "数量", "消费金额", "获得积分", "消费时间")
        self.consumption_tree = ttk.Treeview(left_frame, columns=columns, show='headings', height=15)

        col_widths = [100, 80, 120, 60, 100, 100, 150]
        for col, width in zip(columns, col_widths):
            self.consumption_tree.heading(col, text=col)
            self.consumption_tree.column(col, width=width)

        self.consumption_tree.pack(fill='both', expand=True)

        # 右侧：添加消费记录
        form_frame = ttk.LabelFrame(right_frame, text="添加消费记录", padding=10)
        form_frame.pack(fill='both', expand=True, padx=5, pady=5)

        # 客户搜索框
        ttk.Label(form_frame, text="搜索客户:").grid(row=0, column=0, sticky='e', pady=5, padx=5)
        self.consumption_search_var = tk.StringVar()
        self.consumption_search_var.trace('w', lambda *args: self.update_consumption_customer_list())
        self.consumption_search_entry = ttk.Entry(form_frame, textvariable=self.consumption_search_var, width=25)
        self.consumption_search_entry.grid(row=0, column=1, pady=5, padx=5)

        ttk.Label(form_frame, text="选择客户:").grid(row=1, column=0, sticky='e', pady=5, padx=5)
        self.consumption_customer = ttk.Combobox(form_frame, width=25)
        self.consumption_customer.grid(row=1, column=1, pady=5, padx=5)

        ttk.Label(form_frame, text="选择酒水:").grid(row=2, column=0, sticky='e', pady=5, padx=5)
        self.consumption_wine = ttk.Combobox(form_frame, width=25)
        self.consumption_wine.grid(row=2, column=1, pady=5, padx=5)
        self.consumption_wine.bind('<<ComboboxSelected>>', self.on_wine_combo_select)

        ttk.Label(form_frame, text="购买数量:").grid(row=3, column=0, sticky='e', pady=5, padx=5)
        self.quantity_entry = ttk.Entry(form_frame, width=27)
        self.quantity_entry.grid(row=3, column=1, pady=5, padx=5)
        self.quantity_entry.bind('<KeyRelease>', self.calculate_total)

        ttk.Label(form_frame, text="单价:").grid(row=4, column=0, sticky='e', pady=5, padx=5)
        self.price_display = ttk.Label(form_frame, text="0.00", foreground='blue')
        self.price_display.grid(row=4, column=1, sticky='w', pady=5, padx=5)

        ttk.Label(form_frame, text="总金额:").grid(row=5, column=0, sticky='e', pady=5, padx=5)
        self.total_display = ttk.Label(form_frame, text="0.00", foreground='red')
        self.total_display.grid(row=5, column=1, sticky='w', pady=5, padx=5)

        ttk.Label(form_frame, text="获得积分:").grid(row=6, column=0, sticky='e', pady=5, padx=5)
        self.points_earned_display = ttk.Label(form_frame, text="0", foreground='green')
        self.points_earned_display.grid(row=6, column=1, sticky='w', pady=5, padx=5)

        button_frame = ttk.Frame(form_frame)
        button_frame.grid(row=7, column=0, columnspan=2, pady=10)
        ttk.Button(button_frame, text="记录消费", command=self.add_consumption).pack(side='left', padx=5)
        ttk.Button(button_frame, text="清空表单", command=self.clear_consumption_form).pack(side='left', padx=5)

    def load_customers(self, search_text=""):
        """加载客户列表"""
        cursor = self.conn.cursor()

        if search_text:
            cursor.execute("""
                SELECT customer_name, phone_tail, points, total_consumption, register_time 
                FROM customers 
                WHERE customer_name LIKE ? OR phone_tail LIKE ?
                ORDER BY customer_id DESC
            """, (f'%{search_text}%', f'%{search_text}%'))
        else:
            cursor.execute("""
                SELECT customer_name, phone_tail, points, total_consumption, register_time 
                FROM customers 
                ORDER BY customer_id DESC
            """)

        customers = cursor.fetchall()

        for item in self.customer_tree.get_children():
            self.customer_tree.delete(item)

        for customer in customers:
            self.customer_tree.insert('', 'end', values=customer)

        # 更新下拉框
        cursor.execute("SELECT customer_id, customer_name, phone_tail FROM customers ORDER BY customer_id DESC")
        customers_for_combo = cursor.fetchall()
        combo_values = [f"{c[0]}-{c[1]}({c[2]})" for c in customers_for_combo]
        self.customer_combobox['values'] = combo_values
        self.consumption_customer['values'] = combo_values

    def update_points_customer_list(self):
        """更新积分页面的客户下拉列表（支持搜索）"""
        search_text = self.points_search_var.get().strip()
        cursor = self.conn.cursor()

        if search_text:
            cursor.execute("""
                           SELECT customer_id, customer_name, phone_tail, points
                           FROM customers
                           WHERE customer_name LIKE ?
                              OR phone_tail LIKE ?
                           ORDER BY customer_id DESC
                           """, (f'%{search_text}%', f'%{search_text}%'))
        else:
            cursor.execute("""
                           SELECT customer_id, customer_name, phone_tail, points
                           FROM customers
                           ORDER BY customer_id DESC LIMIT 20
                           """)

        customers = cursor.fetchall()
        combo_values = [f"{c[0]}-{c[1]}({c[2]})" for c in customers]
        self.customer_combobox['values'] = combo_values

        # 清空当前选择
        self.customer_combobox.set('')
        self.current_points_label.config(text="0")
        self.record_tree.delete(*self.record_tree.get_children())

    def update_consumption_customer_list(self):
        """更新消费页面的客户下拉列表（支持搜索）"""
        search_text = self.consumption_search_var.get().strip()
        cursor = self.conn.cursor()

        if search_text:
            cursor.execute("""
                           SELECT customer_id, customer_name, phone_tail
                           FROM customers
                           WHERE customer_name LIKE ?
                              OR phone_tail LIKE ?
                           ORDER BY customer_id DESC
                           """, (f'%{search_text}%', f'%{search_text}%'))
        else:
            cursor.execute("""
                           SELECT customer_id, customer_name, phone_tail
                           FROM customers
                           ORDER BY customer_id DESC LIMIT 20
                           """)

        customers = cursor.fetchall()
        combo_values = [f"{c[0]}-{c[1]}({c[2]})" for c in customers]
        self.consumption_customer['values'] = combo_values

    def load_customers(self, search_text=""):
        """加载客户列表"""
        cursor = self.conn.cursor()

        if search_text:
            cursor.execute("""
                           SELECT customer_name, phone_tail, points, total_consumption, register_time
                           FROM customers
                           WHERE customer_name LIKE ?
                              OR phone_tail LIKE ?
                           ORDER BY customer_id DESC
                           """, (f'%{search_text}%', f'%{search_text}%'))
        else:
            cursor.execute("""
                           SELECT customer_name, phone_tail, points, total_consumption, register_time
                           FROM customers
                           ORDER BY customer_id DESC
                           """)

        customers = cursor.fetchall()

        for item in self.customer_tree.get_children():
            self.customer_tree.delete(item)

        for customer in customers:
            self.customer_tree.insert('', 'end', values=customer)

        # 更新积分和消费页面的下拉列表
        self.update_points_customer_list()
        self.update_consumption_customer_list()

    def load_wines(self):
        """加载酒水列表"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT wine_name, wine_type, price, stock, description FROM wines")
        wines = cursor.fetchall()

        for item in self.wine_tree.get_children():
            self.wine_tree.delete(item)

        for wine in wines:
            self.wine_tree.insert('', 'end', values=wine)

        # 更新酒水下拉框
        cursor.execute("SELECT wine_id, wine_name, price FROM wines WHERE stock > 0")
        wines_for_combo = cursor.fetchall()
        self.consumption_wine['values'] = [f"{w[0]}-{w[1]}(¥{w[2]})" for w in wines_for_combo]

    def load_points_records(self, customer_id):
        """加载积分记录"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT points_change, change_type, reason, record_time 
            FROM points_records 
            WHERE customer_id = ? 
            ORDER BY record_time DESC
        """, (customer_id,))
        records = cursor.fetchall()

        for item in self.record_tree.get_children():
            self.record_tree.delete(item)

        for record in records:
            self.record_tree.insert('', 'end', values=record)

    def load_consumption_records(self):
        """加载消费记录"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT c.customer_name, c.phone_tail, w.wine_name, cr.quantity, 
                   cr.total_amount, cr.points_earned, cr.record_time
            FROM consumption_records cr
            JOIN customers c ON cr.customer_id = c.customer_id
            JOIN wines w ON cr.wine_id = w.wine_id
            ORDER BY cr.record_time DESC
        """)
        records = cursor.fetchall()

        for item in self.consumption_tree.get_children():
            self.consumption_tree.delete(item)

        for record in records:
            self.consumption_tree.insert('', 'end', values=record)

    def search_customers(self):
        """搜索客户"""
        search_text = self.search_var.get().strip()
        self.load_customers(search_text)

    def clear_search(self):
        """清除搜索"""
        self.search_var.set("")
        self.load_customers()

    def on_customer_select(self, event):
        """选择客户时的处理"""
        selection = self.customer_tree.selection()
        if selection:
            values = self.customer_tree.item(selection[0])['values']
            self.customer_name_entry.delete(0, tk.END)
            self.customer_name_entry.insert(0, values[0])
            self.phone_tail_entry.delete(0, tk.END)
            self.phone_tail_entry.insert(0, values[1])
            self.points_display.config(text=str(values[2]))
            self.consumption_display.config(text=f"{values[3]:.2f}")

    def on_customer_combo_select(self, event):
        """选择客户下拉框时的处理"""
        selection = self.customer_combobox.get()
        if selection:
            customer_id = int(selection.split('-')[0])
            cursor = self.conn.cursor()
            cursor.execute("SELECT points FROM customers WHERE customer_id=?", (customer_id,))
            points = cursor.fetchone()[0]
            self.current_points_label.config(text=str(points))
            self.load_points_records(customer_id)

    def on_wine_select(self, event):
        """选择酒水时的处理"""
        selection = self.wine_tree.selection()
        if selection:
            values = self.wine_tree.item(selection[0])['values']
            self.wine_name_entry.delete(0, tk.END)
            self.wine_name_entry.insert(0, values[0])
            self.wine_type_entry.delete(0, tk.END)
            self.wine_type_entry.insert(0, values[1] if values[1] else "")
            self.price_entry.delete(0, tk.END)
            self.price_entry.insert(0, values[2] if values[2] else "")
            self.stock_entry.delete(0, tk.END)
            self.stock_entry.insert(0, values[3] if values[3] else "")
            self.description_text.delete(1.0, tk.END)
            self.description_text.insert(1.0, values[4] if values[4] else "")

    def on_wine_combo_select(self, event):
        """选择酒水下拉框时的处理"""
        selection = self.consumption_wine.get()
        if selection:
            price_str = selection.split('¥')[1].replace(')', '')
            price = float(price_str)
            self.price_display.config(text=f"{price:.2f}")
            self.calculate_total()

    def calculate_total(self, event=None):
        """计算总金额和获得积分"""
        try:
            quantity = int(self.quantity_entry.get()) if self.quantity_entry.get() else 0
            price_text = self.price_display.cget('text')
            if price_text and price_text != '0.00':
                price = float(price_text)
                total = quantity * price
                points_earned = int(total)
                self.total_display.config(text=f"{total:.2f}")
                self.points_earned_display.config(text=str(points_earned))
            else:
                self.total_display.config(text="0.00")
                self.points_earned_display.config(text="0")
        except ValueError:
            self.total_display.config(text="0.00")
            self.points_earned_display.config(text="0")

    def add_customer(self):
        """添加客户"""
        customer_name = self.customer_name_entry.get().strip()
        phone_tail = self.phone_tail_entry.get().strip()

        if not customer_name or not phone_tail:
            messagebox.showwarning("警告", "请填写客户姓名和手机尾号")
            return

        if len(phone_tail) != 4 or not phone_tail.isdigit():
            messagebox.showwarning("警告", "手机尾号必须是4位数字")
            return

        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO customers (customer_name, phone_tail, points, total_consumption, register_time, update_time)
                VALUES (?, ?, 0, 0, ?, ?)
            """, (customer_name, phone_tail, datetime.now(), datetime.now()))
            self.conn.commit()

            messagebox.showinfo("成功", f"客户 {customer_name} 添加成功")
            self.load_customers()
            self.clear_customer_form()
        except sqlite3.IntegrityError:
            messagebox.showerror("错误", "该客户已存在")

    def update_customer(self):
        """更新客户信息"""
        selection = self.customer_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请先选择要更新的客户")
            return

        old_name = self.customer_tree.item(selection[0])['values'][0]
        old_tail = self.customer_tree.item(selection[0])['values'][1]
        customer_name = self.customer_name_entry.get().strip()
        phone_tail = self.phone_tail_entry.get().strip()

        if not customer_name or not phone_tail:
            messagebox.showwarning("警告", "请填写客户姓名和手机尾号")
            return

        if len(phone_tail) != 4 or not phone_tail.isdigit():
            messagebox.showwarning("警告", "手机尾号必须是4位数字")
            return

        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE customers 
            SET customer_name=?, phone_tail=?, update_time=?
            WHERE customer_name=? AND phone_tail=?
        """, (customer_name, phone_tail, datetime.now(), old_name, old_tail))
        self.conn.commit()

        messagebox.showinfo("成功", "客户信息更新成功")
        self.load_customers()

    def delete_customer(self):
        """删除客户"""
        selection = self.customer_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请先选择要删除的客户")
            return

        if messagebox.askyesno("确认", "确定要删除这个客户吗？\n删除后相关的积分和消费记录也会被删除"):
            customer_name = self.customer_tree.item(selection[0])['values'][0]
            phone_tail = self.customer_tree.item(selection[0])['values'][1]

            cursor = self.conn.cursor()
            cursor.execute("SELECT customer_id FROM customers WHERE customer_name=? AND phone_tail=?",
                           (customer_name, phone_tail))
            customer_id = cursor.fetchone()[0]

            cursor.execute("DELETE FROM points_records WHERE customer_id=?", (customer_id,))
            cursor.execute("DELETE FROM consumption_records WHERE customer_id=?", (customer_id,))
            cursor.execute("DELETE FROM customers WHERE customer_id=?", (customer_id,))
            self.conn.commit()

            messagebox.showinfo("成功", "客户删除成功")
            self.load_customers()
            self.clear_customer_form()

    def add_wine(self):
        """添加酒水"""
        wine_name = self.wine_name_entry.get().strip()
        wine_type = self.wine_type_entry.get().strip()
        price = self.price_entry.get().strip()
        stock = self.stock_entry.get().strip()
        description = self.description_text.get(1.0, tk.END).strip()

        if not wine_name:
            messagebox.showwarning("警告", "请填写酒水名称")
            return

        try:
            price = float(price) if price else 0.0
            stock = int(stock) if stock else 0
        except ValueError:
            messagebox.showerror("错误", "价格必须是数字，库存必须是整数")
            return

        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO wines (wine_name, wine_type, price, stock, description, create_time, update_time)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (wine_name, wine_type, price, stock, description, datetime.now(), datetime.now()))
        self.conn.commit()

        messagebox.showinfo("成功", "酒水添加成功")
        self.load_wines()
        self.clear_wine_form()

    def update_wine(self):
        """更新酒水信息"""
        selection = self.wine_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请先选择要更新的酒水")
            return

        old_name = self.wine_tree.item(selection[0])['values'][0]
        wine_name = self.wine_name_entry.get().strip()
        wine_type = self.wine_type_entry.get().strip()
        price = self.price_entry.get().strip()
        stock = self.stock_entry.get().strip()
        description = self.description_text.get(1.0, tk.END).strip()

        if not wine_name:
            messagebox.showwarning("警告", "请填写酒水名称")
            return

        try:
            price = float(price) if price else 0.0
            stock = int(stock) if stock else 0
        except ValueError:
            messagebox.showerror("错误", "价格必须是数字，库存必须是整数")
            return

        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE wines 
            SET wine_name=?, wine_type=?, price=?, stock=?, description=?, update_time=?
            WHERE wine_name=?
        """, (wine_name, wine_type, price, stock, description, datetime.now(), old_name))
        self.conn.commit()

        messagebox.showinfo("成功", "酒水信息更新成功")
        self.load_wines()

    def delete_wine(self):
        """删除酒水"""
        selection = self.wine_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请先选择要删除的酒水")
            return

        if messagebox.askyesno("确认", "确定要删除这款酒水吗？"):
            wine_name = self.wine_tree.item(selection[0])['values'][0]
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM wines WHERE wine_name=?", (wine_name,))
            self.conn.commit()

            messagebox.showinfo("成功", "酒水删除成功")
            self.load_wines()
            self.clear_wine_form()

    def update_points(self):
        """更新积分"""
        selection = self.customer_combobox.get()
        if not selection:
            messagebox.showwarning("警告", "请选择客户")
            return

        customer_id = int(selection.split('-')[0])
        points_type = self.points_type.get()
        points_value = self.points_value_entry.get().strip()
        reason = self.reason_text.get(1.0, tk.END).strip()

        if not points_value:
            messagebox.showwarning("警告", "请输入积分数值")
            return

        try:
            points_value = int(points_value)
            if points_value <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("错误", "积分数值必须是正整数")
            return

        cursor = self.conn.cursor()

        cursor.execute("SELECT points FROM customers WHERE customer_id=?", (customer_id,))
        current_points = cursor.fetchone()[0]

        if points_type == "增加积分":
            new_points = current_points + points_value
            change = points_value
        else:
            if current_points < points_value:
                messagebox.showerror("错误", "积分不足")
                return
            new_points = current_points - points_value
            change = -points_value

        cursor.execute("UPDATE customers SET points=?, update_time=? WHERE customer_id=?",
                       (new_points, datetime.now(), customer_id))

        cursor.execute("""
            INSERT INTO points_records (customer_id, points_change, change_type, reason, record_time)
            VALUES (?, ?, ?, ?, ?)
        """, (customer_id, change, points_type, reason, datetime.now()))

        self.conn.commit()

        messagebox.showinfo("成功", f"积分{points_type}{points_value}成功")
        self.load_customers()
        self.current_points_label.config(text=str(new_points))
        self.load_points_records(customer_id)
        self.clear_points_form()

    def add_consumption(self):
        """添加消费记录"""
        customer_selection = self.consumption_customer.get()
        wine_selection = self.consumption_wine.get()
        quantity_text = self.quantity_entry.get()

        if not customer_selection or not wine_selection or not quantity_text:
            messagebox.showwarning("警告", "请填写完整的消费信息")
            return

        try:
            quantity = int(quantity_text)
            if quantity <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("错误", "购买数量必须是正整数")
            return

        customer_id = int(customer_selection.split('-')[0])
        wine_id = int(wine_selection.split('-')[0])

        cursor = self.conn.cursor()
        cursor.execute("SELECT price, stock FROM wines WHERE wine_id=?", (wine_id,))
        wine_info = cursor.fetchone()

        if not wine_info:
            messagebox.showerror("错误", "酒水不存在")
            return

        price, stock = wine_info

        if stock < quantity:
            messagebox.showerror("错误", f"库存不足，当前库存只有 {stock} 瓶")
            return

        total_amount = price * quantity
        points_earned = int(total_amount)

        # 记录消费
        cursor.execute("""
                    INSERT INTO consumption_records (customer_id, wine_id, quantity, total_amount, points_earned, record_time)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (customer_id, wine_id, quantity, total_amount, points_earned, datetime.now()))

        # 更新库存
        cursor.execute("UPDATE wines SET stock = stock - ? WHERE wine_id=?", (quantity, wine_id))

        # 更新客户总消费和积分
        cursor.execute("""
                    UPDATE customers 
                    SET total_consumption = total_consumption + ?,
                        points = points + ?,
                        update_time = ?
                    WHERE customer_id = ?
                """, (total_amount, points_earned, datetime.now(), customer_id))

        self.conn.commit()

        messagebox.showinfo("成功", f"消费记录添加成功！\n消费金额: ¥{total_amount:.2f}\n获得积分: {points_earned}")

        # 刷新数据
        self.load_customers()
        self.load_wines()
        self.load_consumption_records()
        self.clear_consumption_form()

    def clear_consumption_form(self):
        """清空消费表单"""
        self.consumption_customer.set('')
        self.consumption_wine.set('')
        self.quantity_entry.delete(0, tk.END)
        self.price_display.config(text="0.00")
        self.total_display.config(text="0.00")
        self.points_earned_display.config(text="0")

    def clear_customer_form(self):
        """清空客户表单"""
        self.customer_name_entry.delete(0, tk.END)
        self.phone_tail_entry.delete(0, tk.END)
        self.points_display.config(text="0")
        self.consumption_display.config(text="0.00")

    def clear_wine_form(self):
        """清空酒水表单"""
        self.wine_name_entry.delete(0, tk.END)
        self.wine_type_entry.delete(0, tk.END)
        self.price_entry.delete(0, tk.END)
        self.stock_entry.delete(0, tk.END)
        self.description_text.delete(1.0, tk.END)

    def clear_points_form(self):
        """清空积分表单"""
        self.points_value_entry.delete(0, tk.END)
        self.reason_text.delete(1.0, tk.END)

    def __del__(self):
        """析构函数，关闭数据库连接"""
        if hasattr(self, 'conn'):
            self.conn.close()

if __name__ == "__main__":
    root = tk.Tk()
    app = WineManagementSystem(root)
    root.mainloop()