/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { MoOverviewOperationsBlock } from "@mrp/components/mo_overview_operations_block/mrp_mo_overview_operations_block";
import { MoOverviewLine } from "@mrp/components/mo_overview_line/mrp_mo_overview_line";

patch(MoOverviewOperationsBlock, {
    props: {
        ...MoOverviewOperationsBlock.props,
        summary: {
            ...MoOverviewOperationsBlock.props.summary,
            shape: {
                ...MoOverviewOperationsBlock.props.summary.shape,
                employee_cost: { type: Number, optional: true },
            },
        },
    },
});

patch(MoOverviewLine, {
    props: {
        ...MoOverviewLine.props,
        data: {
            ...MoOverviewLine.props.data,
            shape: {
                ...MoOverviewLine.props.data.shape,
                employee_cost: { type: [Number, Boolean], optional: true },
            },
        },
    },
});
