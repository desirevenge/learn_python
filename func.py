def compare_number(number, min_value, max_value):
    """
    Сравнивает число с минимальным и максимальным значениями
    и возвращает результат в сотых долях
    
    Args:
        number (float): число для сравнения
        min_value (float): минимальное значение
        max_value (float): максимальное значение
    
    Returns:
        float: значение в сотых долях от 0 до 100
    """
    # Проверка на корректность диапазона
    if min_value >= max_value:
        raise ValueError("Минимальное значение должно быть меньше максимального")
    
    # Проверка, что число находится в диапазоне
    if number < min_value or number > max_value:
        raise ValueError(f"Число {number} находится вне диапазона [{min_value}, {max_value}]")
    
    # Вычисление позиции числа в диапазоне в сотых долях
    range_size = max_value - min_value
    position = (number - min_value) / range_size
    hundredths = position * 100
    
    return round(hundredths, 2)

# Пример использования
try:
    number = float(input("Введите число для сравнения: "))
    min_val = float(input("Введите минимальное значение: "))
    max_val = float(input("Введите максимальное значение: "))
    
    result = compare_number(number, min_val, max_val)
    print(f"Число {number} находится на {result}% от минимального значения")
    print(f"Относительно диапазона: min={min_val}, max={max_val}, позиция={result}/100")
    
except ValueError as e:
    print(f"Ошибка: {e}")