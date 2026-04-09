{
    "name": "WHT Cert Revenue Type",
    "version": "18.0.1.0.0",
    "author": "365 Piyawat K.k",
    "category": "Accounting",
    "depends": [
        "account",
        "l10n_th_account_wht_cert_form",
        "l10n_th_account_tax"
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/wht.revenue.type.csv",
        "views/wht_revenue_type_views.xml",
        "views/withholding_tax_cert_views.xml",
    ],
    "assets": {
        "web.report_assets_common": [
            "wht_cert_revenue_type/static/src/scss/report_wht_custom.scss",
        ],
    },
    "installable": True,
}