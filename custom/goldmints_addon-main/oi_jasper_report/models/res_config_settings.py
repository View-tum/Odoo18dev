# -*- coding: utf-8 -*-
'''
Created on Jun 8, 2020

@author: Zuhair Hammadi
'''
from odoo import models, fields
import requests

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    jasper_report_url = fields.Char("Jasper Report Server URL", config_parameter='jasper_report.url')
    jasper_report_user = fields.Char("Jasper Report Server User", config_parameter='jasper_report.user')
    jasper_report_password = fields.Char("Jasper Report Server Passowrd", config_parameter='jasper_report.password')
    jasper_post_chatter = fields.Boolean(string="Post to Chatter on Print", config_parameter='jasper_report.post_chatter', help="โพสต์ข้อความลง Chatter เมื่อมีการพิมพ์/พรีวิวรายงาน Jasper")
    
    def jasper_test(self):
        url = "%s/rest_v2/serverInfo" % self.jasper_report_url        
        try:
            res = requests.get(url, auth=(self.jasper_report_user, self.jasper_report_password))
            status = requests.status_codes._codes[res.status_code][0]
            notification_type = 'success' if res.status_code==200 else 'warning'
            
        except Exception as e:
            status = str(e)
            notification_type= 'danger'
            
        return {
            'type' : 'ir.actions.client',
            'tag' : 'display_notification',
            'params' : {
                'type': notification_type,
                'sticky' : True,
                'message' : status,
                'title' : 'Jasper Server Connection'                                
                }
            }        
