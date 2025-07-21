# app/services/ocr/ocr_service.py
from pathlib import Path
from typing import Dict, Any
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import pdfplumber
import io
import re

from app.services.ocr.receipt_parcer import ReceiptParser


# app/services/ocr/exceptions.py
class OCRProcessingError(Exception):
    """Raised when OCR processing fails."""
    pass


class OCRService:
    def __init__(self):
        self.parser = ReceiptParser()

    async def process_document(self, file_path: Path) -> Dict[str, Any]:
        """Process document based on file type."""
        if file_path.suffix.lower() == '.pdf':
            text = await self.process_pdf(file_path)
            
            # Если текст не извлечен или слишком короткий, пробуем альтернативный метод
            if not text or len(text) < 50:
                text = await self._extract_text_from_pdf_alternative(file_path)
                
            return self.parser.parse_text(text)
        else:
            text = await self.process_image(file_path)
            
            # Если текст не извлечен или слишком короткий, пробуем альтернативный метод
            if not text or len(text) < 50:
                text = await self._extract_text_from_image_alternative(file_path)
                
            return self.parser.parse_text(text)

    async def process_pdf(self, file_path: Path) -> str:
        """Extract text from PDF."""
        try:
            with pdfplumber.open(file_path) as pdf:
                text = ""
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            return text
        except Exception as e:
            raise OCRProcessingError(f"Error processing PDF: {str(e)}")

    async def process_image(self, file_path: Path) -> str:
        """Extract text from image."""
        try:
            image = Image.open(file_path)
            
            # Предварительная обработка изображения
            processed_image = await self._preprocess_image(image)
            
            # Используем различные конфигурации OCR для улучшения результата
            custom_config = r'--oem 3 --psm 6 -l rus+eng'  # PSM 6: Предполагаем, что это единый блок текста
            text = pytesseract.image_to_string(processed_image, config=custom_config)
            
            # Если результат плохой, попробуем другой режим сегментации
            if not text.strip() or len(text) < 50:
                custom_config = r'--oem 3 --psm 4 -l rus+eng'  # PSM 4: Предполагаем, что это одна колонка текста
                text = pytesseract.image_to_string(processed_image, config=custom_config)
            
            # Если всё ещё плохо, попробуем без предварительной обработки
            if not text.strip() or len(text) < 50:
                custom_config = r'--oem 3 --psm 1 -l rus+eng'  # PSM 1: Автоматическая сегментация страницы
                text = pytesseract.image_to_string(image, config=custom_config)
            
            return text
        except Exception as e:
            raise OCRProcessingError(f"Error processing image: {str(e)}")
    
    async def _preprocess_image(self, image):
        """Предварительная обработка изображения перед OCR."""
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
    
    async def _extract_text_from_image_alternative(self, image_path: Path) -> str:
        """Альтернативный метод извлечения текста из изображения."""
        try:
            image = Image.open(image_path)
            width, height = image.size
            
            # Разделяем изображение на две части
            left_half = image.crop((0, 0, width // 2, height))
            right_half = image.crop((width // 2, 0, width, height))
            
            # Обрабатываем каждую половину
            left_half_processed = await self._preprocess_image(left_half)
            right_half_processed = await self._preprocess_image(right_half)
            
            # OCR для каждой половины
            custom_config = r'--oem 3 --psm 6 -l rus+eng'
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
        except Exception as e:
            raise OCRProcessingError(f"Error with alternative image processing: {str(e)}")
    
    async def _extract_text_from_pdf_alternative(self, pdf_path: Path) -> str:
        """Альтернативный метод извлечения текста из PDF с использованием OCR."""
        try:
            # Пробуем импортировать PyMuPDF
            try:
                import fitz  # PyMuPDF
            except ImportError:
                # Если PyMuPDF не установлен, возвращаем пустую строку
                return ""
            
            pdf_document = fitz.open(str(pdf_path))
            text = ""
            
            for page_num in range(len(pdf_document)):
                page = pdf_document.load_page(page_num)
                # Увеличиваем разрешение для лучшего OCR
                pix = page.get_pixmap(matrix=fitz.Matrix(3, 3))
                
                # Преобразуем pixmap в изображение PIL
                img_data = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_data))
                
                # Предварительная обработка изображения
                processed_img = await self._preprocess_image(img)
                
                # Применяем OCR к изображению с разными параметрами
                custom_config = r'--oem 3 --psm 6 -l rus+eng'
                page_text = pytesseract.image_to_string(processed_img, config=custom_config)
                
                # Если результат плохой, попробуем другой режим
                if not page_text.strip() or len(page_text) < 50:
                    custom_config = r'--oem 3 --psm 1 -l rus+eng'
                    page_text = pytesseract.image_to_string(processed_img, config=custom_config)
                
                text += page_text + "\n"
            
            pdf_document.close()
            return text
        except Exception as e:
            # В случае ошибки возвращаем пустую строку, чтобы не прерывать основной процесс
            return ""
