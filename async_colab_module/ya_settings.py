class YaSettings:

    transit_warehouse_type = "MINI_SORTING_CENTER"  # Склад сортировки. Определяет стоимость обработки
    tariff_messages = {
        "PRICE": "Цена",
        "FEE": "Размещение товаров на витрине",
        "AGENCY_COMMISSION": "Прием платежа покупателя",
        "PAYMENT_TRANSFER": "Перевод платежа покупателя",
        "DELIVERY_TO_CUSTOMER": "Доставка покупателю",
        "CROSSREGIONAL_DELIVERY": "Доставка в федеральный округ",
        "EXPRESS_DELIVERY": "Экспресс доставка",
        "SORTING": "Обработка заказа",
        "MIDDLE_MILE": "Средняя миля",
    }


ya_settings = YaSettings()
