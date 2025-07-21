from datetime import datetime
import re
from typing import Dict, Any


class ReceiptParser:
    def parse_text(self, text: str) -> Dict[str, Any]:
        """Parse extracted text to find receipt details."""
        # Словарь для хранения всех извлеченных данных
        result = {}
        
        # Определение банка
        if "Алиф" in text or "alif" in text.lower():
            bank_type = "Алиф Банк"
        elif "Душанбе Сити" in text or "DUSHANBE" in text:
            bank_type = "Душанбе Сити Банк"
        else:
            bank_type = "Неизвестный банк"
        
        result['bank_type'] = bank_type
        
        # Специфическая обработка для Душанбе Сити Банка
        if bank_type == "Душанбе Сити Банк":
            # Извлечение даты и времени
            date_match = re.search(r"Дата операции:\s*\n?\s*(\d{2}\.\d{2}\.\d{4})", text)
            time_match = re.search(r"Время операции:\s*\n?\s*(\d{2}:\d{2}:\d{2})", text)
            
            if date_match and time_match:
                try:
                    date_str = date_match.group(1)
                    time_str = time_match.group(1)
                    result['date'] = datetime.strptime(f"{date_str} {time_str}", '%d.%m.%Y %H:%M:%S')
                except ValueError:
                    result['date'] = None
            
            # Извлечение номера операции
            operation_number_match = re.search(r"Номер операции:\s*\n?\s*([0-9/]+)", text)
            if operation_number_match:
                result['operation_number'] = operation_number_match.group(1).strip()
            
            # Извлечение поставщика
            provider_match = re.search(r"Поставщик:\s*\n?\s*([^\n]+)", text)
            if provider_match:
                result['provider'] = provider_match.group(1).strip()
            
            # Извлечение счета отправителя
            sender_match = re.search(r"Счет отправителя:\s*\n?\s*([^\n]+)", text)
            if sender_match:
                result['sender'] = sender_match.group(1).strip()
            
            # Извлечение счета получателя
            receiver_match = re.search(r"Счет получателя:\s*\n?\s*([^\n]+)", text)
            if receiver_match:
                result['receiver'] = receiver_match.group(1).strip()
            
            # Извлечение суммы операции
            amount_match = re.search(r"Сумма операции:\s*\n?\s*([\d,.]+)", text)
            if amount_match:
                try:
                    amount_str = amount_match.group(1).strip()
                    amount_str = re.sub(r'[^\d.,]', '', amount_str)
                    amount_str = amount_str.replace(',', '.')
                    result['amount'] = float(amount_str)
                except (ValueError, IndexError):
                    result['amount'] = None
            
            # Извлечение статуса операции
            status_match = re.search(r"Статус:\s*\n?\s*([^\n]+)", text)
            if status_match:
                result['status'] = status_match.group(1).strip()
            else:
                # Альтернативный поиск - ищем "ОПЕРАЦИЯ ВЫПОЛНЕНА"
                alt_status_match = re.search(r"ОПЕРАЦИЯ ВЫПОЛНЕНА", text)
                if alt_status_match:
                    result['status'] = "ВЫПОЛНЕНА"
            
            # Извлечение организации
            org_match = re.search(r"ЗАО \"([^\"]+)\"", text)
            if org_match:
                result['organization'] = org_match.group(1).strip()
            else:
                result['organization'] = "Душанбе Сити Банк"
            
            # Комиссия (обычно отсутствует в чеках Душанбе Сити)
            result['fee'] = "0"
            
        else:  # Обработка для Алиф Банка и других банков
            # Извлечение даты и времени
            date_match = re.search(r"(?:Дата и время:|Дата операции:)\s*\n?\s*(\d{2}\.\d{2}\.\d{4})", text)
            time_match = re.search(r"(?:Дата и время:.*?|Время операции:)\s*\n?\s*(\d{2}:\d{2}(?::\d{2})?)", text)
            
            # Обработка даты
            if date_match:
                try:
                    # Сохраняем как datetime объект
                    date_str = date_match.group(1)
                    # Проверяем, есть ли время в строке с датой
                    if time_match:
                        time_str = time_match.group(1)
                        result['date'] = datetime.strptime(f"{date_str} {time_str}", '%d.%m.%Y %H:%M')
                    else:
                        # Ищем время в той же строке, что и дата
                        full_date_match = re.search(r"(\d{2}\.\d{2}\.\d{4})\s+(\d{2}:\d{2}(?::\d{2})?)", text)
                        if full_date_match:
                            date_str = full_date_match.group(1)
                            time_str = full_date_match.group(2)
                            result['date'] = datetime.strptime(f"{date_str} {time_str}", '%d.%m.%Y %H:%M')
                        else:
                            result['date'] = datetime.strptime(date_str, '%d.%m.%Y')
                except ValueError:
                    result['date'] = None
            else:
                # Попробуем найти дату в другом формате - ищем дату и время вместе
                full_date_match = re.search(r"(\d{2}\.\d{2}\.\d{4})\s+(\d{2}:\d{2}(?::\d{2})?)", text)
                if full_date_match:
                    try:
                        date_str = full_date_match.group(1)
                        time_str = full_date_match.group(2)
                        result['date'] = datetime.strptime(f"{date_str} {time_str}", '%d.%m.%Y %H:%M')
                    except ValueError:
                        result['date'] = None
                else:
                    # Ищем просто дату в формате ДД.ММ.ГГГГ
                    alt_date_match = re.search(r'\b(\d{2}\.\d{2}\.\d{4})\b', text)
                    if alt_date_match:
                        try:
                            result['date'] = datetime.strptime(alt_date_match.group(1), '%d.%m.%Y')
                        except ValueError:
                            result['date'] = None
                    else:
                        result['date'] = None
            
            # Извлечение суммы операции - специальная обработка для Алиф Банка
            if bank_type == "Алиф Банк":
                # Для Алиф Банка ищем сумму в специфическом формате
                # Сначала ищем строку "Сумма" и число после неё
                amount_match = re.search(r"Сумма\s*\n?\s*(\d+)\s*(?:с\.|c\.|с|c)", text, re.IGNORECASE)
                
                if not amount_match:
                    # Если не нашли по шаблону выше, ищем строку "Итого" и число после неё
                    amount_match = re.search(r"Итого\s*\n?\s*(\d+)\s*(?:с\.|c\.|с|c)", text, re.IGNORECASE)
                
                if not amount_match:
                    # Если всё ещё не нашли, ищем любое число с единицей измерения "с."
                    amount_match = re.search(r"(\d+)\s*(?:с\.|c\.|с|c)", text)
            else:
                # Для других банков используем общий шаблон
                amount_match = re.search(r"(?:Сумма|Сумма операции:|Итого)\s*\n?\s*([\d,.]+)\s*(?:с\.|сомони)?", text)
            
            if amount_match:
                try:
                    # Извлекаем сумму
                    amount_str = amount_match.group(1).strip()
                    # Удаляем все нецифровые символы, кроме точки и запятой
                    amount_str = re.sub(r'[^\d.,]', '', amount_str)
                    # Заменяем запятую на точку
                    amount_str = amount_str.replace(',', '.')
                    result['amount'] = float(amount_str)
                except (ValueError, IndexError):
                    # Если не удалось извлечь сумму из группы, пробуем извлечь из всего совпадения
                    try:
                        amount_str = re.sub(r'[^\d.,]', '', amount_match.group(0))
                        amount_str = amount_str.replace(',', '.')
                        result['amount'] = float(amount_str)
                    except:
                        result['amount'] = None
            else:
                # Попробуем найти сумму в другом формате - ищем числа с десятичной точкой/запятой
                alt_amount_matches = re.findall(r'\b(\d+[\.,]\d{2})\b', text)
                if alt_amount_matches:
                    # Берем самое большое число как сумму
                    try:
                        amounts = [float(match.replace(',', '.')) for match in alt_amount_matches]
                        result['amount'] = max(amounts)
                    except ValueError:
                        result['amount'] = None
                else:
                    # Ищем просто числа, которые могут быть суммой
                    num_matches = re.findall(r'\b(\d+)\s*(?:с\.|c\.|с|c)\b', text)
                    if num_matches:
                        try:
                            amounts = [float(match) for match in num_matches]
                            result['amount'] = max(amounts)
                        except ValueError:
                            result['amount'] = None
                    else:
                        result['amount'] = None
            
            # Извлечение номера операции - специальная обработка для Алиф Банка
            if bank_type == "Алиф Банк":
                # Для Алиф Банка ищем номер транзакции в специфическом формате
                operation_number_match = re.search(r"Номер транзакции\s*\n?\s*(\d+)", text, re.IGNORECASE)
                
                if not operation_number_match:
                    # Альтернативный поиск - ищем просто номер после слова "транзакции"
                    operation_number_match = re.search(r"транзакции\s*\n?\s*(\d+)", text, re.IGNORECASE)
            else:
                # Для других банков используем общий шаблон
                operation_number_match = re.search(r"(?:Номер транзакции|Номер операции:)\s*\n?\s*([0-9/]+)", text)
            
            if operation_number_match:
                result['operation_number'] = operation_number_match.group(1).strip()
            else:
                # Попробуем найти номер операции в другом формате
                alt_op_match = re.search(r'\bОперация[:\s]+([A-Z0-9]+)\b', text)
                if alt_op_match:
                    result['operation_number'] = alt_op_match.group(1).strip()
                else:
                    # Ищем любые последовательности цифр, которые могут быть номером операции
                    # Исключаем номера телефонов и даты
                    op_matches = re.findall(r'\b(\d{8,9})\b', text)
                    if op_matches:
                        # Исключаем числа, которые могут быть номерами телефонов
                        filtered_matches = [match for match in op_matches if not match.startswith('992')]
                        if filtered_matches:
                            result['operation_number'] = filtered_matches[0]
                        else:
                            result['operation_number'] = None
                    else:
                        result['operation_number'] = None
            
            # Извлечение отправителя
            if bank_type == "Алиф Банк":
                # Для Алиф Банка ищем способ оплаты
                sender_match = re.search(r"Способ оплаты\s*\n?\s*([^\n]+)", text, re.IGNORECASE)
                if not sender_match:
                    # Альтернативный поиск - ищем номер карты в маскированном формате
                    sender_match = re.search(r"(\d+\s*\*+\s*[A-Z]+\s*\*+\s*\d+)", text)
            else:
                sender_match = re.search(r"(?:Счет отправителя:|Способ оплаты|От кого:)\s*\n?\s*([0-9*]+\S*|[^\n]+)", text)
            
            if sender_match:
                result['sender'] = sender_match.group(1).strip()
            else:
                result['sender'] = None
            
            # Извлечение получателя (разная логика для разных банков)
            if bank_type == "Алиф Банк":
                # Для Алиф Банка получатель - это ФИО или номер счета
                # Ищем строку "Перевод на счёт" и извлекаем ФИО после неё
                recipient_match = re.search(r"(?:Перевод на счёт|Перевод на счет)\s+([^\n]+)", text, re.IGNORECASE)
                
                if recipient_match:
                    # Извлекаем имя получателя
                    recipient_name = recipient_match.group(1).strip()
                    
                    # Удаляем слова, которые могут быть ошибочно распознаны как часть имени
                    recipient_name = re.sub(r'^(?:слу|Услуга|Устуяа|слуга)\s+', '', recipient_name, flags=re.IGNORECASE)
                    
                    result['receiver'] = recipient_name
                else:
                    # Альтернативный поиск - ищем после слова "Услуга"
                    alt_recipient_match = re.search(r"Услуга\s+(?:Перевод на счёт|Перевод на счет)\s+([^\n]+)", text, re.IGNORECASE)
                    if alt_recipient_match:
                        recipient_name = alt_recipient_match.group(1).strip()
                        result['receiver'] = recipient_name
                    else:
                        # Если не нашли по шаблонам выше, пробуем найти имя в другом месте
                        # Проверяем, есть ли строка после "Услуга"
                        service_match = re.search(r"Услуга\s+([^\n]+)", text)
                        if service_match:
                            service_text = service_match.group(1).strip()
                            # Проверяем, что это похоже на имя (содержит буквы и не является словом "Перевод")
                            if re.search(r'[А-Яа-яЁё]', service_text) and not service_text.startswith("Перевод"):
                                result['receiver'] = service_text
                            else:
                                result['receiver'] = None
                        else:
                            result['receiver'] = None
            else:
                # Для других банков получатель - это номер телефона или счета
                receiver_match = re.search(r"(?:Счет получателя:|Счёт зачисления|Получатель:)\s*\n?\s*(992\d+|[^\n]+)", text)
                if receiver_match:
                    result['receiver'] = receiver_match.group(1).strip()
                else:
                    result['receiver'] = None
            
            # Извлечение счета зачисления для Алиф Банка
            if bank_type == "Алиф Банк":
                account_match = re.search(r"Счёт зачисления\s*\n?\s*(\+?\d+)", text)
                if account_match:
                    # Если нашли счет зачисления, но не нашли получателя, используем счет как получателя
                    if result.get('receiver') is None:
                        result['receiver'] = account_match.group(1).strip()
            
            # Извлечение статуса операции
            status_match = re.search(r"(?:Статус:\s*\n?\s*|ЭЛЕКТРОННЫЙ ПЛАТЕЖ\s*\n?\s*)(ИСПОЛНЕНО|ВЫПОЛНЕНА|Успешный|УСПЕШНО)", text, re.IGNORECASE)
            if status_match:
                result['status'] = status_match.group(1).strip()
            else:
                result['status'] = None
            
            # Извлечение примечаний (если есть)
            notes_match = re.search(r"(?:Примечание|Назначение платежа|Комментарий):\s*\n?\s*([^\n]+)", text, re.IGNORECASE)
            if notes_match:
                result['notes'] = notes_match.group(1).strip()
            else:
                result['notes'] = None
            
            # Извлечение организации
            org_match = re.search(r"(?:ЗАО|ОАО)\s+\"([^\"]+)\"", text)
            if org_match:
                result['organization'] = org_match.group(1).strip()
            else:
                result['organization'] = bank_type
            
            # Извлечение комиссии (если есть)
            fee_match = re.search(r"Комиссия\s*\n?\s*(\d+)\s*(?:с\.|c\.|с|c)", text, re.IGNORECASE)
            if fee_match:
                fee_value = fee_match.group(1).strip()
                result['fee'] = fee_value
            else:
                # Если поле комиссии отсутствует, устанавливаем значение "0"
                result['fee'] = "0"
        
        # Добавляем исходный текст для отладки
        result['raw_text'] = text
        
        return result
