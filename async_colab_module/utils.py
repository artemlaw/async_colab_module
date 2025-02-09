import os
import re
import asyncio


def get_api_tokens():
    try:
        from google.colab import userdata

        MS_API_TOKEN = userdata.get("MS_API_TOKEN")
        WB_API_TOKEN = userdata.get("WB_API_TOKEN")
        YM_API_TOKEN = userdata.get("YM_API_TOKEN")
        return MS_API_TOKEN, WB_API_TOKEN, YM_API_TOKEN
    except ImportError:
        pass
    from dotenv import load_dotenv

    load_dotenv()
    MS_API_TOKEN = os.getenv("MS_API_TOKEN")
    WB_API_TOKEN = os.getenv("WB_API_TOKEN")
    YM_API_TOKEN = os.getenv("YM_API_TOKEN")

    return MS_API_TOKEN, WB_API_TOKEN, YM_API_TOKEN


def get_ya_ids():
    try:
        from google.colab import userdata

        fbs_campaign_id = userdata.get("YA_FBS_CAMPAIGN_ID")
        ex_campaign_id = userdata.get("YA_EXPRESS_CAMPAIGN_ID")
        business_id = userdata.get("YA_BUSINESS_ID")
        return fbs_campaign_id, ex_campaign_id, business_id
    except ImportError:
        pass
    from dotenv import load_dotenv

    load_dotenv()
    fbs_campaign_id = os.getenv("YA_FBS_CAMPAIGN_ID")
    ex_campaign_id = os.getenv("YA_EXPRESS_CAMPAIGN_ID")
    business_id = os.getenv("YA_BUSINESS_ID")

    return fbs_campaign_id, ex_campaign_id, business_id


async def get_category_dict(wb_client, fbs=True):
    commission = await wb_client.get_commission()
    if fbs:
        key = "kgvpMarketplace"
    else:
        key = "paidStorageKgvp"
    category_dict = {comm["subjectName"]: comm[key] for comm in commission["report"]}
    return category_dict


def get_product_id_from_url(url):
    pattern = r"/product/([0-9a-fA-F-]+)"
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    else:
        return None


def get_stock_for_bundle(stocks_dict, product):
    product_bundles = product["components"]["rows"]
    product_stock = 0.0
    for bundle in product_bundles:
        bundle_id = get_product_id_from_url(bundle["assortment"]["meta"]["href"])
        if bundle_id in stocks_dict:
            p_stock = stocks_dict[bundle_id] // bundle["quantity"]
            if p_stock > product_stock:
                product_stock = p_stock
    return product_stock


async def get_ms_stocks_dict(ms_client, products):
    print("Получение остатков номенклатуры")
    stocks = await ms_client.get_stock()
    stocks_dict = {stock["assortmentId"]: stock["quantity"] for stock in stocks}
    wb_stocks_dict = {
        int(product["code"]): get_stock_for_bundle(stocks_dict, product)
        for product in products
    }
    return wb_stocks_dict


async def get_ms_stocks_article_dict(ms_client, products):
    print("Получение остатков номенклатуры по артикулу")
    stocks = await ms_client.get_stock()
    stocks_dict = {stock["assortmentId"]: stock["quantity"] for stock in stocks}
    wb_stocks_dict = {
        product["article"]: get_stock_for_bundle(stocks_dict, product)
        for product in products
    }
    return wb_stocks_dict


async def get_price_dict(wb_client):
    data = await wb_client.get_product_prices()
    # TODO: Добавить возможность получения данных по другим размерам, либо изменить источник
    price_dict = {
        d["nmID"]: {
            "price": d["sizes"][0]["discountedPrice"],
            "discount": d["discount"],
        }
        for d in data
        if len(d["sizes"]) == 1
    }
    return price_dict


async def get_dict_for_report(products, ms_client, wb_client, fbs=True):
    category_dict_ = get_category_dict(wb_client, fbs=fbs)
    tariffs_logistic_data_ = wb_client.get_tariffs_for_box()
    ms_stocks_dict_ = get_ms_stocks_dict(ms_client, products)
    wb_prices_dict_ = get_price_dict(wb_client)

    category_dict, tariffs_logistic_data, ms_stocks_dict, wb_prices_dict = (
        await asyncio.gather(
            category_dict_, tariffs_logistic_data_, ms_stocks_dict_, wb_prices_dict_
        )
    )
    return {
        "ms_stocks_dict": ms_stocks_dict,
        "category_dict": category_dict,
        "tariffs_data": tariffs_logistic_data,
        "wb_prices_dict": wb_prices_dict,
    }


def create_code_index(elements):
    code_index = {}
    for element in elements:
        code = int(element.get("code"))
        if code:
            code_index[code] = element
    return code_index


def find_warehouse_by_name(warehouses, name):
    return next(
        (warehouse for warehouse in warehouses if warehouse["warehouseName"] == name),
        None,
    )


def get_value_by_name(elements, name):
    """Возвращает value элемента из списка elements по имени name"""
    return next(
        (element["value"] for element in elements if element["name"] == name), None
    )


def get_logistic_dict(tariffs_data, warehouse_name="Маркетплейс"):
    tariff = find_warehouse_by_name(
        tariffs_data["response"]["data"]["warehouseList"], warehouse_name
    )
    if not tariff:
        tariff = find_warehouse_by_name(
            tariffs_data["response"]["data"]["warehouseList"], "Коледино"
        )
    # Логистика
    logistic_dict = {
        "KTR": 1.0,
        "TARIFF_FOR_BASE_L": float(tariff["boxDeliveryBase"].replace(",", ".")),
        "TARIFF_BASE": 1,
        "TARIFF_OVER_BASE": float(tariff["boxDeliveryLiter"].replace(",", ".")),
        "WH_COEFFICIENT": round(
            float(tariff["boxDeliveryAndStorageExpr"].replace(",", ".")) / 100, 2
        ),
    }
    return logistic_dict


def create_prices_dict(prices_list: list) -> dict:
    prices_dict = {}
    for price in prices_list:
        name = price["priceType"]["name"]
        value = price["value"]
        prices_dict[name] = value
    return prices_dict


def get_prime_cost(prices_list: list, price_name: str = "Цена продажи") -> float:
    return next(
        (
            price.get("value", 0.0) / 100
            for price in prices_list
            if price["priceType"]["name"] == price_name
        ),
        0.0,
    )


def create_attributes_dict(attributes_list):
    attributes_dict = {}
    for attribute in attributes_list:
        name = attribute["name"]
        value = attribute["value"]
        attributes_dict[name] = value
    return attributes_dict


def get_product_volume(attributes_dict):
    return (
        attributes_dict.get("Длина", 0)
        * attributes_dict.get("Ширина", 0)
        * attributes_dict.get("Высота", 0)
    ) / 1000.0


def get_logistics(
    KTR, TARIFF_FOR_BASE_L, TARIFF_BASE, TARIFF_OVER_BASE, WH_COEFFICIENT, volume
):
    volume_calc = max(volume - TARIFF_BASE, 0)
    logistics = round(
        (TARIFF_FOR_BASE_L * TARIFF_BASE + TARIFF_OVER_BASE * volume_calc)
        * WH_COEFFICIENT
        * KTR,
        2,
    )
    return logistics


def get_order_data_fbo(order, product, base_dict, acquiring=1.5):
    wb_prices_dict = base_dict["wb_prices_dict"]
    logistic_dict = get_logistic_dict(
        base_dict["tariffs_data"], warehouse_name=order.get("warehouseName", "Коледино")
    )

    nm_id = order.get("nmId", "")
    sale_prices = product.get("salePrices", [])
    prices_dict = create_prices_dict(sale_prices)

    # Получение цены
    price = wb_prices_dict.get(nm_id, {}).get("price")
    if not price:
        price = prices_dict.get("Цена WB после скидки", 0) / 100

    # Получение скидки
    discount = wb_prices_dict.get(nm_id, {}).get("discount")
    if not discount:
        price_before_discount = prices_dict.get("Цена WB до скидки", 0.0)
        price_after_discount = prices_dict.get("Цена WB после скидки", 0.0)
        if price_before_discount:
            discount = (
                1 - round(price_after_discount / price_before_discount, 1)
            ) * 100
        else:
            discount = 0

    cost_price_c = prices_dict.get("Цена основная", 0.0)
    cost_price = cost_price_c / 100
    order_price = round(order.get("finishedPrice", 0.0), 1)

    attributes = product.get("attributes", [])
    attributes_dict = create_attributes_dict(attributes)
    volume = get_product_volume(attributes_dict)

    logistics = get_logistics(
        logistic_dict["KTR"],
        logistic_dict["TARIFF_FOR_BASE_L"],
        logistic_dict["TARIFF_BASE"],
        logistic_dict["TARIFF_OVER_BASE"],
        logistic_dict["WH_COEFFICIENT"],
        volume,
    )

    category = order.get("subject", attributes_dict["Категория товара"])
    # Поставил 30% комиссии по умолчанию, если не найдено
    commission = base_dict.get("category_dict", {}).get(category, 30)

    commission_cost = round(commission / 100 * price, 1)
    acquiring_cost = round(acquiring / 100 * price, 1)

    reward = round(commission_cost + acquiring_cost + logistics, 1)
    profit = round(price - cost_price - reward, 1)
    profitability = round(profit / price * 100, 1)

    order_commission_cost = round(commission / 100 * order_price, 1)
    order_acquiring_cost = round(acquiring / 100 * order_price, 1)

    order_reward = round(order_commission_cost + order_acquiring_cost + logistics, 1)
    order_profit = round(order_price - cost_price - order_reward, 1)
    order_profitability = round(order_profit / order_price * 100, 1)

    data = {
        "name": product.get("name", ""),
        "nm_id": nm_id,
        "article": product.get("article", ""),
        "stock": base_dict.get("ms_stocks_dict", {}).get(nm_id, 0),
        "order_create": order.get("date", ""),
        "order_name": order.get("sticker", "0"),
        "quantity": 1,
        "discount": discount,
        "item_price": price,
        "order_price": order_price,
        "cost_price": cost_price,
        "commission": commission_cost,
        "acquiring": acquiring_cost,
        "logistics": logistics,
        "reward": reward,
        "profit": profit,
        "profitability": profitability,
        "order_reward": order_reward,
        "order_profit": order_profit,
        "order_profitability": order_profitability,
    }

    return data


def get_ya_data_(article, article_data, plan_margin: float = 25.0):

    price = article_data.get("PRICE", 0.0)
    prime_cost = article_data.get("PRIME_COST", 0.0)
    commission_cost = round(article_data.get("FEE").get("current_amount", 0.0), 1)
    agency_commission = article_data.get("AGENCY_COMMISSION", 0.0)
    acquiring_cost = round(
        article_data.get("PAYMENT_TRANSFER").get("current_amount", 0.0)
        + agency_commission,
        1,
    )
    delivery_cost = round(
        article_data.get("DELIVERY_TO_CUSTOMER").get("current_amount", 0.0)
        + article_data.get("EXPRESS_DELIVERY").get("current_amount", 0.0),
        1,
    )
    delivery_cross_cost = article_data.get("CROSSREGIONAL_DELIVERY", 0.0)
    sorting = article_data.get("SORTING", 0.0)

    reward = round(
        commission_cost
        + acquiring_cost
        + delivery_cost
        + delivery_cross_cost
        + sorting,
        1,
    )
    profit = round(price - prime_cost - reward, 1)
    profitability = round(profit / price * 100, 1)

    margin = plan_margin/ 100

    commission_percent = round(article_data.get("FEE", {}).get("percent", 0.0) / 100, 3)
    payment_percent = round(
        article_data.get("PAYMENT_TRANSFER", {}).get("percent", 0.0) / 100, 3
    )

    delivery_cost_percent = round(
        article_data.get("DELIVERY_TO_CUSTOMER", {}).get("percent", 0.0) / 100, 3
    )

    express_delivery_percent = round(
        article_data.get("EXPRESS_DELIVERY", {}).get("percent", 0.0) / 100, 3
    )

    delivery_percent = round(delivery_cost_percent + express_delivery_percent, 3)

    recommended_price = round(
        (prime_cost + agency_commission + delivery_cross_cost + sorting)
        / (1 - margin - commission_percent - payment_percent - delivery_percent)
    )

    delivery_cost_max = article_data.get("DELIVERY_TO_CUSTOMER", {}).get(
        "max_value", 0.0
    )
    express_delivery_max = article_data.get("EXPRESS_DELIVERY", {}).get(
        "max_value", 0.0
    )
    express_delivery_min = article_data.get("EXPRESS_DELIVERY", {}).get(
        "min_value", 0.0
    )

    if delivery_cost_max:
        delivery_cost_ = min(
            recommended_price * delivery_cost_percent, delivery_cost_max
        )
        recommended_price = round(
            (prime_cost + agency_commission + delivery_cross_cost + sorting + delivery_cost_)
            / (1 - margin - commission_percent - payment_percent)
        )
    elif express_delivery_max:
        express_delivery_ = max(
            min(recommended_price * express_delivery_percent, express_delivery_max),
            express_delivery_min,
        )
        recommended_price = round(
            (prime_cost + agency_commission + delivery_cross_cost + sorting + express_delivery_)
            / (1 - margin - commission_percent - payment_percent)
        )

    data = {
        "name": article_data.get("NAME", ""),
        "article": article,
        "stock": article_data.get("STOCK", 0.0),
        "price": price,
        "recommended_price": recommended_price,
        "prime_cost": prime_cost,
        "commission": commission_cost,
        "acquiring": acquiring_cost,
        "delivery": delivery_cost,
        "crossregional_delivery": delivery_cross_cost,
        "sorting": sorting,
        "profit": profit,
        "profitability": profitability,
    }

    return data
