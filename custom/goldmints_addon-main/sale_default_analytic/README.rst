==============================
Sale Default Analytic Distribution
==============================

This module allows you to configure a default Analytic Account in the Sales Settings.

Features
========

* Adds a "Default Sale Analytic Account" field in **Settings > Sales > Analytic Accounting**.
* Automatically applies this analytic account to new Sale Order Lines when a product is selected, if no other specific distribution rule matches.

Configuration
=============

1. Go to **Settings > Sales**.
2. Scroll down to the **Analytic Accounting** section.
3. Select a **Default Sale Analytic Account**.
4. Save.

Usage
=====

1. Create a new **Sale Order**.
2. Add a **Product**.
3. The **Analytic Distribution** column will automatically populate with the default account (100%), unless a more specific Analytic Distribution Model overrides it.
