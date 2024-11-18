import asyncio

import aiohttp
import pytest
from datetime import datetime, timedelta

from async_colab_module import MoySklad, get_api_tokens

ms_token, wb_token, ym_token = get_api_tokens()


@pytest.fixture
def ms_client():
    return MoySklad(api_key=ms_token)


# @pytest.fixture
# def wb_client():
#     return WB(api_key=wb_token)


# def test_get_orders(ms_client):
#     to_date = datetime.now().date()
#     from_date = to_date - timedelta(days=1)
#     from_date_f = f'{from_date} 00:00:00.000'
#     to_date_f = f'{to_date} 23:59:00.000'
#
#     filters = f'?filter=moment>{from_date_f};moment<{to_date_f};&order=name,desc&expand=positions.assortment,state'
#     ms_orders = ms_client.get_orders(filters)
#     assert len(ms_orders) >= 0


# def test_get_bundles(ms_client):
#     bundles = ms_client.get_bundles()
#     assert len(bundles) > 1

async def test_get_bundles(ms_client):
    async with aiohttp.ClientSession() as session:
        bundles = await ms_client.get_bundles(session)
        print(bundles)
        assert len(bundles) > 1

asyncio.run(test_get_bundles(ms_client))
# def test_wb_get_commission(wb_client):
#     commission = wb_client.get_commission()
#     assert commission
#
#
# def test_wb_get_orders(wb_client):
#
#     current_day = datetime.now()
#     past_day = current_day - timedelta(days=1)
#     start_of_day = datetime(past_day.year, past_day.month, past_day.day, 0, 0, 0)
#     end_of_day = datetime(current_day.year, current_day.month, current_day.day, 23, 59, 59)
#
#     wb_orders = wb_client.get_orders(start_of_day.date())
#     wb_orders_fbs = wb_client.get_orders_fbs(from_date=int(start_of_day.timestamp()),
#                                              to_date=int(end_of_day.timestamp()))
#     rids = {order_fbs.get('rid') for order_fbs in wb_orders_fbs}
#     print('FBS', len(wb_orders_fbs))
#     wb_orders_fbo = [order for order in wb_orders
#                      if order.get('orderType') == 'Клиентский' and not order.get('isCancel')
#                      and order.get('srid') not in rids]
#     print('FBO', len(wb_orders_fbo))
#     assert wb_orders_fbs and wb_orders_fbo
