/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class CalendarMultiSelect extends Component {
    static template = "partner_payment_schedule.CalendarMultiSelect";
    static props = {
        ...standardFieldProps,
    };

    setup() {
        const today = new Date();
        this.state = useState({
            currentYear: today.getFullYear(),
            currentMonth: today.getMonth(),
            selectedDates: this.parseSelectedDates(),
        });
    }

    parseSelectedDates() {
        const value = this.props.record.data[this.props.name];
        if (!value) return [];
        try {
            return JSON.parse(value);
        } catch {
            return [];
        }
    }

    get monthName() {
        const monthNames = [
            "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน",
            "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม",
            "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"
        ];
        return monthNames[this.state.currentMonth];
    }

    get daysInMonth() {
        const year = this.state.currentYear;
        const month = this.state.currentMonth;
        const firstDay = new Date(year, month, 1).getDay();
        const daysCount = new Date(year, month + 1, 0).getDate();

        const days = [];
        for (let i = 0; i < firstDay; i++) {
            days.push({ day: null, dateStr: null });
        }
        for (let d = 1; d <= daysCount; d++) {
            const dateStr = this.formatDate(year, month, d);
            days.push({ day: d, dateStr });
        }
        return days;
    }

    formatDate(year, month, day) {
        const m = String(month + 1).padStart(2, "0");
        const d = String(day).padStart(2, "0");
        return `${year}-${m}-${d}`;
    }

    isSelected(dateStr) {
        return this.state.selectedDates.includes(dateStr);
    }

    onDayClick(ev) {
        const dateStr = ev.currentTarget.dataset.date;
        this.toggleDate(dateStr);
    }

    toggleDate(dateStr) {
        if (!dateStr) return;
        const idx = this.state.selectedDates.indexOf(dateStr);
        if (idx >= 0) {
            this.state.selectedDates.splice(idx, 1);
        } else {
            this.state.selectedDates.push(dateStr);
            this.state.selectedDates.sort();
        }
        this.updateValue();
    }

    updateValue() {
        const jsonValue = JSON.stringify(this.state.selectedDates);
        this.props.record.update({ [this.props.name]: jsonValue });
    }

    prevMonth() {
        if (this.state.currentMonth === 0) {
            this.state.currentMonth = 11;
            this.state.currentYear--;
        } else {
            this.state.currentMonth--;
        }
    }

    nextMonth() {
        if (this.state.currentMonth === 11) {
            this.state.currentMonth = 0;
            this.state.currentYear++;
        } else {
            this.state.currentMonth++;
        }
    }
}

registry.category("fields").add("calendar_multiselect", {
    component: CalendarMultiSelect,
    supportedTypes: ["text", "char"],
});
