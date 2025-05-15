Run Odoo - Open source ERP and CRM on Diploi

Diploi component for running Odoo version 18

- 💻 [Odoo](https://www.odoo.com/)
- 💿 [Diploi](https://www.diploi.com)

## Odoo

Based on Odoo version 18 docker with minor Diploi customizations.

Login to Odoo with user `admin`. An initial password is generated for every project. To find password, open Diploi project and check project options.

For the Odoo container there are separate ssh logins for users `odoo` and `root`. For security reasons there is no `sudo` from odoo to root. However
it is possible to restart odoo using command `supervistoctl restart odoo`

Custom modules are linked to git repository, hosted at `/mnt/extra-addons`. This folder is persisted
in the development version and non-persisted for staging and development.

Data folder `/var/lib/odoo` is persisted always
