import asyncio
import logging
import pandas as pd
from pprint import pprint

from async_colab_module import (
    get_api_tokens,
    MoySklad,
    get_prime_cost,
    get_stock_for_bundle,
    get_ya_data_,
)
from async_colab_module.ya_market import (
    YM,
    get_ya_campaign_and_business_ids,
    chunked_offers_list,
    get_dict_for_commission,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PRICES")


async def get_desired_prices(plan_margin: float = 25.0, fbs: bool = True):
    ms_token, _, ym_token = get_api_tokens()
    ms_client = MoySklad(api_key=ms_token)
    products_ = await ms_client.get_bundles()

    # Оставляем только Яндекс
    ms_ya_products = [
        product for product in products_ if "ЯндексМаркет" in product["pathName"]
    ]
    print("Мой склад: Получение остатка товара")
    stocks = await ms_client.get_stock()
    ms_stocks = {stock["assortmentId"]: stock["quantity"] for stock in stocks}
    print("Мой склад: Получение себестоимости товара")
    ms_ya_products_ = {
        product["article"]: {
            "STOCK": get_stock_for_bundle(ms_stocks, product),
            "PRIME_COST": get_prime_cost(product.get("salePrices", [])),
            "NAME": product["name"],
        }
        for product in ms_ya_products
    }
    logger.info(len(ms_ya_products_))
    await ms_client.close()

    ym_client = YM(api_key=ym_token, max_rete=45, time_period=3)

    campaign_id, business_id = await get_ya_campaign_and_business_ids(
        ym_client, fbs=fbs
    )

    offers = await ym_client.get_full_offers(business_id)

    print("ЯндексМаркет: Получение актуальных тарифов")
    offers_commission_dict = await chunked_offers_list(
        get_dict_for_commission,
        ym_client=ym_client,
        campaign_id=campaign_id,
        data=offers,
        chunk_size=200,
    )

    await ym_client.close()

    ya_set = set(offers_commission_dict)
    ms_set = set(ms_ya_products_)

    result_dict = {
        key: {**offers_commission_dict.get(key, {}), **ms_ya_products_.get(key, {})}
        for key in ya_set & ms_set
    }

    print("Номенклатура которая есть в ЯндексМаркете, но не связана в МС:")
    print("\n".join(ya_set - ms_set))
    data_for_report = [
        get_ya_data_(article, result_dict[article], plan_margin)
        for article in result_dict
    ]
    print('Формирую отчет "Рекомендуемые цены"')
    # progress_bar.update(50)
    pd.set_option("display.max_columns", None)
    pd.set_option("display.max_rows", None)
    df = pd.DataFrame(data_for_report)
    df.columns = [
        "Номенклатура",
        "Артикул",
        "Остаток",
        "Текущая цена",
        "Рекомендуемая цена",
        "Себестоимость",
        "Комиссия",
        "Эквайринг",
        "Доставка",
        "Доставка в округ",
        "Обработка",
        "Прибыль",
        "Рентабельность",
    ]
    path_xls_file = "ya_рекомендуемые_цены.xlsx"
    df.to_excel(path_xls_file, sheet_name="Список YA", index=False)
    print("Файл отчета готов")
    files.download(path_xls_file)

    # print(df)

    # Определение комиссии маркетплейса
    # Яндекс
    # _________________________________________
    # Комиссия % от цены
    # Прием платежа 1,9% от цены
    #
    # Доставка FBS покупателя - 4,5% от цены, но не более 500
    #
    # Доставка экспресс = 6% от цены, но не менее 80, не более 500
    #
    # Фиксированные расходы
    # 0,12 руб
    # +FBS
    # 20 - обработка
    # Доставка в округ или населенный пункт - от весообъема

    # Мегамаркет
    # _________________________________________
    # Комиссия по категории из файла тут https://megamarket.ru/docs/percent_price_b2b/ или из готовых связок
    #
    # Комиссия за обработку платежей - 1,5% от цены (график выплат, разнится от 1,25 до 2%)
    # Комиссия за сортировку отправлений - 10 руб.
    # Комиссия за логистику - от объемного веса (фиксированный справочник для расчета) от 75р и до 275 если вес до 25кг
    #
    # Комиссия за доставку до покупателя - 5% от цены, но не менее 10р не более 500


# pprint(ya_products[-1])


if __name__ == "__main__":

    async def main():
        await get_desired_prices()

    asyncio.run(main())
