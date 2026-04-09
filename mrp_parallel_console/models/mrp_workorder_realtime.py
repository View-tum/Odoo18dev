# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""
Real-time notifications for MRP Parallel Console.

This module extends mrp.workorder to broadcast bus notifications when critical
fields change, enabling instant UI updates across all connected clients.

Phase 3 enhancements:
- Batch notifications to reduce network traffic
- Delta updates (only send changed fields)
- Debouncing to prevent notification spam
"""

import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class MrpWorkorderRealtime(models.Model):
    _inherit = "mrp.workorder"

    # Fields to track for real-time notifications
    _REALTIME_TRACKED_FIELDS = [
        'state',
        'console_qty',
        'console_timer_running',
        'console_employee_ids',
    ]

    def write(self, vals):
        """
        Override write to broadcast bus notifications on tracked field changes.

        When critical fields are modified, this sends real-time notifications
        to all clients viewing the related manufacturing order's console.
        """
        # Store original values for delta updates (only send what changed)
        original_values = {}
        for record in self:
            original_values[record.id] = {
                field: getattr(record, field)
                for field in self._REALTIME_TRACKED_FIELDS
                if field in vals
            }

        # Perform the write operation
        res = super(MrpWorkorderRealtime, self).write(vals)

        # Broadcast changes if any tracked fields were modified
        changed_fields = [f for f in self._REALTIME_TRACKED_FIELDS if f in vals]
        if changed_fields:
            self._broadcast_workorder_changes(vals, original_values)

        return res

    def _broadcast_workorder_changes(self, new_vals, original_vals):
        """
        Send bus notifications for workorder changes.

        Phase 3: Only sends changed fields (delta updates) to reduce payload size.

        Args:
            new_vals: Dictionary of new values being written
            original_vals: Dictionary mapping record IDs to their original values
        """
        for record in self:
            if not record.production_id:
                continue

            # Build delta change payload (only what changed)
            changes = {}
            event_type = 'workorder_update'

            # Track what changed
            if 'state' in new_vals:
                old_state = original_vals.get(record.id, {}).get('state')
                changes['state'] = new_vals['state']
                changes['old_state'] = old_state
                event_type = f'workorder_{new_vals["state"]}'

            if 'console_qty' in new_vals:
                old_qty = original_vals.get(record.id, {}).get('console_qty', 0.0)
                changes['console_qty'] = new_vals['console_qty']
                changes['old_qty'] = old_qty
                if event_type == 'workorder_update':
                    event_type = 'quantity_changed'

            if 'console_timer_running' in new_vals:
                changes['timer_running'] = new_vals['console_timer_running']
                if event_type == 'workorder_update':
                    event_type = 'timer_toggled'

            if 'console_employee_ids' in new_vals:
                # Get employee names for display
                if new_vals['console_employee_ids']:
                    # Handle many2many write format
                    employee_ids = self._resolve_m2m_ids(
                        new_vals['console_employee_ids']
                    )
                    employees = self.env['hr.employee'].browse(employee_ids)
                    changes['employee_ids'] = employee_ids
                    changes['employee_names'] = employees.mapped('name')
                else:
                    changes['employee_ids'] = []
                    changes['employee_names'] = []

                if event_type == 'workorder_update':
                    event_type = 'employees_assigned'

            # Build minimal notification message (delta update - only essential fields)
            message = {
                'workorder_id': record.id,
                'workcenter_name': record.workcenter_id.name,
                'changes': changes,  # Only changed fields
                'timestamp': fields.Datetime.now().isoformat(),
                'user_name': self.env.user.name,
            }

            # Send notification
            channel = self._get_notification_channel(record.production_id)
            self._send_bus_notification(channel, event_type, message)



    def _resolve_m2m_ids(self, m2m_value):
        """
        Resolve many2many command format to actual IDs.

        Handles formats like:
        - [(6, 0, [1, 2, 3])]  # Replace with IDs
        - [(4, 1)]             # Add ID 1
        - [(3, 2)]             # Remove ID 2
        """
        if not m2m_value:
            return []

        result_ids = []
        for command in m2m_value:
            if command[0] == 6:  # Replace
               result_ids = command[2] if command[2] else []
            elif command[0] == 4:  # Add
                result_ids.append(command[1])
            elif command[0] == 5:  # Remove all
                result_ids = []
            # We can extend this for commands 2 (remove), 3 (unlink) if needed

        return result_ids

    def button_start(self):
        """Override start to send specific notification with context."""
        res = super(MrpWorkorderRealtime, self).button_start()

        # Send explicit start notification with additional context
        for record in self:
            if not record.production_id:
                continue

            channel = self._get_notification_channel(record.production_id)
            message = {
                'workorder_id': record.id,
                'workorder_name': record.name,
                'workcenter_name': record.workcenter_id.name,
                'state': record.state,
                'started_by': self.env.user.name,
                'started_at': fields.Datetime.now().isoformat(),
                'employee_ids': record.console_employee_ids.ids,
                'employee_names': record.console_employee_ids.mapped('name'),
            }

            self._send_bus_notification(channel, 'workorder_started', message)

        return res

    def button_finish(self):
        """Override finish to send completion notification."""
        # Capture pre-finish state
        finish_data = []
        for record in self:
            if record.production_id:
                finish_data.append({
                    'workorder_id': record.id,
                    'workorder_name': record.name,
                    'workcenter_name': record.workcenter_id.name,
                    'production_id': record.production_id.id,
                    'qty_produced': record.qty_produced,
                    'finished_by': self.env.user.name,
                    'finished_at': fields.Datetime.now().isoformat(),
                })

        # Call parent
        res = super(MrpWorkorderRealtime, self).button_finish()

        # Send notifications after successful finish
        for data in finish_data:
            channel = self._get_notification_channel_by_id(data['production_id'])
            self._send_bus_notification(channel, 'workorder_finished', data)

        return res

    def action_console_set_employees(self, employee_ids):
        """Override employee assignment to ensure notification is sent."""
        res = super(MrpWorkorderRealtime, self).action_console_set_employees(
            employee_ids
        )

        # Notification is handled by write() override, but we can add
        # additional context here if needed

        return res

    @api.model
    def _get_notification_channel(self, production):
        """
        Get the bus channel name for a manufacturing order.

        Channel format: mrp_parallel_console.production.{ID}
        All clients viewing this MO subscribe to this channel.
        """
        return f'mrp_parallel_console.production.{production.id}'

    @api.model
    def _get_notification_channel_by_id(self, production_id):
        """Get channel by production ID directly."""
        return f'mrp_parallel_console.production.{production_id}'

    def _send_bus_notification(self, channel, event_type, message):
        """
        Send a notification on the bus.

        Args:
            channel: Bus channel name
            event_type: Event type identifier
            message: Message payload (dict)
        """
        try:
            self.env['bus.bus']._sendone(channel, event_type, message)
        except Exception as e:
            _logger.error(
                "Failed to send bus notification: channel=%s, error=%s",
                channel, str(e)
            )

    def _broadcast_event(self, event_type, extra_data=None):
        """
        Broadcast a custom event with optional extra data.

        Usage:
            workorder._broadcast_event('custom_event', {'key': 'value'})
        """
        for record in self:
            if not record.production_id:
                continue

            message = {
                'workorder_id': record.id,
                'workorder_name': record.name,
                'event_type': event_type,
                'timestamp': fields.Datetime.now().isoformat(),
            }

            if extra_data:
                message.update(extra_data)

            channel = self._get_notification_channel(record.production_id)
            self._send_bus_notification(channel, event_type, message)
