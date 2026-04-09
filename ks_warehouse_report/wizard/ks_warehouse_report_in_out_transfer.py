from odoo import api, fields, models
from odoo.exceptions import ValidationError

import xlwt
import base64
from io import BytesIO


class KSWarehouseReporttransfers(models.Model):
    _name = "ks.warehouse.report.transfer"
    _description = "Stock transfers / Stock Report"

    ks_report = {'product_code': 0, 'product_type': 1, 'product_categ_id': 2, 'product_name': 3, 'location_id': 4,
                 'company_id': 5, 'product_sales_price': 6, 'product_qty_available': 7, 'product_id': 8}
    kr_in_dates = {'product_id': 0, 'location_id': 1, 'company_id': 2, 'opening_stock': 3, 'closing_stock': 4,
                   'qty_date': 5}

    ks_name = fields.Char(default='Stock transfer Report')
    ks_date_from = fields.Date('Start Date', required=True)
    ks_date_to = fields.Date('End Date', required=True)
    ks_company_id = fields.Many2one('res.company', 'Company', required=True,
                                    default=lambda self: self.env.company)

    def ks_action_generate_report(self):
        return True

    
    def ks_generate_xlsx_report(self):
        report_name = self.ks_name
        workbook = xlwt.Workbook()
        header = xlwt.easyxf('font: name Times New Roman bold on;align: vert centre, horiz center;'
                             'borders:top double;font: height 350, bold on')
        header_small = xlwt.easyxf('font: name Times New Roman bold on;align: vert centre, horiz center;'
                                   'borders:top double;font: height 200, bold on')
        column_style = xlwt.easyxf('font: name Times New Roman bold on;align: vert centre, horiz center, wrap yes;'
                                   'borders: top medium,right medium,bottom medium,left medium;'
                                   'font: height 180, bold on')
        style0 = xlwt.easyxf('font: name Times New Roman bold on;align: horiz center;')

        sheet = workbook.add_sheet(str(report_name))

        sheet.panes_frozen = True  # freeze headers
        sheet.remove_splits = True
        sheet.horz_split_pos = 10  # freeze upto 10 rows

        # sheet template
        sheet.write_merge(0, 1, 0, 20, str(report_name), header)
        sheet.write_merge(2, 2, 0, 20, "COMPANY : " + self.ks_company_id.name, header_small)
        sheet.write(3, 7, 'FROM :', column_style)
        sheet.write_merge(3, 3, 8, 9, str(self.ks_date_from), column_style)
        sheet.write(3, 10, 'TO :', column_style)
        sheet.write_merge(3, 3, 11, 12, str(self.ks_date_to), column_style)
        sheet.write_merge(5, 7, 0, 20, "REPORT", header_small)
        # sheet.write_merge(7, 7, 0, 20, self.warehouse_id.name, header)

        sheet.write_merge(8, 9, 0, 0, "S.NO", column_style)
        sheet.write_merge(8, 9, 1, 1, "Reference/Code", column_style)
        sheet.write_merge(8, 9, 2, 2, "Type", column_style)
        sheet.write_merge(8, 9, 3, 3, "Category", column_style)
        sheet.write_merge(8, 9, 4, 4, "Product", column_style)
        sheet.write_merge(8, 9, 5, 5, "Location", column_style)
        # sheet.write_merge(8, 9, 6, 6, "Warehouse", column_style)
        sheet.write_merge(8, 9, 6, 6, "Company", column_style)
        sheet.write_merge(8, 9, 7, 7, "Operation Types", column_style)
        sheet.write_merge(8, 9, 8, 8, "Status", column_style)

        # get qty available
        self.env.cr.execute("""
        SELECT ks_product_code,ks_product_type,ks_product_categ_id,ks_product_name,ks_location_id,ks_company_id,
               ks_product_sales_price, ks_product_qty_available, ks_product_id 
        FROM ks_warehouse_report 
        WHERE ks_company_id = %s and ks_product_qty_available != 0
        order by ks_location_id
        """ % self.ks_company_id.id)

        datas = self.env.cr.fetchall()
        if not datas:
            raise ValidationError(_("Opps! There are no data."))

        dates_in = self.ks_data_in_date()

        datas = self.ks_merge_data(datas, dates_in)

        datas = self.ks_apply_filter(datas)

        if datas:
            i = 1;
            row = 10;
            col = 0
            for data in datas:
                sheet.write(row, 0, i, style0)
                sheet.write(row, 1, data[0], style0)
                if data[1] == 'consu':
                    sheet.write(row, 2, 'Stockable', style0)
                elif data[1] == 'service':
                    sheet.write(row, 2, 'Consumable', style0)
                if data[2]:
                    catge_id = self.env['product.category'].browse(int(data[2]))
                sheet.write(row, 3, catge_id.name, style0)
                sheet.write(row, 4, data[3], style0)
                if data[4]:
                    location_id = self.env['stock.location'].browse(int(data[4]))
                sheet.write(row, 5, location_id.display_name, style0)
                # sheet.write(row, 6, 'WH', style0)
                if data[5]:
                    comp_id = self.env['res.company'].browse(int(data[5]))
                sheet.write(row, 6, comp_id.name, style0)
                sheet.write(row, 7, data[6], style0)
                sheet.write(row, 8, data[7], style0)

                row += 1
                i += 1
        # Save workbook into an in-memory buffer to avoid filesystem permission issues
        output = BytesIO()
        workbook.save(output)
        output.seek(0)
        file_data = output.read()
        out = base64.encodebytes(file_data)

        # Files actions
        attach_vals = {
            'report_name': str(report_name) + '.xlsx',
            'datas': out,
        }

        act_id = self.env['ks.warehouse.report.transfer.out'].create(attach_vals)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'ks.warehouse.report.transfer.out',
            'res_id': act_id.id,
            'view_type': 'form',
            'view_mode': 'form',
            'context': self.env.context,
            'target': 'new',
        }

    
    def ks_data_in_date(self):
        # get the stock_quant data via date in query
        ks_date_from = fields.Datetime.to_datetime(self.ks_date_from)
        self.env.cr.execute("""
        select sq.product_id, sq.location_id, sq.company_id,
        sum(case when sq.in_date <= '%s' then sq.quantity else 0 end) as opening_stock,
        sum(sq.quantity) as closing_stock, 
        sum(case when sq.in_date >= '%s' then  sq.quantity else 0 end) as qty_date
        from stock_quant as sq
            LEFT JOIN stock_location as sl ON sl.id = sq.location_id
        where sl.usage = 'internal' 
            and sq.company_id = '%s'
            and sq.in_date <= '%s'
        group by sq.product_id, sq.location_id, sq.company_id
        """ % (ks_date_from, ks_date_from, self.ks_company_id.id, fields.Datetime.to_datetime(self.ks_date_to)))

        dates_in = self.env.cr.fetchall()
        if not dates_in:
            raise ValidationError(_("Opps! There are no data."))
        return dates_in

    
    def ks_merge_data(self, datas, dates_in):
        ks_list = []
        kr = self.ks_report
        kid = self.kr_in_dates
        for date in dates_in:
            for data in datas:
                if data[kr['product_id']] == date[kid['product_id']] and data[kr['location_id']] == date[
                    kid['location_id']] \
                        and data[kr['company_id']] == date[kid['company_id']]:
                    ks_cost = self.env['product.product'].browse(
                        date[kid['product_id']]).product_tmpl_id.standard_price
                    ks_list.append(
                        (data[kr['product_id']], data[kr['product_type']], data[kr['product_categ_id']],
                         data[kr['product_name']], data[kr['location_id']], data[kr['company_id']],
                         date[kid['qty_date']], ks_cost, data[kr['product_sales_price']],
                        )
                    )
        if not ks_list:
            raise ValidationError(_("Opps! There are no data."))
        return ks_list

    
    def ks_apply_filter(self, data):
            ks_data = data
            if not ks_data:
                raise ValidationError(_("Opps! There are no data."))
            return ks_data


    class KSWarehouseReporttransferOUT(models.Model):
        _name = "ks.warehouse.report.transfer.out"
        _description = "Stock transfer report Out"

        datas = fields.Binary('File', readonly=True)
        report_name = fields.Char('Report Name', readonly=True)
