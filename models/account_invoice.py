# -*- coding: utf-8 -*-
from odoo import models, api, fields
import logging
import requests
import json

_logger = logging.getLogger(__name__)

class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    transfer_state = fields.Selection([
        ('pending', 'En attente'),
        ('done', 'Terminé')
    ], string="État de transfert", default='pending')

    @api.multi
    def action_invoice_open(self):
        res = super(AccountInvoice, self).action_invoice_open()
        for invoice in self:
            _logger.info("Facture %s validée, transfert prévu via Action Serveur", invoice.number)
            invoice.transfer_state = 'pending'
        return res

    @api.multi
    def send_invoice_to_external_odoo(self):
        for invoice in self:
            try:
                data = invoice.read(list(invoice._fields.keys()))[0]
                config = self.env['transfer_to_odoo17.config'].sudo().search([], limit=1)
                # base_url = config.external_odoo_base_url if config else False
                base_url = "https://proof-sudo-neurones-project.odoo.com"

                if not base_url:
                    _logger.error("Aucune URL configurée. Facture %s non envoyée", invoice.number)
                    continue

                url = "{}/odoo_sync/account_invoice".format(base_url)
                headers = {"Content-Type": "application/json"}

                _logger.info("Données à envoyer pour la facture %s : %s", invoice.number, json.dumps(data, indent=2, default=str))
                response = requests.post(url, headers=headers, data=json.dumps(data, default=str), timeout=15)

                if response.status_code == 200:
                    _logger.info("Facture %s envoyée avec succès", invoice.number)
                    invoice.transfer_state = 'done'
                else:
                    _logger.error("Erreur %s lors de l'envoi de la facture %s : %s", response.status_code, invoice.number, response.text)

            except Exception as e:
                _logger.exception("Exception lors de l'envoi de la facture %s : %s", invoice.number, e)
