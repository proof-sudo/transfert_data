# -*- coding: utf-8 -*-
from odoo import models, api, fields
import logging
import requests
import json

_logger = logging.getLogger(__name__)

class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    transfer_state = fields.Selection([
        ('pending', 'Pending'),
        ('done', 'Done')
    ], string="Transfer State", default='pending')

    @api.multi
    def action_invoice_open(self):
        """Marque l'envoi comme pending; l'action serveur se chargera de l'envoi"""
        res = super(AccountInvoice, self).action_invoice_open()
        for invoice in self:
            _logger.info("Invoice %s validée, transfert prévu via Action Server", invoice.number)
            invoice.transfer_state = 'pending'
        return res

    @api.multi
    def send_invoice_to_external_odoo(self):
        """Méthode appelée par l'Action Serveur"""
        for invoice in self:
            try:
                fields = list(invoice._fields.keys())
                data = invoice.read(fields)[0]

                config = self.env['transfer_to_odoo17.config'].sudo().search([], limit=1)
                base_url = config.external_odoo_base_url if config else False

                if not base_url:
                    _logger.error("Aucune URL configurée. Invoice %s non envoyé", invoice.number)
                    continue

                url = "{}/odoo_sync/account_invoice".format(base_url)
                headers = {"Content-Type": "application/json"}

                _logger.info("Données à envoyer pour Invoice %s : %s", invoice.number, json.dumps(data, indent=2, default=str))
                response = requests.post(url, headers=headers, data=json.dumps(data, default=str), timeout=15)

                if response.status_code == 200:
                    _logger.info("Invoice %s envoyé avec succès", invoice.number)
                    invoice.transfer_state = 'done'
                else:
                    _logger.error("Erreur %s envoi Invoice %s : %s", response.status_code, invoice.number, response.text)

            except Exception as e:
                _logger.exception("Exception lors de l'envoi Invoice %s : %s", invoice.number, e)
