import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import pdfplumber
import re
import sys
import os
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
    details = {}

    # Сначала выведем текст для отладки
    print("Извлеченный текст:")
    print("----------------------------")
    print(text)
    print("----------------------------")

    # Улучшенные регулярные выражения с учетом формата
    transaction_id_match = re.search(r"(?:Номер транзакции)\s*\n?\s*(\d+)", text)
    
    date_match = re.search(r"(?:Дата и время:)\s*\n?\s*(\d{2}\.\d{2}\.\d{4}\s+\d{2}:\d{2})", text)
    
    # Ищем сумму
    amount_match = re.search(r"(?:Сумма|Итого)\s*\n?\s*([\d,.]+)\s*с\.", text)
    
    # Ищем счет зачисления
    account_match = re.search(r"(?:Счёт зачисления)\s*\n?\s*(\+?\d+)", text)
    
    # Ищем способ оплаты (карту)
    card_match = re.search(r"(?:Способ оплаты)\s*\n?\s*(\d+\*+\w+\*+\d+)", text)
    
    # Ищем статус операции
    status_match = re.search(r"(ИСПОЛНЕНО|ВЫПОЛНЕНО|Успешно)", text, re.IGNORECASE)
    
    # Ищем название банка
    bank_match = re.search(r"ОАО\s*«([^»]+)»", text)
    
    # Ищем имя получателя
    recipient_match = re.search(r"(?:Перевод на счёт)\s*\n?\s*([^\n]+)", text)
    
    # Ищем комиссию
    commission_match = re.search(r"(?:Комиссия)\s*\n?\s*(\d+\s*с\.)", text)
    
    # Ищем БИК
    bik_match = re.search(r"(?:БИК:)\s*(\d+)", text)
    
    # Ищем ИНН
    inn_match = re.search(r"(?:ИНН:)\s*(\d+)", text)

    if transaction_id_match:
        details["transaction_id"] = transaction_id_match.group(1)
    if date_match:
        details["datetime"] = date_match.group(1)
    if amount_match:
        details["amount"] = amount_match.group(1) + " с."
    if account_match:
        details["account"] = account_match.group(1)
    if card_match:
        details["card"] = card_match.group(1)
    if status_match:
        details["status"] = status_match.group(1)
    if bank_match:
        details["bank"] = bank_match.group(1).strip()
    if recipient_match:
        details["recipient"] = recipient_match.group(1).strip()
    if commission_match:
        details["commission"] = commission_match.group(1)
    if bik_match:
        details["bik"] = bik_match.group(1)
    if inn_match:
        details["inn"] = inn_match.group(1)

    # Если не нашли сумму стандартным способом, попробуем альтернативный подход
    if "amount" not in details:
        # Ищем "25 с." после "Итого"
        alt_amount_match = re.search(r"Итого\s*\n\s*([\d,.]+)\s*с\.", text)
        if alt_amount_match:
            details["amount"] = alt_amount_match.group(1) + " с."
        else:
            # Ищем любое число с "с." после него
            any_amount_match = re.search(r"(\d+)\s*с\.", text)
            if any_amount_match:
                details["amount"] = any_amount_match.group(1) + " с."

    return details

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
