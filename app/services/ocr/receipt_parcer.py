# app/services/ocr/receipt_parser.py
from datetime import datetime
import re
from typing import Dict, Any


class ReceiptParser:
    @staticmethod
    def parse_text(text: str) -> Dict[str, Any]:
        """Parse extracted text to find receipt details."""
        patterns = {
            'date': r'\b(\d{2}\.\d{2}\.\d{4})\b',
            'amount': r'\b(\d+[\.,]\d{2})\b',
            'operation_number': r'\bОперация[:\s]+([A-Z0-9]+)\b',
            'sender': r'От кого:?\s+([^\n]+)',
            'receiver': r'Получатель:?\s+([^\n]+)',
            'organization': r'Организация:?\s+([^\n]+)'
        }

        result = {}

        # Extract date
        date_match = re.search(patterns['date'], text)
        if date_match:
            try:
                # Сохраняем как datetime объект
                result['date'] = datetime.strptime(date_match.group(1), '%d.%m.%Y')
            except ValueError:
                result['date'] = None

        # Extract amount
        amount_match = re.search(patterns['amount'], text)
        if amount_match:
            try:
                result['amount'] = float(
                    amount_match.group(1).replace(',', '.')
                )
            except ValueError:
                result['amount'] = None

        # Extract other fields
        for field, pattern in patterns.items():
            if field in ['date', 'amount']:
                continue
            match = re.search(pattern, text)
            if match:
                result[field] = match.group(1).strip()
            else:
                result[field] = None

        # Add raw text for debugging
        result['raw_text'] = text

        return result
