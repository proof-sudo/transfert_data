# -*- coding: utf-8 -*-
from odoo import models, api, fields
import logging
import requests
import json
import threading

_logger = logging.getLogger(__name__)

class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    transfer_state = fields.Selection([
        ('pending', 'Pending'),
        ('done', 'Done')
    ], string="Transfer State", default='pending')

    @api.multi
    def action_invoice_open(self):
        """Déclenche l'envoi asynchrone lors de la validation"""
        res = super(AccountInvoice, self).action_invoice_open()
        for invoice in self:
            _logger.info("Invoice %s validée, transfert asynchrone prévu", invoice.number)
            threading.Thread(target=self._send_async, args=(invoice.id,)).start()
        return res

    @api.model
    def _send_async(self, invoice_id):
        """Méthode thread-safe pour envoyer l'enregistrement"""
        invoice = self.browse(invoice_id)
        try:
            invoice._send_to_external_odoo()
        except Exception as e:
            _logger.exception("Erreur envoi asynchrone Invoice %s : %s", invoice.number, e)

    @api.multi
    def _send_to_external_odoo(self):
        """Envoi synchronisé de la facture vers l'Odoo externe"""
        self.ensure_one()
        try:
            # Lire dynamiquement tous les champs
            fields = list(self._fields.keys())
            data = self.read(fields)[0]

            # Récupérer l'URL configurée
            config = self.env['transfer_to_odoo17.config'].sudo().search([], limit=1)
            base_url = config.external_odoo_base_url if config else False

            if not base_url:
                _logger.error("Aucune URL configurée. Invoice %s non envoyé", self.number)
                return False

            url = "{}/odoo_sync/account_invoice".format(base_url)
            headers = {"Content-Type": "application/json"}

            _logger.info("Données à envoyer pour Invoice %s : %s", self.number, json.dumps(data, indent=2, default=str))
            response = requests.post(url, headers=headers, data=json.dumps(data, default=str), timeout=15)

            if response.status_code == 200:
                _logger.info("Invoice %s envoyé avec succès", self.number)
                self.transfer_state = 'done'
            else:
                _logger.error("Erreur %s envoi Invoice %s : %s", response.status_code, self.number, response.text)

        except Exception as e:
            _logger.exception("Exception lors de l'envoi Invoice %s : %s", self.number, e)
