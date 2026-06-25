import datetime
import logging

import requests

from odoo import _, fields, models
from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)

BOT_API_KEY_PARAMETER = "currency_rate_bot_buying_transfer.api_key"
BOT_DAILY_AVERAGE_ENDPOINT = (
    "https://gateway.api.bot.or.th/Stat-ExchangeRate/v2/DAILY_AVG_EXG_RATE/"
)


class ResCompany(models.Model):
    _inherit = "res.company"

    currency_provider = fields.Selection(
        selection_add=[
            ("bot_buying_transfer", "[TH] BOT - Average Buying Transfer Rate")
        ],
        ondelete={"bot_buying_transfer": "set null"},
    )

    def _parse_bot_buying_transfer_data(self, available_currencies):
        api_key = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param(BOT_API_KEY_PARAMETER)
        )
        if not api_key:
            raise UserError(
                _("Configure the BOT API Key before updating currency rates.")
            )

        end_date = fields.Date.today()
        start_date = end_date - datetime.timedelta(days=10)
        try:
            response = requests.get(
                BOT_DAILY_AVERAGE_ENDPOINT,
                headers={"Authorization": api_key, "Accept": "application/json"},
                params={
                    "start_period": fields.Date.to_string(start_date),
                    "end_period": fields.Date.to_string(end_date),
                },
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json()
            data_details = payload["result"]["data"]["data_detail"]
        except (requests.RequestException, ValueError, KeyError, TypeError) as error:
            _logger.error("Unable to retrieve BOT buying transfer rates: %s", error)
            raise UserError(
                _(
                    "Unable to retrieve the BOT Average Buying Transfer Rate. "
                    "Check the BOT API Key and try again."
                )
            ) from error

        if isinstance(data_details, dict):
            data_details = [data_details]
        if not isinstance(data_details, list):
            raise UserError(
                _("No usable BOT Average Buying Transfer Rate was returned.")
            )

        available_currency_names = set(available_currencies.mapped("name"))
        result = {}
        latest_period = False
        for data_detail in data_details:
            if not isinstance(data_detail, dict):
                continue
            currency = data_detail.get("currency_id")
            period = data_detail.get("period")
            try:
                rate = float(data_detail.get("buying_transfer") or 0.0)
            except (TypeError, ValueError):
                continue
            if currency not in available_currency_names or not period or rate <= 0:
                continue
            if not latest_period or period > latest_period:
                latest_period = period
            if currency not in result or period > result[currency][1]:
                result[currency] = (1.0 / rate, period)

        if not result:
            raise UserError(
                _("No usable BOT Average Buying Transfer Rate was returned.")
            )

        result["THB"] = (1.0, latest_period)
        return result
