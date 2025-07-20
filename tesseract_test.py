#Usage: python tesseract_test.py <filename>

import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import pdfplumber
import re
import sys
from pathlib import Path
import io

# Функция для предварительной обработки изображения перед OCR с использованием только PIL
def preprocess_image(image):
    # Преобразуем в оттенки серого
    image = image.convert('L')
    
    # Увеличиваем контраст
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(2.0)
    
    # Увеличиваем резкость
    image = image.filter(ImageFilter.SHARPEN)
    
    # Применяем фильтр для удаления шума
    image = image.filter(ImageFilter.MedianFilter(3))
    
    return image

# Function to extract transaction details
def extract_transaction_details(text):
    # Словарь для хранения всех извлеченных данных
    extracted_data = {}
    
    # Определение банка
    if "Алиф" in text:
        bank_type = "Алиф Банк"
    elif "Душанбе Сити" in text or "DUSHANBE" in text:
        bank_type = "Душанбе Сити Банк"
    else:
        bank_type = "Неизвестный банк"
    
    # Извлечение даты и времени
    date_match = re.search(r"(?:Дата и время:|Дата операции:)\s*\n?\s*(\d{2}\.\d{2}\.\d{4})", text)
    time_match = re.search(r"(?:Дата и время:.*?|Время операции:)\s*\n?\s*(\d{2}:\d{2}(?::\d{2})?)", text)
    
    # Формирование поля datetime
    if date_match and time_match:
        extracted_data["datetime"] = f"{date_match.group(1)} {time_match.group(1)}"
    elif date_match:
        extracted_data["datetime"] = date_match.group(1)
    elif time_match:
        extracted_data["datetime"] = time_match.group(1)
    else:
        extracted_data["datetime"] = ""
    
    # Извлечение суммы операции
    amount_match = re.search(r"(?:Сумма|Сумма операции:|Итого)\s*\n?\s*([\d,.]+)\s*(?:с\.|сомони)?", text)
    if amount_match:
        extracted_data["amount"] = amount_match.group(1).strip()
    else:
        extracted_data["amount"] = ""
    
    # Извлечение номера операции
    operation_number_match = re.search(r"(?:Номер транзакции|Номер операции:)\s*\n?\s*([0-9/]+)", text)
    if operation_number_match:
        extracted_data["operation_number"] = operation_number_match.group(1)
    else:
        extracted_data["operation_number"] = ""
    
    # Извлечение отправителя
    sender_match = re.search(r"(?:Счет отправителя:|Способ оплаты)\s*\n?\s*([0-9*]+\S*)", text)
    if sender_match:
        extracted_data["sender"] = sender_match.group(1).strip()
    else:
        extracted_data["sender"] = ""
    
    # Извлечение получателя (разная логика для разных банков)
    if bank_type == "Алиф Банк":
        # Для Алиф Банка получатель - это ФИО
        recipient_match = re.search(r"Перевод на счёт\s*\n?\s*([^\n]+)", text)
        if recipient_match:
            # Удаляем слово "слуга" из имени получателя
            recipient_name = recipient_match.group(1).strip()
            recipient_name = recipient_name.replace("слуга", "").strip()
            extracted_data["receiver"] = recipient_name
        else:
            extracted_data["receiver"] = ""
    else:
        # Для Душанбе Сити получатель - это номер телефона
        receiver_match = re.search(r"(?:Счет получателя:|Счёт зачисления)\s*\n?\s*(992\d+)", text)
        if receiver_match:
            extracted_data["receiver"] = receiver_match.group(1).strip()
        else:
            extracted_data["receiver"] = ""
    
    # Извлечение статуса операции
    status_match = re.search(r"(?:Статус:\s*\n?\s*|ЭЛЕКТРОННЫЙ ПЛАТЕЖ\s*\n?\s*)(ИСПОЛНЕНО|ВЫПОЛНЕНА|Успешный)", text, re.IGNORECASE)
    if status_match:
        extracted_data["status"] = status_match.group(1).strip()
    else:
        extracted_data["status"] = ""
    
    # Извлечение примечаний (если есть)
    notes_match = re.search(r"(?:Примечание|Назначение платежа):\s*\n?\s*([^\n]+)", text)
    if notes_match:
        extracted_data["notes"] = notes_match.group(1).strip()
    else:
        extracted_data["notes"] = ""
    
    # Извлечение организации
    org_match = re.search(r"(?:ЗАО|ОАО)\s+\"([^\"]+)\"", text)
    if org_match:
        extracted_data["organization"] = org_match.group(1).strip()
    else:
        extracted_data["organization"] = bank_type
    
    # Извлечение комиссии (если есть)
    fee_match = re.search(r"(?:Комиссия)\s*\n?\s*([^\n]+)", text)
    if fee_match:
        fee_value = fee_match.group(1).strip()
        # Удаляем "с." из значения комиссии
        fee_value = re.sub(r'\s*с\.', '', fee_value).strip()
        
        # Проверяем, равна ли комиссия нулю или букве "О"
        if "0" in fee_value or "0.00" in fee_value or fee_value == "О" or fee_value == "о":
            extracted_data["fee"] = "0"
        else:
            extracted_data["fee"] = fee_value
    else:
        # Если поле комиссии отсутствует, устанавливаем значение "0"
        extracted_data["fee"] = "0"
    
    # Формирование результата в заданном порядке
    result = {
        "datetime": extracted_data["datetime"],
        "amount": extracted_data["amount"],
        "operation_number": extracted_data["operation_number"],
        "sender": extracted_data["sender"],
        "receiver": extracted_data["receiver"],
        "status": extracted_data["status"],
        "notes": extracted_data["notes"],
        "organization": extracted_data["organization"],
        "fee": extracted_data["fee"]
    }
    
    return result


# Function to extract text from an image
def extract_text_from_image(image_path):
    try:
        image = Image.open(image_path)
        
        # Предварительная обработка изображения
        processed_image = preprocess_image(image)
        
        # Используем различные конфигурации OCR для улучшения результата
        custom_config = r'--oem 3 --psm 6 -l rus'  # PSM 6: Предполагаем, что это единый блок текста
        text = pytesseract.image_to_string(processed_image, config=custom_config)
        
        # Если результат плохой, попробуем другой режим сегментации
        if not text.strip() or len(text) < 50:
            custom_config = r'--oem 3 --psm 4 -l rus'  # PSM 4: Предполагаем, что это одна колонка текста
            text = pytesseract.image_to_string(processed_image, config=custom_config)
        
        # Если всё ещё плохо, попробуем без предварительной обработки
        if not text.strip() or len(text) < 50:
            custom_config = r'--oem 3 --psm 1 -l rus'  # PSM 1: Автоматическая сегментация страницы
            text = pytesseract.image_to_string(image, config=custom_config)
        
        return text
    except Exception as e:
        print(f"Error processing image {image_path}: {e}")
        return ""

def extract_text_from_pdf(pdf_path):
    try:
        # Сначала попробуем обычный метод с pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        
        # Если текст не извлечен или слишком короткий, попробуем OCR с PyMuPDF
        if not text.strip() or len(text) < 50:
            try:
                import fitz  # PyMuPDF
                
                pdf_document = fitz.open(pdf_path)
                text = ""
                
                for page_num in range(len(pdf_document)):
                    page = pdf_document.load_page(page_num)
                    # Увеличиваем разрешение для лучшего OCR
                    pix = page.get_pixmap(matrix=fitz.Matrix(3, 3))
                    
                    # Преобразуем pixmap в изображение PIL
                    img_data = pix.tobytes("png")
                    img = Image.open(io.BytesIO(img_data))
                    
                    # Предварительная обработка изображения
                    processed_img = preprocess_image(img)
                    
                    # Применяем OCR к изображению с разными параметрами
                    custom_config = r'--oem 3 --psm 6 -l rus'
                    page_text = pytesseract.image_to_string(processed_img, config=custom_config)
                    
                    # Если результат плохой, попробуем другой режим
                    if not page_text.strip() or len(page_text) < 50:
                        custom_config = r'--oem 3 --psm 1 -l rus'
                        page_text = pytesseract.image_to_string(processed_img, config=custom_config)
                    
                    text += page_text + "\n"
                
                pdf_document.close()
            except ImportError:
                print("PyMuPDF не установлен. Установите его с помощью: pip install PyMuPDF")
                return ""
            except Exception as e:
                print(f"Error using PyMuPDF for OCR: {e}")
                return ""
        
        return text
    except Exception as e:
        print(f"Error processing PDF {pdf_path}: {e}")
        return ""

# Дополнительная функция для разделения изображения на две части и обработки каждой отдельно
def extract_text_with_column_splitting(image):
    width, height = image.size
    
    # Разделяем изображение на две части
    left_half = image.crop((0, 0, width // 2, height))
    right_half = image.crop((width // 2, 0, width, height))
    
    # Обрабатываем каждую половину
    left_half_processed = preprocess_image(left_half)
    right_half_processed = preprocess_image(right_half)
    
    # OCR для каждой половины
    custom_config = r'--oem 3 --psm 6 -l rus'
    left_text = pytesseract.image_to_string(left_half_processed, config=custom_config)
    right_text = pytesseract.image_to_string(right_half_processed, config=custom_config)
    
    # Объединяем результаты в один текст
    combined_text = ""
    
    # Разбиваем текст на строки
    left_lines = left_text.split('\n')
    right_lines = right_text.split('\n')
    
    # Объединяем строки из левой и правой частей
    max_lines = max(len(left_lines), len(right_lines))
    for i in range(max_lines):
        left_line = left_lines[i] if i < len(left_lines) else ""
        right_line = right_lines[i] if i < len(right_lines) else ""
        
        # Если строка не пустая, добавляем ее
        if left_line.strip():
            combined_text += left_line + " "
        if right_line.strip():
            combined_text += right_line
        
        combined_text += "\n"
    
    return combined_text

def process_file(file_path):
    file_path = Path(file_path)
    
    if not file_path.exists():
        # Check if file exists in test_files directory
        test_file_path = Path("test_files") / file_path.name
        if test_file_path.exists():
            file_path = test_file_path
        else:
            print(f"Error: File {file_path} not found")
            return
    
    extension = file_path.suffix.lower()
    
    if extension in ['.jpg', '.jpeg', '.png']:
        text = extract_text_from_image(file_path)
    elif extension == '.pdf':
        text = extract_text_from_pdf(file_path)
    else:
        print(f"Unsupported file format: {extension}")
        return
    
    if not text or len(text) < 50:
        print("Стандартный OCR не дал хороших результатов. Пробуем разделение на колонки...")
        try:
            # Если это PDF, сначала преобразуем его в изображение
            if extension == '.pdf':
                import fitz
                pdf_document = fitz.open(file_path)
                page = pdf_document.load_page(0)
                pix = page.get_pixmap(matrix=fitz.Matrix(3, 3))
                img_data = pix.tobytes("png")
                image = Image.open(io.BytesIO(img_data))
                pdf_document.close()
            else:
                image = Image.open(file_path)
            
            # Применяем метод разделения на колонки
            text = extract_text_with_column_splitting(image)
        except Exception as e:
            print(f"Error with column splitting approach: {e}")
    
    if not text:
        print("No text extracted from the file.")
        return
    
    transaction_details = extract_transaction_details(text)
    
    # Вывод только деталей транзакции без дополнительного форматирования
    if transaction_details:
        print("\nНайденные детали транзакции:")
        for key, value in transaction_details.items():
            print(f"{key}: {value}")
    else:
        print("No transaction details found.")

def main():
    if len(sys.argv) < 2:
        print("Usage: python tesseract_test.py <filename>")
        return
    
    file_path = sys.argv[1]
    process_file(file_path)

if __name__ == "__main__":
    main()
