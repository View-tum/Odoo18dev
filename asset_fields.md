# ???????????????????? account.asset (??? Server 10.0.0.14)

| ????????? (Technical Name) | ?????? (Type) | ??????????? (Label/String) |
|---|---|---|
| analytic_distribution | json | Analytic Distribution |
| analytic_precision | integer | Analytic Precision |
| distribution_analytic_account_ids | many2many | Distribution Analytic Account |
| activity_ids | one2many | Activities |
| activity_state | selection | Activity State |
| activity_user_id | many2one | Responsible User |
| activity_type_id | many2one | Next Activity Type |
| activity_type_icon | char | Activity Type Icon |
| activity_date_deadline | date | Next Activity Deadline |
| my_activity_date_deadline | date | My Activity Deadline |
| activity_summary | char | Next Activity Summary |
| activity_exception_decoration | selection | Activity Exception Decoration |
| activity_exception_icon | char | Icon |
| activity_calendar_event_id | many2one | Next Activity Calendar Event |
| message_is_follower | boolean | Is Follower |
| message_follower_ids | one2many | Followers |
| message_partner_ids | many2many | Followers (Partners) |
| message_ids | one2many | Messages |
| has_message | boolean | Has Message |
| message_needaction | boolean | Action Needed |
| message_needaction_counter | integer | Number of Actions |
| message_has_error | boolean | Message Delivery error |
| message_has_error_counter | integer | Number of errors |
| message_attachment_count | integer | Attachment Count |
| rating_ids | one2many | Ratings |
| website_message_ids | one2many | Website Messages |
| message_has_sms_error | boolean | SMS Delivery error |
| depreciation_entries_count | integer | # Posted Depreciation Entries |
| gross_increase_count | integer | # Gross Increases |
| total_depreciation_entries_count | integer | # Depreciation Entries |
| name | char | Asset Name |
| company_id | many2one | Company |
| country_code | char | Country Code |
| currency_id | many2one | Currency |
| state | selection | Status |
| active | boolean | Active |
| method | selection | Method |
| method_number | integer | Duration |
| method_period | selection | Number of Months in a Period |
| method_progress_factor | float | Declining Factor |
| prorata_computation_type | selection | Computation |
| prorata_date | date | Prorata Date |
| paused_prorata_date | date | Paused Prorata Date |
| account_asset_id | many2one | Fixed Asset Account |
| asset_group_id | many2one | Asset Group |
| account_depreciation_id | many2one | Depreciation Account |
| account_depreciation_expense_id | many2one | Expense Account |
| journal_id | many2one | Journal |
| original_value | monetary | Original Value |
| book_value | monetary | Book Value |
| value_residual | monetary | Depreciable Value |
| salvage_value | monetary | Not Depreciable Value |
| salvage_value_pct | float | Not Depreciable Value Percent |
| total_depreciable_value | monetary | Total Depreciable Value |
| gross_increase_value | monetary | Gross Increase Value |
| non_deductible_tax_value | monetary | Non Deductible Tax Value |
| related_purchase_value | monetary | Related Purchase Value |
| depreciation_move_ids | one2many | Depreciation Lines |
| original_move_line_ids | many2many | Journal Items |
| asset_properties_definition | properties_definition | Model Properties |
| asset_properties | properties | Properties |
| acquisition_date | date | Acquisition Date |
| disposal_date | date | Disposal Date |
| model_id | many2one | Model |
| account_type | selection | Type of the account |
| display_account_asset_id | boolean | Display Account Asset |
| parent_id | many2one | Parent |
| children_ids | one2many | Children |
| already_depreciated_amount_import | monetary | Already Depreciated Amount Import |
| asset_lifetime_days | float | Asset Lifetime Days |
| asset_paused_days | float | Asset Paused Days |
| net_gain_on_sale | monetary | Net gain on sale |
| linked_assets_ids | one2many | Linked Assets |
| count_linked_asset | integer | Count Linked Asset |
| warning_count_assets | boolean | Warning Count Assets |
| id | integer | ID |
| display_name | char | Display Name |
| create_uid | many2one | Created by |
| create_date | datetime | Created on |
| write_uid | many2one | Last Updated by |
| write_date | datetime | Last Updated on |
| responsible_id | many2one | Responsible |
| asset_location | char | Asset Location |
| asset_location_id | many2one | Asset Location |
| last_post_depreciation_date | date | Last Post Depreciation Date |
| vehicle_id | many2one | Vehicle |
| asset_register_number | char | เลขทะเบียนคุม FIX ASSET |
| related_asset_ids | many2many | Related Assets |
| child_asset_ids | many2many | Child Assets |
| is_parent_asset | boolean | Is Parent Asset |
| is_child_asset | boolean | Is Child Asset |
| child_count | integer | Child Asset Count |
| has_child_assets | boolean | Has Child Assets |
| hierarchy_related_asset_ids | many2many | Related Assets (Hierarchy) |
| linked_loans_ids | one2many | Related Loans |
| count_linked_loans | integer | Count Linked Loans |
| bill_move_id | many2one | Vendor Bill |
| total_group_value | monetary | Total Group Value |
| x_studio_accum_depreciation | integer | Accum Depreciation |
