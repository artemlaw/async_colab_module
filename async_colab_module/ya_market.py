import asyncio
import logging
import time

from async_colab_module.utils import get_api_tokens, get_value_by_name, get_ya_ids
from async_colab_module.base import AsyncHttpClient
from async_colab_module.ya_settings import ya_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(name="YandexMarket")


class YM(AsyncHttpClient):
    def __init__(self, api_key: str, max_rete: int = 45, time_period: int = 3):
        super().__init__(max_rete=max_rete, time_period=time_period)
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        self.host = "https://api.partner.market.yandex.ru/"

    async def get_campaigns(self):
        logger.info(f"Получение информации о магазинах кабинета")
        url = self.host + "campaigns?page=&pageSize="
        result = await self.get(url)
        if not result:
            logger.error("Не удалось получить данные о магазинах кабинета")
        return result if result else {}

    async def get_offers(self, business_id: int):
        logger.info(f"Получение карточек товара")
        # Лимит 600 запросов в минуту, не более 200 товаров в одном запросе
        # url = self.host + f"businesses/{business_id}/offer-mappings"
        page_token = ""
        url = (
            self.host
            + f"businesses/{business_id}/offer-mappings?page_token={page_token}&limit=200"
        )
        data = {"archived": False}
        result = await self.post(url, data)
        if not result:
            logger.error("Не удалось получить данные о карточках товара")
        return (
            result.get("result", {}).get("offerMappings", [])
            if result.get("status") == "OK"
            else []
        )

    async def get_categories(
        self, offers: list, campaign_id: int = 0, selling_program: str = "FBS"
    ):
        logger.info(f"Получение актуальных тарифов")
        # Максимум 200, то можно совместить с получением номенклатуры
        url = self.host + "tariffs/calculate"
        data = {
            "parameters": {
                "frequency": "BIWEEKLY",
                "campaignId" if campaign_id else "sellingProgram": campaign_id
                or selling_program,
            },
            "offers": offers,
        }

        result = await self.post(url, data)
        if not result:
            logger.error("Не удалось получить данные о карточках товара.")
        return (
            result.get("result", {}).get("offers", [])
            if result.get("status") == "OK"
            else []
        )

    async def get_full_offers(self, business_id: int):
        logger.info(f"Получение карточек товара")
        page_token = ""
        data = {"archived": False}

        offers_list = []
        while True:
            url = (
                self.host
                + f"businesses/{business_id}/offer-mappings?page_token={page_token}&limit=200"
            )
            result = await self.post(url, data)
            if result and result.get("status") == "OK":
                offers_list += result.get("result", {}).get("offerMappings", [])
                if not result.get("result", {}).get("paging", {}):
                    break
                page_token = (
                    result.get("result", {}).get("paging", {}).get("nextPageToken", "")
                )
            else:
                logger.error("Не удалось получить данные о карточках товара.")
                break
        return offers_list


async def get_ya_campaign_and_business_ids(ym_client: YM, fbs: bool = True):
    ids = get_ya_ids()
    campaign_id, business_id = (ids[0], ids[2]) if fbs else (ids[1], ids[2])

    if campaign_id and business_id:
        return campaign_id, business_id
    else:
        campaigns = await ym_client.get_campaigns()
        campaign = campaigns.get("campaigns", [])[0]
        campaign_id = int(campaign.get("id"))
        business_id = int(campaign.get("business", {}).get("id"))
        return campaign_id, business_id


async def get_dict_for_commission(
    ym_client: YM, campaign_id: int, offers: list
) -> dict:
    if len(offers) > 200:
        logger.error("Ограничение запроса комиссии! Не более 200 товаров")
        offers = offers[:200]
    dimensions = 0
    offers_data = [
        {
            "categoryId": offer.get("mapping", {}).get("marketCategoryId", 0),
            "price": offer_data.get("basicPrice", {}).get("value", 0.0),
            "length": dimensions.get("length", 0),
            "width": dimensions.get("width", 0),
            "height": dimensions.get("height", 0),
            "weight": dimensions.get("weight", 0),
            "quantity": 1,
        }
        for offer in offers
        if (offer_data := offer.get("offer", {}))
        and (dimensions := offer_data.get("weightDimensions", {}))
    ]

    offers_dict = {
        index: (
            offer_.get("offer", {}).get("offerId", ""),
            offer_.get("offer", {}).get("basicPrice", {}).get("value", 0.0),
        )
        for index, offer_ in enumerate(offers)
    }

    commission = await ym_client.get_categories(
        campaign_id=campaign_id, offers=offers_data
    )
    # print(len(commission))

    commission_dict = {}
    for i, comm in enumerate(commission):
        tariffs = comm.get("tariffs", [])
        tariff_values = {
            "PRICE": 0.0,
            "FEE": {"current_amount": 0.0, "percent": 0.0},
            "AGENCY_COMMISSION": 0.0,
            "PAYMENT_TRANSFER": {"current_amount": 0.0, "percent": 0.0},
            "DELIVERY_TO_CUSTOMER": {
                "current_amount": 0.0,
                "percent": 0.0,
                "max_value": 0.0,
            },
            "CROSSREGIONAL_DELIVERY": 0.0,
            "EXPRESS_DELIVERY": {
                "current_amount": 0.0,
                "percent": 0.0,
                "min_value": 0.0,
                "max_value": 0.0,
            },
            "SORTING": 0.0,
            "MIDDLE_MILE": 0.0,
        }

        for tariff in tariffs:
            tariff_type = tariff.get("type")
            amount = tariff.get("amount", 0.0)
            parameters = tariff.get("parameters", [])

            if tariff_type == "FEE" and parameters:
                tariff_values["FEE"]["current_amount"] = amount
                tariff_values["FEE"]["percent"] = float(
                    get_value_by_name(parameters, "value")
                )

            elif tariff_type == "PAYMENT_TRANSFER" and parameters:
                tariff_values["PAYMENT_TRANSFER"]["current_amount"] = amount
                tariff_values["PAYMENT_TRANSFER"]["percent"] = float(
                    get_value_by_name(parameters, "value")
                )

            elif tariff_type == "DELIVERY_TO_CUSTOMER" and parameters:
                tariff_values["DELIVERY_TO_CUSTOMER"]["current_amount"] = amount
                tariff_values["DELIVERY_TO_CUSTOMER"]["percent"] = float(
                    get_value_by_name(parameters, "value")
                )
                tariff_values["DELIVERY_TO_CUSTOMER"]["max_value"] = float(
                    get_value_by_name(parameters, "maxValue")
                )

            elif tariff_type == "EXPRESS_DELIVERY" and parameters:
                tariff_values["EXPRESS_DELIVERY"]["current_amount"] = amount
                tariff_values["EXPRESS_DELIVERY"]["percent"] = float(
                    get_value_by_name(parameters, "value")
                )
                tariff_values["EXPRESS_DELIVERY"]["min_value"] = float(
                    get_value_by_name(parameters, "minValue")
                )
                tariff_values["EXPRESS_DELIVERY"]["max_value"] = float(
                    get_value_by_name(parameters, "maxValue")
                )

            elif tariff_type == "SORTING" and parameters:
                if (
                    get_value_by_name(parameters, "transitWarehouseType")
                    == ya_settings.transit_warehouse_type
                ):
                    tariff_values["SORTING"] = amount

            elif tariff_type in tariff_values:
                tariff_values[tariff_type] = amount

        tariff_values["PRICE"] = offers_dict[i][1]
        article = offers_dict[i][0]

        commission_dict[article] = tariff_values

    return commission_dict


async def chunked_offers_list(
    func, ym_client, campaign_id, data: list, chunk_size: int = 200
):
    result = {}
    for i in range(0, len(data), chunk_size):
        chunk_data = data[i: i + chunk_size]
        result = {**result, **await func(ym_client, campaign_id, chunk_data)}
    return result


if __name__ == "__main__":
    ms_token, _, ym_token = get_api_tokens()

    async def main():
        async with YM(api_key=ym_token, max_rete=45, time_period=3) as ym_client:
            start_time = time.time()

            campaign_id, business_id = await get_ya_campaign_and_business_ids(
                ym_client, fbs=True
            )
            offers = await ym_client.get_full_offers(business_id)
            print(len(offers))

            offers_commission_dict = await chunked_offers_list(
                get_dict_for_commission,
                ym_client=ym_client,
                campaign_id=campaign_id,
                data=offers,
                chunk_size=200,
            )

            print(offers_commission_dict)
            print(len(offers_commission_dict))


            print(time.time() - start_time)

    asyncio.run(main())
