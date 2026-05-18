from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import StringField, FloatField, IntegerField, SelectField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Optional
from werkzeug.utils import secure_filename
import os
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///equipment.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads/documents'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

db = SQLAlchemy(app)

# Модель оборудования
class Equipment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    
    # Основная информация
    name = db.Column(db.String(200), nullable=False)
    model = db.Column(db.String(200), nullable=False)
    manufacturer = db.Column(db.String(200), nullable=False)
    serial_number = db.Column(db.String(100), unique=True, nullable=False)
    category = db.Column(db.String(100), nullable=False)  # router, switch, server, etc.
    
    # Технические характеристики
    speed = db.Column(db.Float)  # Мбит/с
    bandwidth = db.Column(db.Float)  # Гбит/с
    power_consumption = db.Column(db.Float)  # Вт
    ports_count = db.Column(db.Integer)
    
    # Габариты
    width = db.Column(db.Float)  # мм
    height = db.Column(db.Float)  # мм
    depth = db.Column(db.Float)  # мм
    weight = db.Column(db.Float)  # кг
    
    # Статус и количество
    quantity = db.Column(db.Integer, default=1)
    status = db.Column(db.String(50), default='available')  # available, in_use, maintenance, retired
    location = db.Column(db.String(200))
    
    # Документы
    documents = db.relationship('Document', backref='equipment', lazy=True, cascade='all, delete-orphan')
    
    # Даты
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Equipment {self.name} - {self.serial_number}>'

# Модель документов
class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    equipment_id = db.Column(db.Integer, db.ForeignKey('equipment.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    document_type = db.Column(db.String(50), nullable=False)  # invoice, manual, certificate, other
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Document {self.filename}>'

# Формы
class EquipmentForm(FlaskForm):
    name = StringField('Название', validators=[DataRequired()])
    model = StringField('Модель', validators=[DataRequired()])
    manufacturer = StringField('Производитель', validators=[DataRequired()])
    serial_number = StringField('Серийный номер', validators=[DataRequired()])
    category = SelectField('Категория', choices=[
        ('router', 'Маршрутизатор'),
        ('switch', 'Коммутатор'),
        ('server', 'Сервер'),
        ('storage', 'Система хранения'),
        ('firewall', 'Фаервол'),
        ('other', 'Другое')
    ], validators=[DataRequired()])
    
    speed = FloatField('Скорость (Мбит/с)', validators=[Optional()])
    bandwidth = FloatField('Пропускная способность (Гбит/с)', validators=[Optional()])
    power_consumption = FloatField('Потребление (Вт)', validators=[Optional()])
    ports_count = IntegerField('Количество портов', validators=[Optional()])
    
    width = FloatField('Ширина (мм)', validators=[Optional()])
    height = FloatField('Высота (мм)', validators=[Optional()])
    depth = FloatField('Глубина (мм)', validators=[Optional()])
    weight = FloatField('Вес (кг)', validators=[Optional()])
    
    quantity = IntegerField('Количество', validators=[DataRequired()])
    status = SelectField('Статус', choices=[
        ('available', 'В наличии'),
        ('in_use', 'В эксплуатации'),
        ('maintenance', 'В обслуживании'),
        ('retired', 'Списано')
    ], validators=[DataRequired()])
    location = StringField('Местоположение', validators=[Optional()])
    
    submit = SubmitField('Сохранить')

class DocumentUploadForm(FlaskForm):
    document = FileField('Документ', validators=[
        FileRequired(),
        FileAllowed(['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png', 'txt'], 'Только PDF, DOC, изображения и TXT файлы!')
    ])
    document_type = SelectField('Тип документа', choices=[
        ('invoice', 'Накладная'),
        ('manual', 'Инструкция'),
        ('certificate', 'Сертификат'),
        ('warranty', 'Гарантия'),
        ('other', 'Другое')
    ], validators=[DataRequired()])
    submit = SubmitField('Загрузить')

class SearchForm(FlaskForm):
    search_query = StringField('Поиск')
    category = SelectField('Категория', choices=[('all', 'Все')] + [
        ('router', 'Маршрутизатор'),
        ('switch', 'Коммутатор'),
        ('server', 'Сервер'),
        ('storage', 'Система хранения'),
        ('firewall', 'Фаервол'),
        ('other', 'Другое')
    ])
    status = SelectField('Статус', choices=[('all', 'Все')] + [
        ('available', 'В наличии'),
        ('in_use', 'В эксплуатации'),
        ('maintenance', 'В обслуживании'),
        ('retired', 'Списано')
    ])
    submit = SubmitField('Поиск')

# Создание БД
with app.app_context():
    db.create_all()

# Маршруты
@app.route('/')
def index():
    form = SearchForm()
    
    # Устанавливаем значения формы из параметров запроса для сохранения состояния фильтров
    if request.args.get('search_query'):
        form.search_query.data = request.args.get('search_query')
    if request.args.get('category'):
        form.category.data = request.args.get('category')
    if request.args.get('status'):
        form.status.data = request.args.get('status')
    
    query = Equipment.query
    
    # Применение фильтров
    if request.args.get('search_query'):
        search = request.args.get('search_query')
        query = query.filter(
            db.or_(
                Equipment.name.ilike(f'%{search}%'),
                Equipment.model.ilike(f'%{search}%'),
                Equipment.manufacturer.ilike(f'%{search}%'),
                Equipment.serial_number.ilike(f'%{search}%')
            )
        )
    
    if request.args.get('category') and request.args.get('category') != 'all':
        query = query.filter(Equipment.category == request.args.get('category'))
    
    if request.args.get('status') and request.args.get('status') != 'all':
        query = query.filter(Equipment.status == request.args.get('status'))
    
    equipment_list = query.order_by(Equipment.created_at.desc()).all()
    
    # Статистика
    total_count = Equipment.query.count()
    total_units = db.session.query(db.func.sum(Equipment.quantity)).scalar() or 0
    available_count = Equipment.query.filter_by(status='available').count()
    
    return render_template('index.html', 
                         equipment_list=equipment_list, 
                         form=form,
                         total_count=total_count,
                         total_units=total_units,
                         available_count=available_count)

@app.route('/add', methods=['GET', 'POST'])
def add_equipment():
    form = EquipmentForm()
    if form.validate_on_submit():
        equipment = Equipment(
            name=form.name.data,
            model=form.model.data,
            manufacturer=form.manufacturer.data,
            serial_number=form.serial_number.data,
            category=form.category.data,
            speed=form.speed.data,
            bandwidth=form.bandwidth.data,
            power_consumption=form.power_consumption.data,
            ports_count=form.ports_count.data,
            width=form.width.data,
            height=form.height.data,
            depth=form.depth.data,
            weight=form.weight.data,
            quantity=form.quantity.data,
            status=form.status.data,
            location=form.location.data
        )
        
        try:
            db.session.add(equipment)
            db.session.commit()
            flash('Оборудование успешно добавлено!', 'success')
            return redirect(url_for('view_equipment', id=equipment.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при добавлении: {str(e)}', 'danger')
    
    return render_template('add_equipment.html', form=form)

@app.route('/equipment/<int:id>')
def view_equipment(id):
    equipment = Equipment.query.get_or_404(id)
    upload_form = DocumentUploadForm()
    return render_template('view_equipment.html', equipment=equipment, upload_form=upload_form)

@app.route('/equipment/<int:id>/edit', methods=['GET', 'POST'])
def edit_equipment(id):
    equipment = Equipment.query.get_or_404(id)
    form = EquipmentForm(obj=equipment)
    
    if form.validate_on_submit():
        equipment.name = form.name.data
        equipment.model = form.model.data
        equipment.manufacturer = form.manufacturer.data
        equipment.serial_number = form.serial_number.data
        equipment.category = form.category.data
        equipment.speed = form.speed.data
        equipment.bandwidth = form.bandwidth.data
        equipment.power_consumption = form.power_consumption.data
        equipment.ports_count = form.ports_count.data
        equipment.width = form.width.data
        equipment.height = form.height.data
        equipment.depth = form.depth.data
        equipment.weight = form.weight.data
        equipment.quantity = form.quantity.data
        equipment.status = form.status.data
        equipment.location = form.location.data
        
        try:
            db.session.commit()
            flash('Оборудование успешно обновлено!', 'success')
            return redirect(url_for('view_equipment', id=equipment.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при обновлении: {str(e)}', 'danger')
    
    return render_template('edit_equipment.html', form=form, equipment=equipment)

@app.route('/equipment/<int:id>/delete', methods=['POST'])
def delete_equipment(id):
    equipment = Equipment.query.get_or_404(id)
    try:
        db.session.delete(equipment)
        db.session.commit()
        flash('Оборудование успешно удалено!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при удалении: {str(e)}', 'danger')
    
    return redirect(url_for('index'))

@app.route('/equipment/<int:id>/upload', methods=['POST'])
def upload_document(id):
    equipment = Equipment.query.get_or_404(id)
    form = DocumentUploadForm()
    
    if form.validate_on_submit():
        file = form.document.data
        filename = secure_filename(file.filename)
        
        # Генерируем уникальное имя файла
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"{timestamp}_{filename}"
        
        # Сохраняем файл
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(filepath)
        
        # Создаем запись в БД
        document = Document(
            equipment_id=equipment.id,
            filename=unique_filename,
            original_filename=filename,
            document_type=form.document_type.data
        )
        
        try:
            db.session.add(document)
            db.session.commit()
            flash('Документ успешно загружен!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при загрузке документа: {str(e)}', 'danger')
            os.remove(filepath)
    
    return redirect(url_for('view_equipment', id=id))

@app.route('/equipment/<int:id>/document/<int:doc_id>')
def download_document(id, doc_id):
    document = Document.query.get_or_404(doc_id)
    if document.equipment_id != id:
        flash('Документ не найден', 'danger')
        return redirect(url_for('index'))
    
    return send_from_directory(app.config['UPLOAD_FOLDER'], document.filename, 
                             as_attachment=True, attachment_filename=document.original_filename)

@app.route('/equipment/<int:id>/document/<int:doc_id>/delete', methods=['POST'])
def delete_document(id, doc_id):
    document = Document.query.get_or_404(doc_id)
    if document.equipment_id != id:
        flash('Документ не найден', 'danger')
        return redirect(url_for('index'))
    
    try:
        # Удаляем файл
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], document.filename)
        if os.path.exists(filepath):
            os.remove(filepath)
        
        # Удаляем запись из БД
        db.session.delete(document)
        db.session.commit()
        flash('Документ успешно удален!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при удалении документа: {str(e)}', 'danger')
    
    return redirect(url_for('view_equipment', id=id))

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
