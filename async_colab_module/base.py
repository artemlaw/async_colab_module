import asyncio
import logging
import aiohttp
from aiolimiter import AsyncLimiter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('API')


def handle_request(max_retries=3, delay_seconds=15):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    async with aiohttp.ClientSession() as session:
                        response = await func(session, *args, **kwargs)
                        response.raise_for_status()
                        return response
                except aiohttp.ClientResponseError as e:
                    logger.error(f'Неудачный запрос, ошибка: {e}. Повтор через {delay_seconds} секунд.')
                    await asyncio.sleep(delay_seconds)
            logger.error(f'Достигнуто максимальное количество попыток ({max_retries}). Прекращение повторных запросов.')
            return None
        return wrapper
    return decorator


class ApiBase:
    def __init__(self):
        self.headers = {'Content-Type': 'application/json'}

    @handle_request()
    async def get_data(self, session, url, params=None):
        async with session.get(url, headers=self.headers, params=params) as response:
            return response

    @handle_request()
    async def post_data(self, session, url, data):
        async with session.post(url, headers=self.headers, json=data) as response:
            return response

    @handle_request()
    async def put_data(self, session, url, data):
        async with session.put(url, headers=self.headers, json=data) as response:
            return response

    @handle_request()
    async def delete_data(self, session, url):
        async with session.delete(url, headers=self.headers) as response:
            return response


class AsyncHttpClient:
    def __init__(self, max_retries=3, delay_seconds=15):
        self.session = aiohttp.ClientSession()
        self.headers = {'Content-Type': 'application/json'}
        self.max_retries = max_retries
        self.delay_seconds = delay_seconds
        # Ограничитель для 45 запросов каждые 3 секунды
        self.rate_limiter = AsyncLimiter(45, 3)
        # Ограничитель для не более 5 параллельных запросов
        self.semaphore = asyncio.Semaphore(5)

    async def handle_request_errors(self, func, *args, **kwargs):
        for attempt in range(self.max_retries):
            try:
                return await func(*args, **kwargs)
            except aiohttp.ClientResponseError as e:
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.delay_seconds)
                else:
                    raise e

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
                        raise aiohttp.ClientResponseError(history=response.history, status=response.status, message=response.reason, request_info=response.request_info)
                    return await response.json()

    async def _post(self, url, json):
        async with self.session.post(url, headers=self.headers, json=json) as response:
            return await response.json()

    async def _put(self, url, json):
        async with self.session.put(url, headers=self.headers, json=json) as response:
            return await response.json()

    async def _delete(self, url):
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
        async with AsyncHttpClient() as client:
            data = await client.get('https://jsonplaceholder.typicode.com/todos/1')
            print(data)


    asyncio.run(main())
