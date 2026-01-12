# -*- coding: utf-8 -*-
from odoo import models, fields
import os
import csv
import shutil
from datetime import datetime
import requests
import logging
from docutils.nodes import entry

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # ===== Import revenue file =====
    his_file_path = fields.Char(string="Source path", config_parameter='his_file.path')
    his_file_name = fields.Char(string="File name", config_parameter='his_file.name')

    # his_destination_path = fields.Char(string="Destination path", config_parameter='his_destination.path')

    # ===== Method revenue import =====
    def file_test(self):
        print("===== file_test =====")
        file_path = self.his_file_path + self.his_file_name + ".csv"
        # destination_path = self.his_destination_path + self.his_file_name + datetime.now().strftime(
        #     "_import_%Y%m%d_%H%M%S") + ".csv"
        encoding = 'utf-8'
        try:

            if file_path:
                with open(file_path, mode='r', encoding=encoding) as file:
                    csv_reader = csv.reader(file)
                    next(csv_reader)  # Skip the first row
                    for row in csv_reader:
                        print(row)

            # ===== Move file to destination path =====
            print("file_path:", file_path)
            # print("destination_path:", destination_path)

            status = 'Test read csv file is OK.'
            notification_type = 'success'

        except FileNotFoundError:
            print("Source file or destination path not found.")
            status = "Source file or destination path not found."
            notification_type = 'danger'
        except PermissionError:
            print("Permission denied.")
            status = "Permission denied."
            notification_type = 'danger'
        except Exception as e:
            status = str(e)
            notification_type = 'danger'

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': notification_type,
                'sticky': True,
                'message': status,
                'title': 'Testing File'
            }
        }

    def manual_import(self):
        print("===== manual_import =====")
        file_path = self.his_file_path + self.his_file_name + ".csv"
        # destination_path = self.his_destination_path + self.his_file_name + datetime.now().strftime(
        #     "_import_%Y%m%d_%H%M%S") + ".csv"
        encoding = 'utf-8'

        thecool_receive_import = self.env["thecool.receive.import"]
        try:
            if file_path:
                with open(file_path, mode='r', encoding=encoding) as file:
                    csv_reader = csv.reader(file)
                    next(csv_reader)  # Skip the first row
                    for row in csv_reader:
                        print(row)

                        if row[0] == 'NULL':
                            state = None
                        else:
                            state = row[0]

                        if row[1] == 'NULL':
                            reference = None
                        else:
                            reference = row[1]

                        if row[2] == 'NULL':
                            old_system_number = None
                        else:
                            old_system_number = row[2]

                        if row[3] == 'NULL':
                            contact_id = None
                        else:
                            contact_id = row[3]

                        if row[4] == 'NULL':
                            picking_type = None
                        else:
                            picking_type = row[4]

                        if row[5] == 'NULL':
                            source_location = None
                        else:
                            source_location = row[5]

                        if row[6] == 'NULL':
                            destination_location = None
                        else:
                            destination_location = row[6]

                        if row[7] == 'NULL':
                            scheduled_date = None
                        else:
                            scheduled_date = row[7]

                        if row[8] == 'NULL':
                            source_document = None
                        else:
                            source_document = row[8]

                        if row[9] == 'NULL':
                            effective_date = None
                        else:
                            effective_date = row[9]

                        if row[10] == 'NULL':
                            date_done = None
                        else:
                            date_done = row[10]

                        if row[11] == 'NULL':
                            procurement_group = None
                        else:
                            procurement_group = row[11]

                        if row[12] == 'NULL':
                            line_number = None
                        else:
                            line_number = row[12]

                        if row[13] == 'NULL':
                            line_product_id = None
                        else:
                            line_product_id = row[13]

                        if row[14] == 'NULL':
                            line_scheduled_date = None
                        else:
                            line_scheduled_date = row[14]

                        if row[15] == 'NULL':
                            line_qty = None
                        else:
                            line_qty = row[15]

                        if row[16] == 'NULL':
                            line_state = None
                        else:
                            line_state = row[16]

                        if row[17] == 'NULL':
                            line_purchase_line_id = None
                        else:
                            line_purchase_line_id = row[17]


                        thecool_receive_import.create(
                            {
                                "state": state,
                                "reference": reference,
                                "old_system_number": old_system_number,
                                "contact_id": contact_id,
                                "picking_type": picking_type,
                                "source_location": source_location,
                                "destination_location": destination_location,
                                "scheduled_date": scheduled_date,
                                "source_document": source_document,
                                "effective_date": effective_date,
                                "date_done": date_done,
                                "procurement_group": procurement_group,
                                "line_number": line_number,
                                "line_product_id": line_product_id,
                                "line_scheduled_date": line_scheduled_date,
                                "line_qty": line_qty,
                                "line_state": line_state,
                                "line_purchase_line_id": line_purchase_line_id,
                            }
                        )

            # # ===== Move file to destination path =====
            # shutil.move(file_path, destination_path)

            status = 'Manual import is success.'
            notification_type = 'success'

        except FileNotFoundError:
            status = "Source file or destination path not found."
            notification_type = 'danger'
        except PermissionError:
            status = "Permission denied."
            notification_type = 'danger'
        except Exception as e:
            status = str(e)
            notification_type = 'danger'

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': notification_type,
                'sticky': True,
                'message': status,
                'title': 'Import File'
            }
        }
