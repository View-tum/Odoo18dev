{
    "name": "Auto Sequence (Monthly Autopilot)",
    "version": "18.0.1.0",
    "summary": "Automatically creates monthly date ranges for sequences (zero-touch).",
    "author": "Piyawat K.",
    "license": "LGPL-3",
    "depends": [
        "base",
        "oi_base",
        "base_sequence_option",
    ],
    "data": [
        "security/ir.model.access.csv",
        "wizard/generate_sequence_wizard.xml",
        "views/ir_sequence_view.xml",
        "data/ir_cron.xml",
    ],
    "installable": True,
    "application": False
}
