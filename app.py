from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import hashlib
from sqlalchemy import func, case

app = Flask(__name__)
app.secret_key = 'wine_system_secret_key_2024_very_secure'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///wine_system.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# 管理员密码（默认: admin123）
ADMIN_PASSWORD_HASH = hashlib.sha256('admin123'.encode()).hexdigest()


# ==================== 数据模型 ====================

class Customer(db.Model):
    __tablename__ = 'customers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    phone_tail = db.Column(db.String(4), nullable=False)
    points = db.Column(db.Integer, default=0)
    total_consumption = db.Column(db.Float, default=0)
    register_time = db.Column(db.DateTime, default=datetime.now)
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)


class Wine(db.Model):
    __tablename__ = 'wines'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50))
    price = db.Column(db.Float, default=0)
    stock = db.Column(db.Integer, default=0)
    description = db.Column(db.String(200))
    create_time = db.Column(db.DateTime, default=datetime.now)


class PointsRecord(db.Model):
    __tablename__ = 'points_records'
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'))
    points_change = db.Column(db.Integer)
    change_type = db.Column(db.String(20))
    reason = db.Column(db.String(100))
    operator = db.Column(db.String(50))
    record_time = db.Column(db.DateTime, default=datetime.now)


# 酒卡存储表
class WineCard(db.Model):
    __tablename__ = 'wine_cards'
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'))
    card_number = db.Column(db.String(20))
    card_type = db.Column(db.String(50))
    quantity = db.Column(db.Integer, default=1)
    store_date = db.Column(db.DateTime, default=datetime.now)
    expiry_date = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='active')  # active, used, expired
    operator = db.Column(db.String(50))
    note = db.Column(db.String(200))


# 存酒记录表
class StoredWine(db.Model):
    __tablename__ = 'stored_wines'
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'))
    wine_id = db.Column(db.Integer, db.ForeignKey('wines.id'))
    wine_name = db.Column(db.String(100))
    quantity = db.Column(db.Integer, default=1)
    store_date = db.Column(db.DateTime, default=datetime.now)
    expected_pickup_date = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='stored')  # stored, picked_up, expired
    operator = db.Column(db.String(50))
    note = db.Column(db.String(200))


class ConsumptionRecord(db.Model):
    __tablename__ = 'consumption_records'
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'))
    wine_id = db.Column(db.Integer, db.ForeignKey('wines.id'))
    quantity = db.Column(db.Integer)
    total_amount = db.Column(db.Float)
    points_earned = db.Column(db.Integer)
    operator = db.Column(db.String(50))
    record_time = db.Column(db.DateTime, default=datetime.now)


# SNG比赛记录表
class SNGRecord(db.Model):
    __tablename__ = 'sng_records'
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'))
    rank = db.Column(db.String(10))
    rank_name = db.Column(db.String(20))
    points_earned = db.Column(db.Integer, default=0)
    game_date = db.Column(db.DateTime, default=datetime.now)
    operator = db.Column(db.String(50))
    note = db.Column(db.String(200))


# ==================== 路由 ====================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone_tail = request.form.get('phone_tail', '').strip()
        password = request.form.get('password', '')

        if not name or not phone_tail:
            return render_template('login.html', error='请填写姓名和手机尾号')

        if len(phone_tail) != 4 or not phone_tail.isdigit():
            return render_template('login.html', error='手机尾号必须是4位数字')

        customer = Customer.query.filter_by(name=name, phone_tail=phone_tail).first()

        if not customer:
            return render_template('login.html', error='未找到您的信息，请确认姓名和手机尾号')

        session['customer_id'] = customer.id
        session['customer_name'] = customer.name

        if password:
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            if password_hash == ADMIN_PASSWORD_HASH:
                session['admin_logged_in'] = True
                return redirect(url_for('admin_index'))
            else:
                return render_template('login.html', error='管理密码错误')
        else:
            return redirect(url_for('user_dashboard'))

    return render_template('login.html', error=None)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/')
def admin_index():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))
    return render_template('admin.html')


@app.route('/user/dashboard')
def user_dashboard():
    if not session.get('customer_id'):
        return redirect(url_for('login'))

    customer_id = session.get('customer_id')
    customer = Customer.query.get(customer_id)

    if not customer:
        session.clear()
        return redirect(url_for('login'))

    return render_template('user_dashboard.html', customer=customer)


# ==================== API接口（需要登录）====================

def require_admin():
    if not session.get('admin_logged_in'):
        return False
    return True


# ---------- 客户相关API ----------
@app.route('/api/customers')
def get_customers():
    if not require_admin():
        return jsonify({'error': '未授权'}), 401

    keyword = request.args.get('keyword', '')
    if keyword:
        customers = Customer.query.filter(
            (Customer.name.contains(keyword)) |
            (Customer.phone_tail.contains(keyword))
        ).order_by(Customer.points.desc()).all()
    else:
        customers = Customer.query.order_by(Customer.id.desc()).limit(50).all()
    return jsonify([{
        'id': c.id, 'name': c.name, 'phone_tail': c.phone_tail,
        'points': c.points, 'total_consumption': c.total_consumption
    } for c in customers])


@app.route('/api/customers', methods=['POST'])
def add_customer():
    if not require_admin():
        return jsonify({'success': False, 'error': '未授权'}), 401

    data = request.json
    name = data.get('name', '').strip()
    phone_tail = data.get('phone_tail', '').strip()
    if not name or not phone_tail:
        return jsonify({'success': False, 'error': '请填写完整信息'})
    if len(phone_tail) != 4 or not phone_tail.isdigit():
        return jsonify({'success': False, 'error': '手机尾号必须是4位数字'})
    if Customer.query.filter_by(name=name, phone_tail=phone_tail).first():
        return jsonify({'success': False, 'error': '该客户已存在'})
    customer = Customer(name=name, phone_tail=phone_tail)
    db.session.add(customer)
    db.session.commit()
    return jsonify({'success': True,
                    'customer': {'id': customer.id, 'name': customer.name, 'phone_tail': customer.phone_tail,
                                 'points': 0}})


@app.route('/api/customers/<int:id>', methods=['PUT'])
def update_customer(id):
    if not require_admin():
        return jsonify({'success': False, 'error': '未授权'}), 401
    
    data = request.json
    new_name = data.get('name', '').strip()
    new_phone = data.get('phone_tail', '').strip()
    operator = data.get('operator', '')
    
    if not new_name or not new_phone:
        return jsonify({'success': False, 'error': '请填写完整信息'})
    
    if len(new_phone) != 4 or not new_phone.isdigit():
        return jsonify({'success': False, 'error': '手机尾号必须是4位数字'})
    
    customer = Customer.query.get(id)
    if not customer:
        return jsonify({'success': False, 'error': '客户不存在'})
    
    # 检查新名称+手机号是否已被其他客户使用
    existing = Customer.query.filter(
        Customer.name == new_name, 
        Customer.phone_tail == new_phone,
        Customer.id != id
    ).first()
    if existing:
        return jsonify({'success': False, 'error': '该客户已存在'})
    
    customer.name = new_name
    customer.phone_tail = new_phone
    customer.update_time = datetime.now()
    
    db.session.commit()
    
    return jsonify({'success': True})


@app.route('/api/customers/<int:id>', methods=['DELETE'])
def delete_customer(id):
    if not require_admin():
        return jsonify({'success': False, 'error': '未授权'}), 401

    customer = Customer.query.get(id)
    if customer:
        PointsRecord.query.filter_by(customer_id=id).delete()
        ConsumptionRecord.query.filter_by(customer_id=id).delete()
        WineCard.query.filter_by(customer_id=id).delete()
        StoredWine.query.filter_by(customer_id=id).delete()
        SNGRecord.query.filter_by(customer_id=id).delete()
        db.session.delete(customer)
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': '客户不存在'})


# ---------- 积分相关API ----------
@app.route('/api/points', methods=['POST'])
def update_points():
    if not require_admin():
        return jsonify({'success': False, 'error': '未授权'}), 401

    data = request.json
    customer_id = data.get('customer_id')
    points_value = data.get('points')
    action = data.get('action')
    reason = data.get('reason', '')
    operator = data.get('operator', '')
    customer = Customer.query.get(customer_id)
    if not customer:
        return jsonify({'success': False, 'error': '客户不存在'})
    change = points_value if action == 'add' else -points_value
    if customer.points + change < 0:
        return jsonify({'success': False, 'error': '积分不足'})
    customer.points += change
    record = PointsRecord(customer_id=customer_id, points_change=points_value,
                          change_type='增加积分' if action == 'add' else '减少积分',
                          reason=reason, operator=operator)
    db.session.add(record)
    db.session.commit()
    return jsonify({'success': True, 'new_points': customer.points})


@app.route('/api/points_records/<int:customer_id>')
def get_points_records(customer_id):
    if not require_admin():
        return jsonify({'error': '未授权'}), 401

    records = PointsRecord.query.filter_by(customer_id=customer_id).order_by(PointsRecord.record_time.desc()).limit(30).all()
    return jsonify([{
        'points_change': r.points_change, 'change_type': r.change_type,
        'reason': r.reason, 'operator': r.operator,
        'record_time': r.record_time.strftime('%Y-%m-%d %H:%M')
    } for r in records])


# ---------- 酒卡相关API ----------
@app.route('/api/winecards', methods=['POST'])
def add_winecard():
    if not require_admin():
        return jsonify({'success': False, 'error': '未授权'}), 401

    data = request.json
    customer_id = data.get('customer_id')
    card_number = data.get('card_number', '')
    card_type = data.get('card_type')
    quantity = data.get('quantity', 1)
    expiry_date = data.get('expiry_date')
    note = data.get('note', '')
    operator = data.get('operator', '')

    if not card_type:
        return jsonify({'success': False, 'error': '请填写酒卡类型'})

    winecard = WineCard(
        customer_id=customer_id,
        card_number=card_number,
        card_type=card_type,
        quantity=quantity,
        expiry_date=datetime.strptime(expiry_date, '%Y-%m-%d') if expiry_date else None,
        note=note,
        operator=operator
    )
    db.session.add(winecard)
    db.session.commit()

    return jsonify({'success': True})


@app.route('/api/winecards/use', methods=['POST'])
def use_winecard():
    if not require_admin():
        return jsonify({'success': False, 'error': '未授权'}), 401
    
    data = request.json
    card_id = data.get('card_id')
    use_quantity = data.get('quantity', 1)
    operator = data.get('operator', '')
    reason = data.get('reason', '')
    
    winecard = WineCard.query.get(card_id)
    if not winecard:
        return jsonify({'success': False, 'error': '酒卡记录不存在'})
    
    if winecard.status != 'active':
        return jsonify({'success': False, 'error': '酒卡已使用或已过期'})
    
    if winecard.quantity < use_quantity:
        return jsonify({'success': False, 'error': f'酒卡数量不足，剩余 {winecard.quantity} 张'})
    
    winecard.quantity -= use_quantity
    
    if winecard.quantity == 0:
        winecard.status = 'used'
    
    if winecard.note:
        winecard.note = f"{winecard.note}\n{datetime.now().strftime('%Y-%m-%d %H:%M')} 使用{use_quantity}张，操作人:{operator}，原因:{reason}"
    else:
        winecard.note = f"{datetime.now().strftime('%Y-%m-%d %H:%M')} 使用{use_quantity}张，操作人:{operator}，原因:{reason}"
    
    db.session.commit()
    
    return jsonify({'success': True, 'remaining': winecard.quantity})


@app.route('/api/winecards/<int:customer_id>')
def get_winecards(customer_id):
    if not require_admin():
        return jsonify({'error': '未授权'}), 401

    cards = WineCard.query.filter_by(customer_id=customer_id, status='active').order_by(WineCard.store_date.desc()).all()
    return jsonify([{
        'id': c.id, 'card_number': c.card_number, 'card_type': c.card_type,
        'quantity': c.quantity, 'store_date': c.store_date.strftime('%Y-%m-%d %H:%M'),
        'expiry_date': c.expiry_date.strftime('%Y-%m-%d') if c.expiry_date else None,
        'status': c.status, 'note': c.note, 'operator': c.operator
    } for c in cards])


@app.route('/api/winecards/all/<int:customer_id>')
def get_all_winecards(customer_id):
    if not require_admin():
        return jsonify({'error': '未授权'}), 401
    
    cards = WineCard.query.filter_by(customer_id=customer_id).order_by(WineCard.store_date.desc()).all()
    return jsonify([{
        'id': c.id, 'card_number': c.card_number, 'card_type': c.card_type,
        'quantity': c.quantity, 'store_date': c.store_date.strftime('%Y-%m-%d %H:%M'),
        'expiry_date': c.expiry_date.strftime('%Y-%m-%d') if c.expiry_date else None,
        'status': c.status, 'note': c.note, 'operator': c.operator
    } for c in cards])


# ---------- 存酒相关API ----------
@app.route('/api/storedwines', methods=['POST'])
def add_storedwine():
    if not require_admin():
        return jsonify({'success': False, 'error': '未授权'}), 401

    data = request.json
    customer_id = data.get('customer_id')
    wine_id = data.get('wine_id')
    wine_name = data.get('wine_name')
    quantity = data.get('quantity', 1)
    expected_pickup_date = data.get('expected_pickup_date')
    note = data.get('note', '')
    operator = data.get('operator', '')

    stored_wine = StoredWine(
        customer_id=customer_id, wine_id=wine_id, wine_name=wine_name, quantity=quantity,
        expected_pickup_date=datetime.strptime(expected_pickup_date, '%Y-%m-%d') if expected_pickup_date else None,
        note=note, operator=operator
    )
    db.session.add(stored_wine)
    db.session.commit()

    return jsonify({'success': True})


@app.route('/api/storedwines/pickup', methods=['POST'])
def pickup_storedwine():
    if not require_admin():
        return jsonify({'success': False, 'error': '未授权'}), 401
    
    data = request.json
    wine_id = data.get('wine_id')
    pickup_quantity = data.get('quantity', 1)
    operator = data.get('operator', '')
    reason = data.get('reason', '')
    
    stored_wine = StoredWine.query.get(wine_id)
    if not stored_wine:
        return jsonify({'success': False, 'error': '存酒记录不存在'})
    
    if stored_wine.status != 'stored':
        return jsonify({'success': False, 'error': '存酒已取走或已过期'})
    
    if stored_wine.quantity < pickup_quantity:
        return jsonify({'success': False, 'error': f'存酒数量不足，剩余 {stored_wine.quantity} 瓶'})
    
    stored_wine.quantity -= pickup_quantity
    
    if stored_wine.quantity == 0:
        stored_wine.status = 'picked_up'
    
    if stored_wine.note:
        stored_wine.note = f"{stored_wine.note}\n{datetime.now().strftime('%Y-%m-%d %H:%M')} 取走{pickup_quantity}瓶，操作人:{operator}，原因:{reason}"
    else:
        stored_wine.note = f"{datetime.now().strftime('%Y-%m-%d %H:%M')} 取走{pickup_quantity}瓶，操作人:{operator}，原因:{reason}"
    
    db.session.commit()
    
    return jsonify({'success': True, 'remaining': stored_wine.quantity})


@app.route('/api/storedwines/<int:customer_id>')
def get_storedwines(customer_id):
    if not require_admin():
        return jsonify({'error': '未授权'}), 401

    wines = StoredWine.query.filter_by(customer_id=customer_id, status='stored').order_by(StoredWine.store_date.desc()).all()
    return jsonify([{
        'id': w.id, 'wine_name': w.wine_name, 'quantity': w.quantity,
        'store_date': w.store_date.strftime('%Y-%m-%d %H:%M'),
        'expected_pickup_date': w.expected_pickup_date.strftime('%Y-%m-%d') if w.expected_pickup_date else None,
        'status': w.status, 'note': w.note, 'operator': w.operator
    } for w in wines])


@app.route('/api/storedwines/all/<int:customer_id>')
def get_all_storedwines(customer_id):
    if not require_admin():
        return jsonify({'error': '未授权'}), 401
    
    wines = StoredWine.query.filter_by(customer_id=customer_id).order_by(StoredWine.store_date.desc()).all()
    return jsonify([{
        'id': w.id, 'wine_name': w.wine_name, 'quantity': w.quantity,
        'store_date': w.store_date.strftime('%Y-%m-%d %H:%M'),
        'expected_pickup_date': w.expected_pickup_date.strftime('%Y-%m-%d') if w.expected_pickup_date else None,
        'status': w.status, 'note': w.note, 'operator': w.operator
    } for w in wines])


# ---------- 酒水相关API ----------
@app.route('/api/wines')
def get_wines():
    if not require_admin():
        return jsonify({'error': '未授权'}), 401

    wines = Wine.query.order_by(Wine.name).all()
    return jsonify([{
        'id': w.id, 'name': w.name, 'type': w.type or '',
        'price': w.price, 'stock': w.stock, 'description': w.description or ''
    } for w in wines])


@app.route('/api/wines/available')
def get_available_wines():
    if not require_admin():
        return jsonify({'error': '未授权'}), 401

    wines = Wine.query.filter(Wine.stock > 0).order_by(Wine.name).all()
    return jsonify([{'id': w.id, 'name': w.name, 'price': w.price, 'stock': w.stock} for w in wines])


@app.route('/api/wines', methods=['POST'])
def add_wine():
    if not require_admin():
        return jsonify({'success': False, 'error': '未授权'}), 401

    data = request.json
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'success': False, 'error': '请填写酒水名称'})
    wine = Wine(name=name, type=data.get('type', ''), price=data.get('price', 0),
                stock=data.get('stock', 0), description=data.get('description', ''))
    db.session.add(wine)
    db.session.commit()
    return jsonify({'success': True, 'wine': {'id': wine.id, 'name': wine.name, 'price': wine.price, 'stock': wine.stock}})


@app.route('/api/wines/<int:id>', methods=['PUT'])
def update_wine(id):
    if not require_admin():
        return jsonify({'success': False, 'error': '未授权'}), 401

    data = request.json
    wine = Wine.query.get(id)
    if not wine:
        return jsonify({'success': False, 'error': '酒水不存在'})
    wine.name = data.get('name', wine.name)
    wine.type = data.get('type', wine.type)
    wine.price = data.get('price', wine.price)
    wine.stock = data.get('stock', wine.stock)
    wine.description = data.get('description', wine.description)
    db.session.commit()
    return jsonify({'success': True})


@app.route('/api/wines/<int:id>', methods=['DELETE'])
def delete_wine(id):
    if not require_admin():
        return jsonify({'success': False, 'error': '未授权'}), 401

    wine = Wine.query.get(id)
    if wine:
        db.session.delete(wine)
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': '酒水不存在'})


# ---------- 消费相关API ----------
@app.route('/api/consumption', methods=['POST'])
def add_consumption():
    if not require_admin():
        return jsonify({'success': False, 'error': '未授权'}), 401

    data = request.json
    customer_id = data.get('customer_id')
    wine_id = data.get('wine_id')
    quantity = data.get('quantity')
    operator = data.get('operator', '')

    customer = Customer.query.get(customer_id)
    wine = Wine.query.get(wine_id)

    if not customer or not wine:
        return jsonify({'success': False, 'error': '客户或酒水不存在'})

    if wine.stock < quantity:
        return jsonify({'success': False, 'error': f'库存不足，只剩 {wine.stock} 瓶'})

    total = wine.price * quantity
    points_earned = int(total)

    record = ConsumptionRecord(
        customer_id=customer_id, wine_id=wine_id, quantity=quantity,
        total_amount=total, points_earned=points_earned, operator=operator
    )
    db.session.add(record)
    wine.stock -= quantity
    customer.points += points_earned
    customer.total_consumption += total
    db.session.commit()

    return jsonify({
        'success': True, 'total': total, 'points_earned': points_earned, 'new_points': customer.points
    })


@app.route('/api/consumption_records')
def get_consumption_records():
    if not require_admin():
        return jsonify({'error': '未授权'}), 401

    records = db.session.query(
        ConsumptionRecord, Customer.name.label('customer_name'),
        Customer.phone_tail, Wine.name.label('wine_name')
    ).join(Customer, ConsumptionRecord.customer_id == Customer.id)\
     .join(Wine, ConsumptionRecord.wine_id == Wine.id)\
     .order_by(ConsumptionRecord.record_time.desc()).limit(50).all()

    return jsonify([{
        'customer_name': r.customer_name, 'phone_tail': r.phone_tail,
        'wine_name': r.wine_name, 'quantity': r.ConsumptionRecord.quantity,
        'total_amount': r.ConsumptionRecord.total_amount,
        'points_earned': r.ConsumptionRecord.points_earned,
        'operator': r.ConsumptionRecord.operator or '-',
        'record_time': r.ConsumptionRecord.record_time.strftime('%Y-%m-%d %H:%M')
    } for r in records])


# ---------- SNG相关API ----------
@app.route('/api/sng/record', methods=['POST'])
def record_sng():
    if not require_admin():
        return jsonify({'success': False, 'error': '未授权'}), 401

    data = request.json
    customer_id = data.get('customer_id')
    rank = data.get('rank')
    points = data.get('points', 0)
    operator = data.get('operator', '')

    customer = Customer.query.get(customer_id)
    if not customer:
        return jsonify({'success': False, 'error': '客户不存在'})

    customer.points += points

    record = SNGRecord(
        customer_id=customer_id,
        rank='champion' if rank == '冠军' else 'runner_up' if rank == '亚军' else 'third_place',
        rank_name=rank,
        points_earned=points,
        operator=operator
    )
    db.session.add(record)

    points_record = PointsRecord(
        customer_id=customer_id, points_change=points,
        change_type='增加积分', reason=f'SNG比赛{rank}', operator=operator
    )
    db.session.add(points_record)

    db.session.commit()
    return jsonify({'success': True})


@app.route('/api/sng/records/<int:customer_id>')
def get_sng_records(customer_id):
    if not require_admin():
        return jsonify({'error': '未授权'}), 401

    records = SNGRecord.query.filter_by(customer_id=customer_id).order_by(SNGRecord.game_date.desc()).all()
    return jsonify([{
        'rank_name': r.rank_name, 'points_earned': r.points_earned,
        'game_date': r.game_date.strftime('%Y-%m-%d %H:%M'), 'operator': r.operator
    } for r in records])


# ---------- 排行榜API ----------
@app.route('/api/rankings/points')
def get_points_ranking():
    customers = Customer.query.order_by(Customer.points.desc()).limit(50).all()
    return jsonify([{
        'name': c.name, 'phone_tail': c.phone_tail, 'points': c.points
    } for c in customers])


@app.route('/api/rankings/sng')
def get_sng_ranking():
    results = db.session.query(
        Customer.id, Customer.name,
        func.sum(case((SNGRecord.rank_name == '冠军', 1), else_=0)).label('champion_count'),
        func.sum(case((SNGRecord.rank_name == '亚军', 1), else_=0)).label('runner_up_count'),
        func.sum(case((SNGRecord.rank_name == '季军', 1), else_=0)).label('third_place_count'),
        func.count(SNGRecord.id).label('total_count')
    ).outerjoin(SNGRecord, Customer.id == SNGRecord.customer_id)\
     .group_by(Customer.id, Customer.name)\
     .order_by(
        func.sum(case((SNGRecord.rank_name == '冠军', 1), else_=0)).desc(),
        func.sum(case((SNGRecord.rank_name == '亚军', 1), else_=0)).desc(),
        func.sum(case((SNGRecord.rank_name == '季军', 1), else_=0)).desc()
     ).limit(50).all()

    return jsonify([{
        'name': r.name,
        'champion_count': int(r.champion_count or 0),
        'runner_up_count': int(r.runner_up_count or 0),
        'third_place_count': int(r.third_place_count or 0),
        'total_count': int(r.total_count or 0)
    } for r in results])


# ---------- 用户端API（无需登录验证）----------
@app.route('/api/user/points')
def user_points():
    if not session.get('customer_id'):
        return jsonify({'error': '未登录'}), 401

    customer_id = session.get('customer_id')
    customer = Customer.query.get(customer_id)
    if not customer:
        return jsonify({'error': '用户不存在'}), 404
    return jsonify({'points': customer.points})


@app.route('/api/user/records')
def user_records():
    if not session.get('customer_id'):
        return jsonify({'error': '未登录'}), 401

    customer_id = session.get('customer_id')
    records = PointsRecord.query.filter_by(customer_id=customer_id).order_by(PointsRecord.record_time.desc()).limit(20).all()
    return jsonify({
        'records': [{
            'points_change': r.points_change, 'change_type': r.change_type,
            'reason': r.reason, 'operator': r.operator,
            'record_time': r.record_time.strftime('%Y-%m-%d %H:%M')
        } for r in records]
    })


@app.route('/api/user/winecards')
def user_winecards():
    if not session.get('customer_id'):
        return jsonify({'error': '未登录'}), 401

    customer_id = session.get('customer_id')
    cards = WineCard.query.filter_by(customer_id=customer_id, status='active').order_by(WineCard.store_date.desc()).all()
    return jsonify({
        'cards': [{
            'card_type': c.card_type, 'card_number': c.card_number, 'quantity': c.quantity,
            'store_date': c.store_date.strftime('%Y-%m-%d %H:%M'),
            'expiry_date': c.expiry_date.strftime('%Y-%m-%d') if c.expiry_date else None,
            'operator': c.operator
        } for c in cards]
    })


@app.route('/api/user/storedwines')
def user_storedwines():
    if not session.get('customer_id'):
        return jsonify({'error': '未登录'}), 401

    customer_id = session.get('customer_id')
    wines = StoredWine.query.filter_by(customer_id=customer_id, status='stored').order_by(StoredWine.store_date.desc()).all()
    return jsonify({
        'wines': [{
            'wine_name': w.wine_name, 'quantity': w.quantity,
            'store_date': w.store_date.strftime('%Y-%m-%d %H:%M'),
            'expected_pickup_date': w.expected_pickup_date.strftime('%Y-%m-%d') if w.expected_pickup_date else None,
            'operator': w.operator
        } for w in wines]
    })

# ---------- 统计API ----------
@app.route('/api/stats')
def get_stats():
    if not require_admin():
        return jsonify({'error': '未授权'}), 401
    
    customer_count = Customer.query.count()
    wine_count = Wine.query.count()
    total_points = db.session.query(func.sum(Customer.points)).scalar() or 0
    
    return jsonify({
        'customer_count': customer_count,
        'wine_count': wine_count,
        'total_points': total_points
    })

# ==================== 启动 ====================
if __name__ == '__main__':
    with app.app_context():
        db.create_all()

    import socket
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)

    print("\n" + "=" * 60)
    print("🥃 HUSTLE BAR 酒水积分系统已启动！")
    print("=" * 60)
    print("\n📱 手机访问地址（确保同一WiFi）：")
    print("\n🔐 管理后台登录：")
    print(f"   http://{local_ip}:8080/login")
    print("\n👤 用户查询页面（顾客使用）：")
    print(f"   http://{local_ip}:8080/user/dashboard")
    print("\n📝 默认密码：admin123")
    print("\n⚠️  按 Ctrl+C 停止服务")
    print("=" * 60 + "\n")

    app.run(host='0.0.0.0', port=8080, debug=False)