from unittest.mock import Mock, patch

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestBotBuyingTransferProvider(TransactionCase):
    def setUp(self):
        super().setUp()
        self.company = self.env.company
        self.active_currencies = (
            self.env.ref("base.THB")
            | self.env.ref("base.USD")
            | self.env.ref("base.EUR")
        )
        self.parameter = "currency_rate_bot_buying_transfer.api_key"

    def test_provider_is_additive(self):
        selection = dict(
            self.env["res.company"].fields_get(["currency_provider"])[
                "currency_provider"
            ]["selection"]
        )

        self.assertIn("bot", selection)
        self.assertIn("bot_buying_transfer", selection)

    @patch(
        "odoo.addons.currency_rate_bot_buying_transfer.models.res_company.requests.get"
    )
    def test_parser_uses_latest_buying_transfer_rate(self, mock_get):
        self.env["ir.config_parameter"].sudo().set_param(self.parameter, "secret")
        response = Mock()
        response.json.return_value = {
            "result": {
                "data": {
                    "data_detail": [
                        {
                            "period": "2026-05-22",
                            "currency_id": "USD",
                            "buying_transfer": "31.9000",
                            "selling": "32.5000",
                        },
                        {
                            "period": "2026-05-25",
                            "currency_id": "USD",
                            "buying_transfer": "32.1234",
                            "selling": "32.8000",
                        },
                        {
                            "period": "2026-05-25",
                            "currency_id": "EUR",
                            "buying_transfer": "36.4000",
                            "selling": "37.1000",
                        },
                    ]
                }
            }
        }
        mock_get.return_value = response

        rates = self.company._parse_bot_buying_transfer_data(self.active_currencies)

        self.assertAlmostEqual(rates["USD"][0], 1.0 / 32.1234)
        self.assertEqual(rates["USD"][1], "2026-05-25")
        self.assertAlmostEqual(rates["EUR"][0], 1.0 / 36.4)
        self.assertEqual(rates["THB"], (1.0, "2026-05-25"))
        response.raise_for_status.assert_called_once_with()
        call_kwargs = mock_get.call_args.kwargs
        self.assertEqual(call_kwargs["headers"]["Authorization"], "secret")
        self.assertEqual(call_kwargs["timeout"], 30)

    def test_parser_requires_api_key(self):
        self.env["ir.config_parameter"].sudo().search(
            [("key", "=", self.parameter)]
        ).unlink()

        with self.assertRaises(UserError):
            self.company._parse_bot_buying_transfer_data(self.active_currencies)

    @patch(
        "odoo.addons.currency_rate_bot_buying_transfer.models.res_company.requests.get"
    )
    def test_parser_rejects_response_without_buying_transfer(self, mock_get):
        self.env["ir.config_parameter"].sudo().set_param(self.parameter, "secret")
        response = Mock()
        response.json.return_value = {
            "result": {
                "data": {
                    "data_detail": [
                        {
                            "period": "2026-05-25",
                            "currency_id": "USD",
                            "selling": "32.8000",
                        }
                    ]
                }
            }
        }
        mock_get.return_value = response

        with self.assertRaises(UserError):
            self.company._parse_bot_buying_transfer_data(self.active_currencies)

    @patch(
        "odoo.addons.currency_rate_bot_buying_transfer.models.res_company.requests.get"
    )
    def test_parser_rejects_rates_for_inactive_currencies_only(self, mock_get):
        self.env["ir.config_parameter"].sudo().set_param(self.parameter, "secret")
        response = Mock()
        response.json.return_value = {
            "result": {
                "data": {
                    "data_detail": [
                        {
                            "period": "2026-05-25",
                            "currency_id": "JPY",
                            "buying_transfer": "0.2100",
                        }
                    ]
                }
            }
        }
        mock_get.return_value = response

        with self.assertRaises(UserError):
            self.company._parse_bot_buying_transfer_data(self.active_currencies)
