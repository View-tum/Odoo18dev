import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

class TmpProdJournalTable(models.Model):
    _inherit = 'tmp.prod.journal.table'

    def action_import_incremental(self):
        # 1. เตรียม Picking Type (ทำครั้งเดียวนอกลูป)
        picking_type = self.env['stock.picking.type'].search([
            ('name', 'ilike', 'Report as finish')
        ], limit=1)

        if not picking_type:
            raise UserError("ไม่พบ Operation Type ที่ชื่อ 'Report as finish'")

        for header in self:
            try:
                # [CRITICAL FIX] เริ่มต้น Savepoint
                # ห้ามมีคำสั่ง commit() ภายใน Block นี้เด็ดขาด!
                with self.env.cr.savepoint():
                    
                    # --- Logic ภายใน Savepoint ---
                    lines_to_process = self.env['tmp.prod.journal.prod'].search([
                        ('ax_journal_id', '=', header.ax_journal_id),
                        ('is_imported', 'in', ['draft', 'error']),
                    ])

                    if not lines_to_process:
                        if header.is_imported != 'imported':
                            header.write({'is_imported': 'imported', 'error_log': False})
                        # ถ้าไม่มี Line ให้ทำ ก็จบ Block นี้ไปแบบปกติ (ไปบรรทัด commit ด้านล่าง)
                    
                    else:
                        # 2. จัดการ Picking Header
                        picking = self.env['stock.picking'].search([
                            ('origin', '=', header.ax_journal_id),
                            ('state', 'not in', ('done', 'cancel')),
                            ('picking_type_id', '=', picking_type.id)
                        ], limit=1)

                        if not picking:
                            picking = self.env['stock.picking'].create({
                                'picking_type_id': picking_type.id,
                                'origin': header.ax_journal_id,
                                'ax_report_as_finish': header.ax_journal_id,
                                'ax_description': header.ax_description,
                                'ax_prod_id': header.ax_prod_id,
                                'location_id': picking_type.default_location_src_id.id,
                                'location_dest_id': picking_type.default_location_dest_id.id,
                                'scheduled_date': fields.Datetime.now(),
                            })

                        # 3. Loop Lines
                        for line in lines_to_process:
                            # CHECK 1: ยอดติดลบ -> Raise Error เพื่อให้ Savepoint Rollback ทันที
                            if line.ax_quantity < 0:
                                raise ValidationError(f"Quantity ติดลบ ({line.ax_quantity})")

                            if line.ax_transdate:
                                picking.write({'scheduled_date': line.ax_transdate})

                            product_code = line.ax_item_id[-5:] if line.ax_item_id else ''
                            if not product_code:
                                raise ValidationError(f"Line {line.ax_line_num}: Item ID เป็นค่าว่าง")

                            product = self.env['product.product'].search([
                                ('old_default_code', '=', product_code)
                            ], limit=1)

                            if not product:
                                raise ValidationError(f"Line {line.ax_line_num}: ไม่พบสินค้า Code {product_code}")

                            # Create Move
                            move = self.env['stock.move'].create({
                                'name': product.name,
                                'product_id': product.id,
                                'product_uom_qty': line.ax_quantity,
                                'product_uom': product.uom_id.id,
                                'picking_id': picking.id,
                                'location_id': picking.location_id.id,
                                'location_dest_id': picking.location_dest_id.id,
                                'picking_type_id': picking_type.id,
                                'state': 'draft',
                                'ax_invent_trans': line.ax_invent_trans_id,
                                'date': line.ax_transdate or fields.Datetime.now()
                            })
                            
                            move._action_confirm()

                            # Fix Ghost Line
                            ghost_lines = move.move_line_ids.filtered(lambda l: not l.lot_name and not l.lot_id)
                            if ghost_lines:
                                ghost_lines.unlink()

                            # Create Real Line
                            self.env['stock.move.line'].create({
                                'move_id': move.id,
                                'picking_id': picking.id,
                                'product_id': product.id,
                                'qty_done': line.ax_quantity, 
                                'lot_name': line.ax_invent_batch_id or False,
                                'location_id': picking.location_id.id,
                                'location_dest_id': picking.location_dest_id.id,
                                'date': line.ax_transdate or fields.Datetime.now(),
                            })

                            line.write({
                                'is_imported': 'imported',
                                'imported_date': fields.Datetime.now(),
                                'error_log': False
                            })
                        
                        # Confirm Header
                        if picking.state == 'draft':
                            picking.action_confirm()

                        header.write({
                            'is_imported': 'imported',
                            'imported_date': fields.Datetime.now(),
                            'error_log': False
                        })

                # --- จบ Block Savepoint (Success) ---
                # ถ้า Code วิ่งมาถึงตรงนี้ได้ แปลว่าไม่มี Error ใน Savepoint
                # เราจึง Commit ข้อมูลที่ถูกต้องลง Database
                self.env.cr.commit()

            except Exception as e:
                # --- กรณีเกิด Error (Failure) ---
                # 1. Savepoint จะ Rollback ข้อมูลข้างบนทิ้งให้อัตโนมัติ (Picking/Move ที่สร้างครึ่งๆกลางๆ จะหายไป)
                # 2. Transaction กลับมาสะอาด พร้อมให้เราบันทึก Error Log

                msg = str(e)
                _logger.error(f"Import Error Journal {header.ax_journal_id}: {msg}")
                
                # เขียน Log ลง Header
                header.write({
                    'is_imported': 'error',
                    'error_log': msg
                })
                
                # Commit เพื่อบันทึก "สถานะ Error" นี้ลง Database ทันที
                # เพื่อให้ Header ถัดไปเริ่มทำงานต่อได้
                self.env.cr.commit()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Processing Complete',
                'message': 'ดำเนินการเรียบร้อยแล้ว',
                'type': 'success',
                'sticky': False,
            }
        }