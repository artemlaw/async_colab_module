import asyncio
import logging
import time

from async_colab_module.utils import get_api_tokens
from async_colab_module.base import AsyncHttpClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('MoySklad')


class MoySklad(AsyncHttpClient):
    def __init__(self, api_key: str, max_rete: int = 45, time_period: int = 3):
        super().__init__(max_rete=max_rete, time_period=time_period)
        self.headers = {'Accept-Encoding': 'gzip', 'Authorization': api_key, 'Content-Type': 'application/json'}
        self.host = 'https://api.moysklad.ru/api/remap/1.2/'

    async def get_with_pagination(self, url, limit=1000):
        result = await self.get(url, params={'limit': 1, 'offset': 0})
        items = []
        if result:
            size = result.get('meta', {}).get('size', 0)
            if size:
                request_list = [self.get(url, params={'limit': limit, 'offset': i}) for i in range(0, size + limit, limit)]
                requests = await asyncio.gather(*request_list)
                for request in requests:
                    items += request.get('rows', [])
        return items

    async def get_products_list(self):
        url = f'{self.host}entity/product'
        return await self.get_with_pagination(url, limit=1000)

    async def get_bundles(self):
        url = f'{self.host}entity/bundle?expand=components.rows.assortment'
        return await self.get_with_pagination(url, limit=100)

    async def get_stock(self):
        url = f'{self.host}report/stock/all/current'
        # 'include': 'zeroLines' - показать товары с нулевым доступным остатком
        params = {'stockType': 'quantity', 'include': 'zeroLines'}  # по умолчанию params = {'stockType': 'quantity'}
        result = await self.get(url, params)
        response_json = result if result else []
        if not result:
            logger.error('Не удалось получить данные о наличии.')
        return response_json


if __name__ == '__main__':
    ms_token, wb_token, _ = get_api_tokens()


    async def main():
        async with MoySklad(api_key=ms_token, max_rete=45, time_period=3) as ms_client:
            start_time = time.time()
            products_task = ms_client.get_products_list()
            bundles_task = ms_client.get_bundles()

            products, bundles = await asyncio.gather(products_task, bundles_task)

            # Печать результатов
            print(f"Количество продуктов: {len(products)}")
            print(f"Количество пакетов: {len(bundles)}")
            print(time.time() - start_time)


    asyncio.run(main())
