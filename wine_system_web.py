# 保存为 wine_system_web.py
# 运行前先安装：pip install pywebio

from pywebio import start_server
from pywebio.input import *
from pywebio.output import *
from pywebio.session import run_js, set_env, defer_call
import sqlite3
from datetime import datetime
import hashlib


# 数据库操作类
class Database:
    def __init__(self):
        self.conn = sqlite3.connect('wine_system.db', check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()

        # 客户表
        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS customers
                       (
                           customer_id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           customer_name
                           TEXT
                           NOT
                           NULL,
                           phone_tail
                           TEXT
                           NOT
                           NULL,
                           points
                           INTEGER
                           DEFAULT
                           0,
                           total_consumption
                           REAL
                           DEFAULT
                           0,
                           register_time
                           TEXT,
                           update_time
                           TEXT,
                           UNIQUE
                       (
                           customer_name,
                           phone_tail
                       )
                           )
                       ''')

        # 酒水表
        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS wines
                       (
                           wine_id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           wine_name
                           TEXT
                           NOT
                           NULL,
                           wine_type
                           TEXT,
                           price
                           REAL,
                           stock
                           INTEGER
                           DEFAULT
                           0,
                           description
                           TEXT,
                           create_time
                           TEXT,
                           update_time
                           TEXT
                       )
                       ''')

        # 积分记录表
        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS points_records
                       (
                           record_id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           customer_id
                           INTEGER,
                           points_change
                           INTEGER,
                           change_type
                           TEXT,
                           reason
                           TEXT,
                           record_time
                           TEXT,
                           operator
                           TEXT,
                           FOREIGN
                           KEY
                       (
                           customer_id
                       ) REFERENCES customers
                       (
                           customer_id
                       )
                           )
                       ''')

        # 消费记录表
        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS consumption_records
                       (
                           record_id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           customer_id
                           INTEGER,
                           wine_id
                           INTEGER,
                           quantity
                           INTEGER,
                           total_amount
                           REAL,
                           points_earned
                           INTEGER,
                           record_time
                           TEXT,
                           operator
                           TEXT,
                           FOREIGN
                           KEY
                       (
                           customer_id
                       ) REFERENCES customers
                       (
                           customer_id
                       ),
                           FOREIGN KEY
                       (
                           wine_id
                       ) REFERENCES wines
                       (
                           wine_id
                       )
                           )
                       ''')

        self.conn.commit()

    def search_customers(self, keyword):
        cursor = self.conn.cursor()
        cursor.execute("""
                       SELECT customer_id, customer_name, phone_tail, points
                       FROM customers
                       WHERE customer_name LIKE ?
                          OR phone_tail LIKE ?
                       ORDER BY points DESC
                       """, (f'%{keyword}%', f'%{keyword}%'))
        return cursor.fetchall()

    def get_customer_by_id(self, customer_id):
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT customer_id, customer_name, phone_tail, points, total_consumption FROM customers WHERE customer_id=?",
            (customer_id,))
        return cursor.fetchone()

    def get_wines(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT wine_id, wine_name, price, stock FROM wines WHERE stock > 0 ORDER BY wine_name")
        return cursor.fetchall()

    def get_all_wines(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT wine_id, wine_name, wine_type, price, stock, description FROM wines ORDER BY wine_name")
        return cursor.fetchall()

    def update_points(self, customer_id, change, reason, operator):
        cursor = self.conn.cursor()

        # 获取当前积分
        cursor.execute("SELECT points FROM customers WHERE customer_id=?", (customer_id,))
        current_points = cursor.fetchone()[0]
        new_points = current_points + change

        if new_points < 0:
            return False, "积分不足"

        # 更新积分
        cursor.execute("UPDATE customers SET points=?, update_time=? WHERE customer_id=?",
                       (new_points, datetime.now(), customer_id))

        # 添加记录
        change_type = "增加积分" if change > 0 else "减少积分"
        cursor.execute("""
                       INSERT INTO points_records (customer_id, points_change, change_type, reason, record_time,
                                                   operator)
                       VALUES (?, ?, ?, ?, ?, ?)
                       """, (customer_id, abs(change), change_type, reason, datetime.now(), operator))

        self.conn.commit()
        return True, new_points

    def add_consumption(self, customer_id, wine_id, quantity, operator):
        cursor = self.conn.cursor()

        # 获取酒水信息
        cursor.execute("SELECT wine_name, price, stock FROM wines WHERE wine_id=?", (wine_id,))
        wine = cursor.fetchone()
        if not wine:
            return False, "酒水不存在"

        wine_name, price, stock = wine

        if stock < quantity:
            return False, f"库存不足，当前只剩 {stock} 瓶"

        total = price * quantity
        points_earned = int(total)

        # 记录消费
        cursor.execute("""
                       INSERT INTO consumption_records (customer_id, wine_id, quantity, total_amount, points_earned,
                                                        record_time, operator)
                       VALUES (?, ?, ?, ?, ?, ?, ?)
                       """, (customer_id, wine_id, quantity, total, points_earned, datetime.now(), operator))

        # 更新库存
        cursor.execute("UPDATE wines SET stock = stock - ? WHERE wine_id=?", (quantity, wine_id))

        # 更新客户总消费和积分
        cursor.execute("""
                       UPDATE customers
                       SET total_consumption = total_consumption + ?,
                           points            = points + ?,
                           update_time       = ?
                       WHERE customer_id = ?
                       """, (total, points_earned, datetime.now(), customer_id))

        self.conn.commit()
        return True, {"total": total, "points": points_earned, "wine_name": wine_name}

    def add_customer(self, name, phone_tail):
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                           INSERT INTO customers (customer_name, phone_tail, points, total_consumption, register_time,
                                                  update_time)
                           VALUES (?, ?, 0, 0, ?, ?)
                           """, (name, phone_tail, datetime.now(), datetime.now()))
            self.conn.commit()
            return True, cursor.lastrowid
        except sqlite3.IntegrityError:
            return False, "客户已存在"

    def add_wine(self, name, wine_type, price, stock, description):
        cursor = self.conn.cursor()
        cursor.execute("""
                       INSERT INTO wines (wine_name, wine_type, price, stock, description, create_time, update_time)
                       VALUES (?, ?, ?, ?, ?, ?, ?)
                       """, (name, wine_type, price, stock, description, datetime.now(), datetime.now()))
        self.conn.commit()
        return True

    def update_wine(self, wine_id, name, wine_type, price, stock, description):
        cursor = self.conn.cursor()
        cursor.execute("""
                       UPDATE wines
                       SET wine_name=?,
                           wine_type=?,
                           price=?,
                           stock=?,
                           description=?,
                           update_time=?
                       WHERE wine_id = ?
                       """, (name, wine_type, price, stock, description, datetime.now(), wine_id))
        self.conn.commit()

    def delete_wine(self, wine_id):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM wines WHERE wine_id=?", (wine_id,))
        self.conn.commit()

    def get_points_records(self, customer_id, limit=20):
        cursor = self.conn.cursor()
        cursor.execute("""
                       SELECT points_change, change_type, reason, record_time, operator
                       FROM points_records
                       WHERE customer_id = ?
                       ORDER BY record_time DESC LIMIT ?
                       """, (customer_id, limit))
        return cursor.fetchall()

    def get_consumption_records(self, limit=50):
        cursor = self.conn.cursor()
        cursor.execute("""
                       SELECT c.customer_name,
                              c.phone_tail,
                              w.wine_name,
                              cr.quantity,
                              cr.total_amount,
                              cr.points_earned,
                              cr.record_time,
                              cr.operator
                       FROM consumption_records cr
                                JOIN customers c ON cr.customer_id = c.customer_id
                                JOIN wines w ON cr.wine_id = w.wine_id
                       ORDER BY cr.record_time DESC LIMIT ?
                       """, (limit,))
        return cursor.fetchall()


# 页面1：客户搜索和积分查询
def page_customer():
    db = Database()

    set_env(title="客户查询", output_max_width='500px')

    put_markdown('## 🔍 查询客户')

    keyword = input("输入客户姓名或手机尾号", type=TEXT, placeholder="输入姓名或手机尾号")

    if not keyword:
        toast("请输入搜索关键词", color='warning')
        return

    customers = db.search_customers(keyword)

    if not customers:
        put_warning("未找到客户")
        if actions("是否添加新客户？", ["是", "否"]) == "是":
            page_add_customer()
        return

    put_markdown(f'### 找到 {len(customers)} 位客户')

    for c in customers:
        with put_collapsible(f"📇 {c[1]} ({c[2]}) - 积分: {c[3]}"):
            put_text(f"客户ID: {c[0]}")
            put_text(f"手机尾号: {c[2]}")
            put_text(f"当前积分: {c[3]}")

            # 查看积分记录按钮
            if actions("操作", ["查看积分记录", "返回"]) == "查看积分记录":
                records = db.get_points_records(c[0])
                if records:
                    put_table([
                                  ["变更积分", "类型", "原因", "操作人", "时间"]
                              ] + [[r[0], r[1], r[2], r[4], r[3][:16]] for r in records])
                else:
                    put_text("暂无积分记录")


# 页面2：增加积分
def page_add_points():
    db = Database()

    set_env(title="增加积分", output_max_width='500px')

    put_markdown('## ➕ 增加积分')

    keyword = input("输入客户姓名或手机尾号", type=TEXT, placeholder="输入姓名或手机尾号")

    if not keyword:
        return

    customers = db.search_customers(keyword)

    if not customers:
        put_warning("未找到客户")
        return

    # 选择客户
    customer_options = [f"{c[1]} ({c[2]}) - 当前积分:{c[3]}" for c in customers]
    selected = select("选择客户", customer_options)
    idx = customer_options.index(selected)
    customer = customers[idx]

    points = input("增加积分数值", type=NUMBER, required=True)
    if points <= 0:
        toast("积分必须是正数", color='error')
        return

    reason = input("积分原因", type=TEXT, placeholder="例如：消费赠送、活动奖励")
    operator = input("操作人姓名", type=TEXT, required=True, placeholder="荷官姓名")

    success, result = db.update_points(customer[0], points, reason, operator)

    if success:
        put_success(f"✅ 为客户 {customer[1]} 增加 {points} 积分成功！当前积分: {result}")
    else:
        put_error(f"❌ 操作失败: {result}")


# 页面3：扣减积分
def page_reduce_points():
    db = Database()

    set_env(title="扣减积分", output_max_width='500px')

    put_markdown('## ➖ 扣减积分')

    keyword = input("输入客户姓名或手机尾号", type=TEXT, placeholder="输入姓名或手机尾号")

    if not keyword:
        return

    customers = db.search_customers(keyword)

    if not customers:
        put_warning("未找到客户")
        return

    customer_options = [f"{c[1]} ({c[2]}) - 当前积分:{c[3]}" for c in customers]
    selected = select("选择客户", customer_options)
    idx = customer_options.index(selected)
    customer = customers[idx]

    points = input("扣减积分数值", type=NUMBER, required=True)
    if points <= 0:
        toast("积分必须是正数", color='error')
        return

    reason = input("扣减原因", type=TEXT, placeholder="例如：兑换酒水、过期")
    operator = input("操作人姓名", type=TEXT, required=True, placeholder="荷官姓名")

    success, result = db.update_points(customer[0], -points, reason, operator)

    if success:
        put_success(f"✅ 为客户 {customer[1]} 扣减 {points} 积分成功！当前积分: {result}")
    else:
        put_error(f"❌ 操作失败: {result}")


# 页面4：记录消费
def page_consumption():
    db = Database()

    set_env(title="记录消费", output_max_width='500px')

    put_markdown('## 🍷 记录消费')

    keyword = input("输入客户姓名或手机尾号", type=TEXT, placeholder="输入姓名或手机尾号")

    if not keyword:
        return

    customers = db.search_customers(keyword)

    if not customers:
        put_warning("未找到客户")
        if actions("是否添加新客户？", ["是", "否"]) == "是":
            page_add_customer()
        return

    customer_options = [f"{c[1]} ({c[2]})" for c in customers]
    selected = select("选择客户", customer_options)
    idx = customer_options.index(selected)
    customer = customers[idx]

    # 选择酒水
    wines = db.get_wines()
    if not wines:
        put_error("暂无酒水库存，请先添加酒水")
        return

    wine_options = [f"{w[1]} - ¥{w[2]} (库存:{w[3]})" for w in wines]
    selected = select("选择酒水", wine_options)
    idx = wine_options.index(selected)
    wine = wines[idx]

    quantity = input("购买数量", type=NUMBER, required=True)
    if quantity <= 0:
        toast("数量必须是正数", color='error')
        return

    if quantity > wine[3]:
        put_error(f"库存不足，当前只剩 {wine[3]} 瓶")
        return

    total = wine[2] * quantity
    points_earned = int(total)

    put_markdown(f'### 📋 消费确认')
    put_info(f"""
    - 客户: {customer[1]} ({customer[2]})
    - 酒水: {wine[1]}
    - 数量: {quantity} 瓶
    - 单价: ¥{wine[2]}
    - 总金额: ¥{total}
    - 获得积分: {points_earned}
    """)

    operator = input("操作人姓名", type=TEXT, required=True, placeholder="荷官姓名")

    if actions("确认记录消费", ["确认", "取消"]) == "确认":
        success, result = db.add_consumption(customer[0], wine[0], quantity, operator)

        if success:
            put_success(f"""
            ✅ 消费记录成功！
            - 消费金额: ¥{result['total']}
            - 获得积分: {result['points']}
            - 客户当前总积分: {customer[3] + result['points']}
            """)
        else:
            put_error(f"❌ 操作失败: {result}")


# 页面5：添加客户
def page_add_customer():
    db = Database()

    set_env(title="添加客户", output_max_width='500px')

    put_markdown('## 👤 添加新客户')

    name = input("客户姓名", type=TEXT, required=True)
    phone_tail = input("手机尾号", type=TEXT, required=True, placeholder="4位数字")

    if len(phone_tail) != 4 or not phone_tail.isdigit():
        toast("手机尾号必须是4位数字", color='error')
        return

    success, result = db.add_customer(name, phone_tail)

    if success:
        put_success(f"✅ 客户 {name} 添加成功！客户ID: {result}")
    else:
        put_error(f"❌ 添加失败: {result}")


# 页面6：酒水管理
def page_wine_manage():
    db = Database()

    set_env(title="酒水管理", output_max_width='500px')

    put_markdown('## 🍾 酒水管理')

    while True:
        action = select("酒水管理", [
            "查看酒水列表",
            "添加酒水",
            "修改酒水",
            "删除酒水",
            "返回主菜单"
        ])

        if action == "查看酒水列表":
            wines = db.get_all_wines()
            if wines:
                put_table([
                              ["ID", "名称", "类型", "价格", "库存", "描述"]
                          ] + [[w[0], w[1], w[2] or "-", f"¥{w[3]}", w[4], (w[5] or "-")[:20]] for w in wines])
            else:
                put_warning("暂无酒水")

        elif action == "添加酒水":
            name = input("酒水名称", type=TEXT, required=True)
            wine_type = input("酒水类型", type=TEXT, placeholder="威士忌/红酒/啤酒等")
            price = input("价格", type=FLOAT, required=True)
            stock = input("库存数量", type=NUMBER, required=True)
            description = input("描述", type=TEXT)

            db.add_wine(name, wine_type, price, stock, description)
            put_success(f"✅ 酒水 {name} 添加成功")

        elif action == "修改酒水":
            wines = db.get_all_wines()
            if not wines:
                put_warning("暂无酒水")
                continue

            wine_options = [f"{w[0]}. {w[1]} (¥{w[3]})" for w in wines]
            selected = select("选择要修改的酒水", wine_options)
            idx = wine_options.index(selected)
            wine = wines[idx]

            name = input("酒水名称", type=TEXT, value=wine[1])
            wine_type = input("酒水类型", type=TEXT, value=wine[2] or "")
            price = input("价格", type=FLOAT, value=wine[3])
            stock = input("库存数量", type=NUMBER, value=wine[4])
            description = input("描述", type=TEXT, value=wine[5] or "")

            db.update_wine(wine[0], name, wine_type, price, stock, description)
            put_success(f"✅ 酒水 {name} 修改成功")

        elif action == "删除酒水":
            wines = db.get_all_wines()
            if not wines:
                put_warning("暂无酒水")
                continue

            wine_options = [f"{w[0]}. {w[1]} (库存:{w[4]})" for w in wines]
            selected = select("选择要删除的酒水", wine_options)
            idx = wine_options.index(selected)
            wine = wines[idx]

            if actions(f"确认删除 {wine[1]}？", ["确认", "取消"]) == "确认":
                db.delete_wine(wine[0])
                put_success(f"✅ 酒水 {wine[1]} 删除成功")

        else:
            break


# 页面7：查看消费记录
def page_records():
    db = Database()

    set_env(title="消费记录", output_max_width='500px')

    put_markdown('## 📋 最近消费记录')

    records = db.get_consumption_records(30)

    if records:
        put_table([
                      ["客户", "手机尾号", "酒水", "数量", "金额", "积分", "时间", "操作人"]
                  ] + [[
            r[0], r[1], r[2], r[3], f"¥{r[4]}", r[5], r[6][:16], r[7] or "-"
        ] for r in records])
    else:
        put_warning("暂无消费记录")


# 主菜单
def main():
    db = Database()

    set_env(title="德州酒吧酒水积分系统", output_max_width='500px')

    put_markdown('# 🍷 德州酒吧酒水积分系统')

    # 显示统计信息
    cursor = db.conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM customers")
    customer_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM wines WHERE stock > 0")
    wine_count = cursor.fetchone()[0]

    put_info(f"📊 当前系统: {customer_count} 位客户 | {wine_count} 种酒水")

    while True:
        action = select("请选择功能", [
            "🔍 查询客户/积分",
            "➕ 增加积分",
            "➖ 扣减积分",
            "🍷 记录消费",
            "👤 添加新客户",
            "🍾 酒水管理",
            "📋 查看消费记录",
            "🚪 退出系统"
        ])

        if action == "🔍 查询客户/积分":
            page_customer()
        elif action == "➕ 增加积分":
            page_add_points()
        elif action == "➖ 扣减积分":
            page_reduce_points()
        elif action == "🍷 记录消费":
            page_consumption()
        elif action == "👤 添加新客户":
            page_add_customer()
        elif action == "🍾 酒水管理":
            page_wine_manage()
        elif action == "📋 查看消费记录":
            page_records()
        else:
            put_markdown('## 👋 感谢使用！')
            break


if __name__ == '__main__':
    start_server(main, port=8080, debug=True)