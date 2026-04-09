# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class DynamicCheque(models.Model):
	_name = 'dynamic.cheque'
	_description = "Dynamic Cheque"

	# format
	name = fields.Char(string="Cheque Format", required=True )
	partner_id = fields.Char(string="Partner")
	cheque_hight = fields.Float(string='Height')
	cheque_width = fields.Float(string='Width')

	# a/c pay
	# ac_pay = fields.Boolean(string="A/c Pay")
	ac_top_margin = fields.Float(string="Top Margin")
	ac_left_margin = fields.Float(string='Left Margin')
	ac_font_size = fields.Float(string='Font Size')
	ac_width = fields.Float(string='Width')
	ac_color = fields.Char(string='Color', default='black')

	# cheque date
	top_margin = fields.Float(string="Top Margin")
	left_margin = fields.Float(string='Left Margin')
	font_size = fields.Float(string="Font Size")
	char_spacing = fields.Float(string="Character Spacing")

	# payee name
	payee_top_margin = fields.Float(string='Top Margin')
	payee_left_margin = fields.Float(string='Left Margin')
	payee_width = fields.Float(string="Width")
	payee_font_size = fields.Float(string="Font Size")

	# amount in figure
	af_top_margin = fields.Float(string='Top Margin')
	af_left_margin = fields.Float(string='Left Margin')
	af_width = fields.Float(string="Width")
	af_font_size = fields.Float(string="Font Size")
	# af_currency_symbol = fields.Boolean(string="Currency Symbol")
	# af_currency_symbol_position = fields.Selection([('before','Before'),('after','After')],string="Currency Symbol Position", default='before')

	# amount in word
	first_line_amount = fields.Char(string='First Line')
	second_line_amount = fields.Char(string='Second Line')
	fl_top_margin = fields.Float(string='First Line Top Margin')
	fl_left_margin = fields.Float(string='First Line Left Margin')
	fl_width = fields.Float(string="First Line Width")
	words_in_fl_line = fields.Integer(string="No. of Word in First Line")
	sc_top_margin = fields.Float(string='Second Line Top Margin')
	sc_left_margin = fields.Float(string='Second Line Left Margin')
	sc_width = fields.Float(string='Second Line Width')
	words_in_sc_line = fields.Integer(string='No. of Word in Second Line')
	sc_font_size = fields.Float(string='Font Size')
	sc_currency_name = fields.Boolean(string='Currency Name')
	sc_currency_name_position = fields.Selection([('before','Before'),('after','After')], string="Position", default='before')

	# company
	comapny_name = fields.Boolean(string='Company Name')
	comp_font_size = fields.Float(string='Font Size')
	comp_top_margin = fields.Float(string="Top Margin")
	comp_left_margin = fields.Float(string="Left Margin")
	comp_width = fields.Float(string="Width")

	# signature box
	is_signature_box = fields.Boolean(string="Signature Box")
	sb_width = fields.Float(string='Width')
	sb_hight = fields.Float(string='Height')
	sb_top_margin = fields.Float(string='Top Margin')
	sb_left_margin = fields.Float(string='Left Margin')

	# origin date
	is_origin_date = fields.Boolean(string="Origin Date")
	od_top_margin = fields.Float(string="Top Margin")
	od_left_margin = fields.Float(string='Left Margin')
	od_font_size = fields.Float(string='Font Size')

	# origin pay to
	is_origin_pay_to = fields.Boolean(string="Origin Pay To")
	opt_top_margin = fields.Float(string="Top Margin")
	opt_left_margin = fields.Float(string='Left Margin')
	opt_font_size = fields.Float(string='Font Size')
	opt_width = fields.Float(string="Width")

	# origin pay date
	is_origin_pay_date = fields.Boolean(string="Origin Pay Date")
	opd_top_margin = fields.Float(string="Top Margin")
	opd_left_margin = fields.Float(string='Left Margin')
	opd_font_size = fields.Float(string='Font Size')

	# origin amount
	is_origin_amount = fields.Boolean(string="Origin Amount")
	oa_top_margin = fields.Float(string="Top Margin")
	oa_left_margin = fields.Float(string='Left Margin')
	oa_font_size = fields.Float(string='Font Size')
	oa_width = fields.Float(string="Width")

	# origin remark
	is_origin_remark = fields.Boolean(string="Origin Remark")
	or_top_margin = fields.Float(string="Top Margin")
	or_left_margin = fields.Float(string='Left Margin')
	or_font_size = fields.Float(string='Font Size')
	or_width = fields.Float(string="Width")

	# line
	is_line = fields.Boolean(string="Line")
	line_top_margin = fields.Float(string="Top Margin")
	line_left_margin = fields.Float(string='Left Margin')
	line_width = fields.Float(string='Width')
	line_size = fields.Float(string='Size')
	line_color = fields.Char(string='Color')
	line_rotate = fields.Float(string='Rotate')
