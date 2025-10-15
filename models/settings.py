# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import logging
from odoo.exceptions import UserError

_logger = logging.getLogger('odoo')

class TransferToOdooConfig(models.Model):
    _name = 'transfer_to_odoo17.config'
    _description = "Configuration Odoo Externe"

    external_odoo_base_url = fields.Char(
        string="URL Odoo Externe",
        help="URL du serveur Odoo cible pour synchronisation des commandes et factures",
        store=True
        
    )
    @classmethod
    def get_external_url(cls):
        config = cls.env['transfer_to_odoo17.config'].search([], limit=1)
        if not config or not config.external_odoo_base_url:
            _logger.error("Aucune URL externe configurée dans transfer_to_odoo17.config")
            raise UserError("Aucune URL Odoo externe n'est configurée.")
        return config.external_odoo_base_url.rstrip('/')
    
    def action_mark_existing_done(self):
        """Marquer toutes les commandes et factures existantes comme déjà transférées"""
        sale_orders = self.env['sale.order'].search([('state', '=', 'sale')])
        invoices = self.env['account.invoice'].search([('state', '=', 'open')])

        sale_orders.write({'transfer_state': 'done'})
        invoices.write({'transfer_state': 'done'})

        _logger.info(
            "🔹 Toutes les anciennes SaleOrders (%s) et Invoices (%s) ont été marquées comme transférées",
            len(sale_orders), len(invoices)
        )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Transfert mis à jour'),
                'message': _('Toutes les anciennes commandes et factures sont maintenant marquées comme transférées.'),
                'type': 'success',
                'sticky': False,
            }
        }
