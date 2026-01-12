# inventory_stock_card/utils/inventory_stock_card_utils.py
from odoo.tools.misc import formatLang as _formatLang
from datetime import datetime, date, time
import pytz
from odoo import fields

def fmt(env, value, dp=None, monetary=False, currency=None, digits=None, wizard=None):
    company_currency = wizard.company_id.currency_id if wizard else env.company.currency_id
    cur = currency or company_currency
    return _formatLang(env, value, digits=digits, monetary=monetary, dp=dp, currency_obj=cur)

def money(env, value, currency=None, wizard=None, show_symbol=True):
    company_currency = wizard.company_id.currency_id if wizard else env.company.currency_id
    cur = currency or company_currency
    num = _formatLang(env, value, dp="Account", monetary=False)
    if not show_symbol:
        return num
    return f"{num} {cur.symbol if cur else ''}".rstrip()

def qty(env, value, uom_name=None):
    try:
        if value == int(value):
            num_str = f"{int(value):,}"
        else:
            num_str = _formatLang(env, value, dp="Product Unit of Measure", monetary=False)
    except Exception:
        num_str = str(value)
    
    label = uom_name or ""
    return f"{num_str} {label}".rstrip()

def thdate(env, dt_in):
    if not dt_in:
        return ""
    if isinstance(dt_in, str):
        for fmt_str in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                dt_in = datetime.strptime(dt_in, fmt_str)
                break
            except Exception:
                pass
        else:
            return dt_in
    if isinstance(dt_in, date) and not isinstance(dt_in, datetime):
        dt_in = datetime.combine(dt_in, time.min)

    user_tz = pytz.timezone(env.user.tz or "UTC")
    if dt_in.tzinfo is None:
        dt_in = pytz.UTC.localize(dt_in)
    dt_local = dt_in.astimezone(user_tz)
    year_be = dt_local.year + 543
    return dt_local.strftime(f"%d/%m/{year_be} %H:%M:%S")

def local_midnight_to_utc_naive(env, d):
    d = d.date() if isinstance(d, datetime) else d
    user_tz = pytz.timezone(env.user.tz or 'UTC')
    local_dt = user_tz.localize(datetime.combine(d, time.min))
    return local_dt.astimezone(pytz.UTC).replace(tzinfo=None)

def utc_naive_to_local_naive(env, dt):
    if not dt:
        return None
    if isinstance(dt, str):
        try:
            dt = fields.Datetime.from_string(dt)
        except Exception:
            try:
                dt = datetime.strptime(dt, "%Y-%m-%d")
                dt = datetime.combine(dt, time.min)
            except Exception:
                return None
    if dt.tzinfo is None:
        dt = pytz.UTC.localize(dt)
    user_tz = pytz.timezone(env.user.tz or "UTC")
    local_dt = dt.astimezone(user_tz)
    return local_dt.replace(tzinfo=None)