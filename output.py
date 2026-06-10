import sqlite3
from datetime import datetime

# 数据库路径
DB_PATH = 'instance/wine_system.db'


def get_winecard_stats():
    """统计酒卡数量"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("\n" + "=" * 60)
    print("🎫 酒卡统计报告")
    print("=" * 60)
    print(f"统计时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 1. 总酒卡数量（所有记录的张数总和）
    cursor.execute("SELECT SUM(quantity) FROM wine_cards")
    total_cards = cursor.fetchone()[0] or 0
    print(f"\n📊 总酒卡数量: {total_cards} 张")
    
    # 2. 有效酒卡数量（status = 'active'）
    cursor.execute("SELECT SUM(quantity) FROM wine_cards WHERE status = 'active'")
    active_cards = cursor.fetchone()[0] or 0
    print(f"✅ 有效酒卡: {active_cards} 张")
    
    # 3. 已使用酒卡数量
    cursor.execute("SELECT SUM(quantity) FROM wine_cards WHERE status = 'used'")
    used_cards = cursor.fetchone()[0] or 0
    print(f"❌ 已使用酒卡: {used_cards} 张")
    
    # 4. 过期酒卡数量
    cursor.execute("SELECT SUM(quantity) FROM wine_cards WHERE status = 'expired'")
    expired_cards = cursor.fetchone()[0] or 0
    print(f"⚠️ 已过期酒卡: {expired_cards} 张")
    
    # 5. 按酒卡类型统计
    print("\n" + "-" * 40)
    print("📋 按酒卡类型统计:")
    print("-" * 40)
    cursor.execute("""
        SELECT card_type, SUM(quantity) as total, COUNT(*) as records
        FROM wine_cards
        GROUP BY card_type
        ORDER BY total DESC
    """)
    types = cursor.fetchall()
    for t in types:
        print(f"  {t[0]}: {t[1]} 张 (共 {t[2]} 条记录)")
    
    # 6. 按客户统计（拥有酒卡最多的客户）
    print("\n" + "-" * 40)
    print("🏆 酒卡持有量 Top 10:")
    print("-" * 40)
    cursor.execute("""
        SELECT c.name, c.phone_tail, SUM(wc.quantity) as total_cards
        FROM wine_cards wc
        JOIN customers c ON wc.customer_id = c.id
        WHERE wc.status = 'active'
        GROUP BY c.id, c.name, c.phone_tail
        ORDER BY total_cards DESC
        LIMIT 10
    """)
    top_customers = cursor.fetchall()
    for idx, tc in enumerate(top_customers, 1):
        print(f"  {idx}. {tc[0]} ({tc[1]}): {tc[2]} 张")
    
    # 7. 近期酒卡存储记录（最近10条）
    print("\n" + "-" * 40)
    print("📅 最近10条酒卡存储记录:")
    print("-" * 40)
    cursor.execute("""
        SELECT c.name, wc.card_type, wc.quantity, wc.store_date, wc.operator, wc.status
        FROM wine_cards wc
        JOIN customers c ON wc.customer_id = c.id
        ORDER BY wc.store_date DESC
        LIMIT 10
    """)
    recent = cursor.fetchall()
    for r in recent:
        status_icon = "✅" if r[5] == 'active' else "❌" if r[5] == 'used' else "⚠️"
        print(f"  {status_icon} {r[0]}: {r[1]} x{r[2]}张 | {r[3][:10]} | 经办:{r[4]}")
    
    conn.close()
    
    print("\n" + "=" * 60)
    print(f"总计: {total_cards} 张酒卡 (有效: {active_cards}, 已使用: {used_cards}, 过期: {expired_cards})")
    print("=" * 60 + "\n")
    
    return {
        'total': total_cards,
        'active': active_cards,
        'used': used_cards,
        'expired': expired_cards
    }


def get_all_stats():
    """获取所有统计信息"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("\n" + "=" * 60)
    print("🥃 HUSTLE BAR 全系统统计报告")
    print("=" * 60)
    print(f"统计时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 客户统计
    cursor.execute("SELECT COUNT(*) FROM customers")
    customer_count = cursor.fetchone()[0]
    cursor.execute("SELECT SUM(points) FROM customers")
    total_points = cursor.fetchone()[0] or 0
    cursor.execute("SELECT SUM(total_consumption) FROM customers")
    total_consumption = cursor.fetchone()[0] or 0
    
    print(f"\n👥 客户统计:")
    print(f"  总客户数: {customer_count} 人")
    print(f"  总积分: {total_points} 分")
    print(f"  总消费: ¥{total_consumption:,.2f}")
    
    # 酒卡统计
    cursor.execute("SELECT SUM(quantity) FROM wine_cards")
    total_cards = cursor.fetchone()[0] or 0
    cursor.execute("SELECT SUM(quantity) FROM wine_cards WHERE status = 'active'")
    active_cards = cursor.fetchone()[0] or 0
    
    print(f"\n🎫 酒卡统计:")
    print(f"  总酒卡: {total_cards} 张")
    print(f"  有效酒卡: {active_cards} 张")
    
    # 存酒统计
    cursor.execute("SELECT SUM(quantity) FROM stored_wines WHERE status = 'stored'")
    stored_wines = cursor.fetchone()[0] or 0
    
    print(f"\n🍾 存酒统计:")
    print(f"  存酒总数: {stored_wines} 瓶")
    
    # SNG统计
    cursor.execute("SELECT COUNT(*) FROM sng_records")
    sng_count = cursor.fetchone()[0] or 0
    cursor.execute("SELECT rank_name, COUNT(*) FROM sng_records GROUP BY rank_name")
    sng_breakdown = cursor.fetchall()
    
    print(f"\n🏆 SNG统计:")
    print(f"  总比赛次数: {sng_count} 次")
    for sb in sng_breakdown:
        print(f"  {sb[0]}: {sb[1]} 次")
    
    # 消费统计
    cursor.execute("SELECT COUNT(*) FROM consumption_records")
    consumption_count = cursor.fetchone()[0] or 0
    
    print(f"\n🍷 消费统计:")
    print(f"  总消费记录: {consumption_count} 条")
    
    conn.close()
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    print("\n🥃 HUSTLE BAR 统计工具")
    print("=" * 40)
    print("1. 统计酒卡数量")
    print("2. 全系统统计")
    print("3. 全部显示")
    print("=" * 40)
    
    choice = input("请选择操作 (1-3): ").strip()
    
    if choice == '1':
        get_winecard_stats()
    elif choice == '2':
        get_all_stats()
    elif choice == '3':
        get_all_stats()
        get_winecard_stats()
    else:
        print("❌ 无效选择，默认显示酒卡统计")
        get_winecard_stats()