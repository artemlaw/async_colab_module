import asyncio
import logging
import time
from datetime import datetime

from async_colab_module.utils import get_api_tokens
from async_colab_module.base import AsyncHttpClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('WB')


class WB(AsyncHttpClient):
    def __init__(self, api_key: str, max_rete: int = 45, time_period: int = 3):
        super().__init__(max_rete=max_rete, time_period=time_period)
        # ssl_context = ssl.create_default_context()
        # ssl_context.check_hostname = False
        # ssl_context.verify_mode = ssl.CERT_NONE
        # self.session = aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context))
        self.headers = {'Authorization': api_key, 'Content-Type': 'application/json'}
        self.host = 'https://suppliers-api.wildberries.ru/'

    async def get_commission(self):
        logger.info(f'Получение комиссий по категориям')
        url = 'https://common-api.wildberries.ru/api/v1/tariffs/commission'
        result = await self.get(url, {'locale': 'ru'})
        if not result:
            logger.error('Не удалось получить данные о комиссиях.')
        return result if result else []

    async def get_tariffs_for_box(self):
        logger.info(f'Получение данных логистики')
        url = 'https://common-api.wildberries.ru/api/v1/tariffs/box'
        current_date = datetime.now().strftime('%Y-%m-%d')
        params = {'date': current_date}
        result = await self.get(url, params)
        if not result:
            logger.error('Не удалось получить данные о тарифах логистики.')
        return result if result else []

    async def get_product_prices(self):
        print(f'Получение актуальных цен и дисконта')
        url = 'https://discounts-prices-api.wb.ru/api/v2/list/goods/filter'
        params = {'limit': 1000, 'offset': 0}

        products_list = []
        while True:
            result = await self.get(url, params)
            if result:
                list_goods = result.get('data', {}).get('listGoods', [])
                if list_goods:
                    products_list += list_goods
                    params['offset'] += params['limit']
                else:
                    break
            else:
                logger.error('Не удалось получить данные о ценах.')
                break
        return products_list

    async def get_orders(self, from_data):
        url = 'https://statistics-api.wildberries.ru/api/v1/supplier/orders'
        params = {'dateFrom': from_data, 'flag': 1}
        result = await self.get(url, params)
        if not result:
            logger.error('Не удалось получить данные о заказах.')
        return result.json() if result else []

    async def get_orders_fbs(self, from_date=None, to_date=None):
        url = self.host + 'api/v3/orders'
        params = {'limit': 1000, 'next': 0}
        if from_date:
            params['dateFrom'] = from_date
        if to_date:
            params['dateTo'] = to_date

        orders_fbs = []
        while True:
            result = await self.get(url, params)
            if result:
                response_json = result.json()
                orders_list = response_json.get('orders')
                next_cursor = response_json.get('next')
                if orders_list and next_cursor:
                    orders_fbs += orders_list
                    params['next'] = next_cursor
                else:
                    break
            else:
                logger.error('Не удалось получить данные о заказах FBS.')
                break
        return orders_fbs


if __name__ == '__main__':
    ms_token, wb_token, _ = get_api_tokens()

    async def main():
        async with WB(api_key=wb_token, max_rete=45, time_period=3) as wb_client:
            start_time = time.time()
            commission = wb_client.get_commission()
            tariffs = wb_client.get_tariffs_for_box()
            product_prices = wb_client.get_product_prices()

            commission_, tariffs_, product_prices_ = await asyncio.gather(commission, tariffs, product_prices)

            # Печать результатов
            print(len(commission_))
            print(len(tariffs_))
            print(f"Количество товаров с ценой: {len(product_prices_)}")
            print(time.time() - start_time)

    asyncio.run(main())
