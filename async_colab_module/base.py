import asyncio
import logging
import aiohttp
from aiolimiter import AsyncLimiter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('API')


class AsyncHttpClient:
    def __init__(self, max_rete: int, time_period: int, semaphore: int = 5,
                 max_retries: int = 3, delay_seconds: int = 10):
        self.session = aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False))
        self.headers = {'Content-Type': 'application/json'}
        # Ограничитель для 45 запросов каждые 3 секунды
        self.rate_limiter = AsyncLimiter(max_rete, time_period)
        # Ограничитель для не более semaphore параллельных запросов
        self.semaphore = asyncio.Semaphore(semaphore)
        # Три попытки при ошибке, через 10 секунд
        self.max_retries = max_retries
        self.delay_seconds = delay_seconds

    async def handle_request_errors(self, func, *args, **kwargs):
        for attempt in range(self.max_retries):
            try:
                return await func(*args, **kwargs)
            except aiohttp.ClientResponseError as e:
                if attempt < self.max_retries - 1:
                    logger.error(f'Неудачный запрос, ошибка: {e}. Повтор через {self.delay_seconds} секунд.')
                    await asyncio.sleep(self.delay_seconds)
                else:
                    logger.error(
                        f'Достигнуто максимальное количество попыток ({self.max_retries}). '
                        f'Прекращение повторных запросов.')
        return None

    async def get(self, url, params=None):
        return await self.handle_request_errors(self._get, url, params=params)

    async def post(self, url, data):
        return await self.handle_request_errors(self._post, url, json=data)

    async def put(self, url, data):
        return await self.handle_request_errors(self._put, url, json=data)

    async def delete(self, url):
        return await self.handle_request_errors(self._delete, url)

    async def _get(self, url, params=None):
        async with self.semaphore:
            async with self.rate_limiter:
                async with self.session.get(url, headers=self.headers, params=params) as response:
                    if not response.ok:
                        raise aiohttp.ClientResponseError(history=response.history, status=response.status,
                                                          message=response.reason, request_info=response.request_info)
                    return await response.json()

    async def _post(self, url, json):
        async with self.semaphore:
            async with self.rate_limiter:
                async with self.session.post(url, headers=self.headers, json=json) as response:
                    return await response.json()

    async def _put(self, url, json):
        async with self.semaphore:
            async with self.rate_limiter:
                async with self.session.put(url, headers=self.headers, json=json) as response:
                    return await response.json()

    async def _delete(self, url):
        async with self.semaphore:
            async with self.rate_limiter:
                async with self.session.delete(url, headers=self.headers) as response:
                    return await response.json()

    async def close(self):
        await self.session.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()


if __name__ == '__main__':

    async def main():
        async with AsyncHttpClient(max_rete=45, time_period=3) as client:
            data = await client.get('https://jsonplaceholder.typicode.com/todos/1')
            print(data)


    asyncio.run(main())
