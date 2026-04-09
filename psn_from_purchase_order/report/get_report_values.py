# -*- coding: utf-8 -*-
import base64
from io import BytesIO
from PIL import Image
from odoo import models
import logging
_logger = logging.getLogger(__name__)

class ReportLetterhead(models.AbstractModel):
    _name = 'report.psn_from_purchase_order.report_page'


    def _get_report_values(self, docids, data=None):
        docs = self.env['purchase.order'].browse(docids)
        # Prepare any data you need for the report
        company = self.env.user.company_id
        logo_binary = company.logo

        if not logo_binary:
            return {
                'logo_data_uri': None,
                'image_height': None,
        }

        try:
            
            logo_image = Image.open(BytesIO(base64.b64decode(logo_binary)))

            image_height = logo_image.height  # Get the height in pixels
            calculate_DPL = int(image_height / 96)
            paper_format = self.env.ref('psn_from_purchase_order.paper_format_psn_from_purchase_order_report')
            if calculate_DPL > 5:
                if paper_format:
                    margin_top_new = paper_format.margin_top + calculate_DPL - 1
                    header_spacing_new = paper_format.header_spacing + calculate_DPL - 1
                    paper_format.write({'margin_top': margin_top_new})
                    paper_format.write({'header_spacing': header_spacing_new})
            else:
                paper_format.write({'margin_top': 61})
                paper_format.write({'header_spacing': 59})
            

            return {
                'doc_ids': docids,
                'doc_model': self.env['purchase.order'],
                'data': data,
                'docs': docs,
                'image_height': image_height
            }

        except Image as e:
            # Handle if PIL cannot identify the image
            _logger.error(f"Error loading logo image: {e}")
            return {
                'doc_ids': docids,
                'doc_model': self.env['purchase.order'],
                'data': data,
                'docs': docs,
                'logo_data_uri': None,
                'image_height': None,
            }