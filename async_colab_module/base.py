import asyncio
import logging
import aiohttp

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