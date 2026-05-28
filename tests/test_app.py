import unittest
import os
import tempfile
import shutil
from datetime import datetime
from app import app, db, Equipment, Document

class TestEquipmentSystem(unittest.TestCase):
    
    def setUp(self):
        """Настройка тестового окружения перед каждым тестом"""
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['WTF_CSRF_ENABLED'] = False  # Отключаем CSRF для тестов
        self.app.config['UPLOAD_FOLDER'] = tempfile.mkdtemp()
        
        self.client = self.app.test_client()
        
        with self.app.app_context():
            db.create_all()
    
    def tearDown(self):
        """Очистка после каждого теста"""
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
        
        # Очищаем временную директорию с файлами
        if os.path.exists(self.app.config['UPLOAD_FOLDER']):
            shutil.rmtree(self.app.config['UPLOAD_FOLDER'], ignore_errors=True)
    
    # ==================== Тесты модели Equipment ====================
    
    def test_create_equipment(self):
        """Тест создания оборудования"""
        with self.app.app_context():
            equipment = Equipment(
                name='Test Router',
                model='Cisco ISR 4000',
                manufacturer='Cisco',
                serial_number='SN123456789',
                category='router',
                speed=1000.0,
                quantity=5,
                status='available'
            )
            db.session.add(equipment)
            db.session.commit()
            
            result = Equipment.query.filter_by(serial_number='SN123456789').first()
            
            self.assertIsNotNone(result)
            self.assertEqual(result.name, 'Test Router')
            self.assertEqual(result.model, 'Cisco ISR 4000')
            self.assertEqual(result.manufacturer, 'Cisco')
            self.assertEqual(result.category, 'router')
            self.assertEqual(result.speed, 1000.0)
            self.assertEqual(result.quantity, 5)
            self.assertEqual(result.status, 'available')
    
    def test_equipment_repr(self):
        """Тест строкового представления оборудования"""
        with self.app.app_context():
            equipment = Equipment(
                name='Test Switch',
                model='HP ProCurve',
                manufacturer='HP',
                serial_number='SN987654321',
                category='switch'
            )
            db.session.add(equipment)
            db.session.commit()
            
            self.assertEqual(repr(equipment), '<Equipment Test Switch - SN987654321>')
    
    def test_equipment_optional_fields(self):
        """Тест оборудования с необязательными полями (None значения)"""
        with self.app.app_context():
            equipment = Equipment(
                name='Basic Device',
                model='Simple Model',
                manufacturer='Generic',
                serial_number='SN000000001',
                category='other',
                speed=None,
                bandwidth=None,
                power_consumption=None,
                ports_count=None,
                width=None,
                height=None,
                depth=None,
                weight=None
            )
            db.session.add(equipment)
            db.session.commit()
            
            result = Equipment.query.filter_by(serial_number='SN000000001').first()
            
            self.assertIsNone(result.speed)
            self.assertIsNone(result.bandwidth)
            self.assertIsNone(result.power_consumption)
            self.assertIsNone(result.ports_count)
            self.assertIsNone(result.width)
            self.assertIsNone(result.height)
            self.assertIsNone(result.depth)
            self.assertIsNone(result.weight)
    
    def test_equipment_unique_serial_number(self):
        """Тест уникальности серийного номера"""
        with self.app.app_context():
            equipment1 = Equipment(
                name='Device 1',
                model='Model A',
                manufacturer='Manuf A',
                serial_number='SN-UNIQUE-001',
                category='router'
            )
            db.session.add(equipment1)
            db.session.commit()
            
            equipment2 = Equipment(
                name='Device 2',
                model='Model B',
                manufacturer='Manuf B',
                serial_number='SN-UNIQUE-001',  # Дубликат серийного номера
                category='switch'
            )
            db.session.add(equipment2)
            
            with self.assertRaises(Exception):
                db.session.commit()
    
    def test_update_equipment(self):
        """Тест обновления оборудования"""
        with self.app.app_context():
            equipment = Equipment(
                name='Old Name',
                model='Old Model',
                manufacturer='Old Manuf',
                serial_number='SN-UPDATE-001',
                category='router',
                quantity=1,
                status='available'
            )
            db.session.add(equipment)
            db.session.commit()
            
            equipment.name = 'New Name'
            equipment.quantity = 10
            equipment.status = 'in_use'
            equipment.location = 'Server Room A'
            db.session.commit()
            
            result = Equipment.query.filter_by(serial_number='SN-UPDATE-001').first()
            
            self.assertEqual(result.name, 'New Name')
            self.assertEqual(result.quantity, 10)
            self.assertEqual(result.status, 'in_use')
            self.assertEqual(result.location, 'Server Room A')
    
    def test_delete_equipment(self):
        """Тест удаления оборудования"""
        with self.app.app_context():
            equipment = Equipment(
                name='To Delete',
                model='Model',
                manufacturer='Manuf',
                serial_number='SN-DELETE-001',
                category='router'
            )
            db.session.add(equipment)
            db.session.commit()
            
            eq_id = equipment.id
            db.session.delete(equipment)
            db.session.commit()
            
            result = Equipment.query.filter_by(id=eq_id).first()
            self.assertIsNone(result)
    
    # ==================== Тесты модели Document ====================
    
    def test_create_document(self):
        """Тест создания документа"""
        with self.app.app_context():
            equipment = Equipment(
                name='Test Device',
                model='Model',
                manufacturer='Manuf',
                serial_number='SN-DOC-001',
                category='router'
            )
            db.session.add(equipment)
            db.session.commit()
            
            document = Document(
                equipment_id=equipment.id,
                filename='20260101_120000_test.pdf',
                original_filename='test.pdf',
                document_type='invoice'
            )
            db.session.add(document)
            db.session.commit()
            
            result = Document.query.filter_by(original_filename='test.pdf').first()
            
            self.assertIsNotNone(result)
            self.assertEqual(result.equipment_id, equipment.id)
            self.assertEqual(result.document_type, 'invoice')
    
    def test_document_relationship(self):
        """Тест связи оборудования с документами"""
        with self.app.app_context():
            equipment = Equipment(
                name='Device with Docs',
                model='Model',
                manufacturer='Manuf',
                serial_number='SN-REL-001',
                category='server'
            )
            db.session.add(equipment)
            db.session.commit()
            
            doc1 = Document(
                equipment_id=equipment.id,
                filename='doc1.pdf',
                original_filename='manual.pdf',
                document_type='manual'
            )
            doc2 = Document(
                equipment_id=equipment.id,
                filename='doc2.pdf',
                original_filename='warranty.pdf',
                document_type='warranty'
            )
            db.session.add(doc1)
            db.session.add(doc2)
            db.session.commit()
            
            result = Equipment.query.filter_by(id=equipment.id).first()
            
            self.assertEqual(len(result.documents), 2)
            self.assertEqual(result.documents[0].document_type, 'manual')
            self.assertEqual(result.documents[1].document_type, 'warranty')
    
    def test_delete_equipment_cascades_documents(self):
        """Тест каскадного удаления документов при удалении оборудования"""
        with self.app.app_context():
            equipment = Equipment(
                name='Cascade Test',
                model='Model',
                manufacturer='Manuf',
                serial_number='SN-CASCADE-001',
                category='router'
            )
            db.session.add(equipment)
            db.session.commit()
            
            document = Document(
                equipment_id=equipment.id,
                filename='doc.pdf',
                original_filename='doc.pdf',
                document_type='other'
            )
            db.session.add(document)
            db.session.commit()
            
            doc_id = document.id
            eq_id = equipment.id
            
            db.session.delete(equipment)
            db.session.commit()
            
            deleted_doc = Document.query.filter_by(id=doc_id).first()
            deleted_eq = Equipment.query.filter_by(id=eq_id).first()
            
            self.assertIsNone(deleted_eq)
            self.assertIsNone(deleted_doc)
    
    # ==================== Тесты API/Маршрутов ====================
    
    def test_index_page_loads(self):
        """Тест загрузки главной страницы"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'navbar', response.data)
        self.assertIn(b'hdd-network', response.data)
    
    def test_add_equipment_page_loads(self):
        """Тест загрузки страницы добавления оборудования"""
        response = self.client.get('/add')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'form', response.data)
        self.assertIn(b'serial_number', response.data)
    
    def test_add_equipment_success(self):
        """Тест успешного добавления оборудования через форму"""
        data = {
            'name': 'API Test Router',
            'model': 'Test Model',
            'manufacturer': 'Test Manufacturer',
            'serial_number': 'SN-API-001',
            'category': 'router',
            'quantity': 3,
            'status': 'available'
        }
        
        response = self.client.post('/add', data=data, follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'success', response.data)
        
        with self.app.app_context():
            equipment = Equipment.query.filter_by(serial_number='SN-API-001').first()
            self.assertIsNotNone(equipment)
            self.assertEqual(equipment.name, 'API Test Router')
    
    def test_view_equipment_page(self):
        """Тест просмотра карточки оборудования"""
        with self.app.app_context():
            equipment = Equipment(
                name='View Test',
                model='Model View',
                manufacturer='Manuf View',
                serial_number='SN-VIEW-001',
                category='switch',
                speed=10000.0,
                quantity=2,
                status='available'
            )
            db.session.add(equipment)
            db.session.commit()
            
            eq_id = equipment.id
        
        response = self.client.get(f'/equipment/{eq_id}')
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'View Test', response.data)
        self.assertIn(b'Model View', response.data)
    
    def test_edit_equipment_page(self):
        """Тест загрузки страницы редактирования"""
        with self.app.app_context():
            equipment = Equipment(
                name='Edit Test',
                model='Model Edit',
                manufacturer='Manuf Edit',
                serial_number='SN-EDIT-001',
                category='server'
            )
            db.session.add(equipment)
            db.session.commit()
            
            eq_id = equipment.id
        
        response = self.client.get(f'/equipment/{eq_id}/edit')
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Edit', response.data)
    
    def test_edit_equipment_success(self):
        """Тест успешного редактирования оборудования"""
        with self.app.app_context():
            equipment = Equipment(
                name='Before Edit',
                model='Before Model',
                manufacturer='Before Manuf',
                serial_number='SN-EDIT-002',
                category='router',
                quantity=1,
                status='available'
            )
            db.session.add(equipment)
            db.session.commit()
            
            eq_id = equipment.id
        
        data = {
            'name': 'After Edit',
            'model': 'After Model',
            'manufacturer': 'After Manuf',
            'serial_number': 'SN-EDIT-002',
            'category': 'switch',
            'quantity': 5,
            'status': 'in_use',
            'location': 'New Location'
        }
        
        response = self.client.post(f'/equipment/{eq_id}/edit', data=data, follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'success', response.data)
        
        with self.app.app_context():
            updated = Equipment.query.filter_by(id=eq_id).first()
            self.assertEqual(updated.name, 'After Edit')
            self.assertEqual(updated.category, 'switch')
            self.assertEqual(updated.quantity, 5)
            self.assertEqual(updated.status, 'in_use')
            self.assertEqual(updated.location, 'New Location')
    
    def test_delete_equipment_success(self):
        """Тест успешного удаления оборудования"""
        with self.app.app_context():
            equipment = Equipment(
                name='Delete Test',
                model='Model Del',
                manufacturer='Manuf Del',
                serial_number='SN-DEL-001',
                category='router'
            )
            db.session.add(equipment)
            db.session.commit()
            
            eq_id = equipment.id
        
        response = self.client.post(f'/equipment/{eq_id}/delete', follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'success', response.data)
        
        with self.app.app_context():
            deleted = Equipment.query.filter_by(id=eq_id).first()
            self.assertIsNone(deleted)
    
    def test_search_functionality(self):
        """Тест поиска оборудования"""
        with self.app.app_context():
            eq1 = Equipment(
                name='Cisco Router',
                model='ISR 4000',
                manufacturer='Cisco',
                serial_number='SN-SEARCH-001',
                category='router',
                status='available'
            )
            eq2 = Equipment(
                name='HP Switch',
                model='ProCurve 2920',
                manufacturer='HP',
                serial_number='SN-SEARCH-002',
                category='switch',
                status='in_use'
            )
            eq3 = Equipment(
                name='Dell Server',
                model='PowerEdge R740',
                manufacturer='Dell',
                serial_number='SN-SEARCH-003',
                category='server',
                status='available'
            )
            db.session.add(eq1)
            db.session.add(eq2)
            db.session.add(eq3)
            db.session.commit()
        
        # Поиск по названию
        response = self.client.get('/?search_query=Cisco')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Cisco Router', response.data)
        self.assertNotIn(b'HP Switch', response.data)
        
        # Поиск по категории
        response = self.client.get('/?category=switch')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'HP Switch', response.data)
        self.assertNotIn(b'Cisco Router', response.data)
        
        # Поиск по статусу
        response = self.client.get('/?status=available')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Cisco Router', response.data)
        self.assertIn(b'Dell Server', response.data)
        self.assertNotIn(b'HP Switch', response.data)
    
    def test_statistics_on_index(self):
        """Тест статистики на главной странице"""
        with self.app.app_context():
            eq1 = Equipment(
                name='Device 1',
                model='Model 1',
                manufacturer='Manuf 1',
                serial_number='SN-STAT-001',
                category='router',
                quantity=5,
                status='available'
            )
            eq2 = Equipment(
                name='Device 2',
                model='Model 2',
                manufacturer='Manuf 2',
                serial_number='SN-STAT-002',
                category='switch',
                quantity=3,
                status='in_use'
            )
            eq3 = Equipment(
                name='Device 3',
                model='Model 3',
                manufacturer='Manuf 3',
                serial_number='SN-STAT-003',
                category='server',
                quantity=2,
                status='available'
            )
            db.session.add(eq1)
            db.session.add(eq2)
            db.session.add(eq3)
            db.session.commit()
        
        response = self.client.get('/')
        
        self.assertEqual(response.status_code, 200)
        # Проверяем наличие статистики (число моделей = 3, всего единиц = 10)
        self.assertIn(b'>3<', response.data)  # Число моделей
        self.assertIn(b'>10<', response.data)  # Всего единиц
    
    def test_upload_document_success(self):
        """Тест успешной загрузки документа"""
        with self.app.app_context():
            equipment = Equipment(
                name='Doc Upload Test',
                model='Model',
                manufacturer='Manuf',
                serial_number='SN-UPLOAD-001',
                category='router'
            )
            db.session.add(equipment)
            db.session.commit()
            
            eq_id = equipment.id
        
        # Создаем тестовый файл
        temp_file = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
        temp_file.write(b'Test PDF content')
        temp_file.close()
        
        with open(temp_file.name, 'rb') as f:
            data = {
                'document': (f, 'test_document.pdf'),
                'document_type': 'invoice'
            }
            
            response = self.client.post(f'/equipment/{eq_id}/upload', 
                                       data=data, 
                                       content_type='multipart/form-data',
                                       follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'success', response.data)
        
        # Очищаем временный файл
        os.unlink(temp_file.name)
        
        with self.app.app_context():
            document = Document.query.filter_by(original_filename='test_document.pdf').first()
            self.assertIsNotNone(document)
            self.assertEqual(document.equipment_id, eq_id)
    
    def test_delete_document(self):
        """Тест удаления документа"""
        with self.app.app_context():
            equipment = Equipment(
                name='Delete Doc Test',
                model='Model',
                manufacturer='Manuf',
                serial_number='SN-DELDOC-001',
                category='router'
            )
            db.session.add(equipment)
            db.session.commit()
            
            eq_id = equipment.id
            
            # Создаем тестовый файл
            test_filename = '20260101_120000_delete_test.pdf'
            filepath = os.path.join(self.app.config['UPLOAD_FOLDER'], test_filename)
            with open(filepath, 'wb') as f:
                f.write(b'To be deleted')
            
            document = Document(
                equipment_id=eq_id,
                filename=test_filename,
                original_filename='delete_test.pdf',
                document_type='other'
            )
            db.session.add(document)
            db.session.commit()
            
            doc_id = document.id
        
        response = self.client.post(f'/equipment/{eq_id}/document/{doc_id}/delete', 
                                   follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'success', response.data)
        
        with self.app.app_context():
            deleted_doc = Document.query.filter_by(id=doc_id).first()
            self.assertIsNone(deleted_doc)
        
        # Файл также должен быть удален
        self.assertFalse(os.path.exists(filepath))
    
    def test_form_validation_required_fields(self):
        """Тест валидации обязательных полей формы"""
        # Пустая форма
        response = self.client.post('/add', data={}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        # Форма должна вернуть ошибку валидации
    
    def test_categories_and_statuses(self):
        """Тест доступных категорий и статусов"""
        response = self.client.get('/add')
        self.assertEqual(response.status_code, 200)
        
        # Проверяем наличие категорий
        categories = [b'router', b'switch', b'server', b'storage', b'firewall', b'other']
        for cat in categories:
            self.assertIn(cat, response.data)
        
        # Проверяем наличие статусов
        statuses = [b'available', b'in_use', b'maintenance', b'retired']
        for status in statuses:
            self.assertIn(status, response.data)


class TestEquipmentModelEdgeCases(unittest.TestCase):
    """Тесты граничных случаев для модели оборудования"""
    
    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['WTF_CSRF_ENABLED'] = False
        
        with self.app.app_context():
            db.create_all()
    
    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
    
    def test_zero_quantity(self):
        """Тест оборудования с нулевым количеством"""
        with self.app.app_context():
            equipment = Equipment(
                name='Zero Qty',
                model='Model',
                manufacturer='Manuf',
                serial_number='SN-ZERO-001',
                category='router',
                quantity=0
            )
            db.session.add(equipment)
            db.session.commit()
            
            self.assertEqual(equipment.quantity, 0)
    
    def test_large_quantity(self):
        """Тест оборудования с большим количеством"""
        with self.app.app_context():
            equipment = Equipment(
                name='Large Qty',
                model='Model',
                manufacturer='Manuf',
                serial_number='SN-LARGE-001',
                category='router',
                quantity=999999
            )
            db.session.add(equipment)
            db.session.commit()
            
            self.assertEqual(equipment.quantity, 999999)
    
    def test_all_status_values(self):
        """Тест всех возможных значений статуса"""
        statuses = ['available', 'in_use', 'maintenance', 'retired']
        
        with self.app.app_context():
            for i, status in enumerate(statuses):
                equipment = Equipment(
                    name=f'Status Test {i}',
                    model='Model',
                    manufacturer='Manuf',
                    serial_number=f'SN-STATUS-{i:03d}',
                    category='router',
                    status=status
                )
                db.session.add(equipment)
            
            db.session.commit()
            
            for i, status in enumerate(statuses):
                eq = Equipment.query.filter_by(serial_number=f'SN-STATUS-{i:03d}').first()
                self.assertEqual(eq.status, status)
    
    def test_float_precision(self):
        """Тест точности дробных чисел"""
        with self.app.app_context():
            equipment = Equipment(
                name='Float Test',
                model='Model',
                manufacturer='Manuf',
                serial_number='SN-FLOAT-001',
                category='router',
                speed=1000.123456,
                bandwidth=10.987654,
                power_consumption=250.555,
                width=482.6,
                height=44.45,
                depth=300.0,
                weight=2.345
            )
            db.session.add(equipment)
            db.session.commit()
            
            result = Equipment.query.filter_by(serial_number='SN-FLOAT-001').first()
            
            self.assertAlmostEqual(result.speed, 1000.123456, places=5)
            self.assertAlmostEqual(result.bandwidth, 10.987654, places=5)
            self.assertAlmostEqual(result.power_consumption, 250.555, places=5)


if __name__ == '__main__':
    unittest.main(verbosity=2)
