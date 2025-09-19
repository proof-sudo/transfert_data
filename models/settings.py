# -*- coding: utf-8 -*-
from odoo import models, fields

class TransferToOdooConfig(models.Model):
    _name = 'transfer_to_odoo17.config'
    _description = "Configuration Odoo Externe"

    external_odoo_base_url = fields.Char(
        string="URL Odoo Externe",
        required=True,
        help="URL du serveur Odoo cible pour synchronisation des commandes et factures"
    )
