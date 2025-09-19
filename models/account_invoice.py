# -*- coding: utf-8 -*-
from odoo import models, api
import logging
import requests
import json

_logger = logging.getLogger(__name__)


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    @api.multi
    def action_invoice_open(self):
        """Déclenche l'envoi lors de la comptabilisation"""
        res = super(AccountInvoice, self).action_invoice_open()
        for inv in self:
            try:
                inv._send_full_record_to_external_odoo()
            except Exception as e:
                _logger.exception("Erreur transfert Invoice %s : %s", inv.number, e)
        return res

    def _send_full_record_to_external_odoo(self):
        self.ensure_one()
        try:
            # lire tous les champs dynamiquement
            fields = list(self._fields.keys())
            data = self.read(fields)[0]

            # Lecture de l'URL configurable
            base_url = self.env['ir.config_parameter'].sudo().get_param('external_odoo.base_url', default=False)
            if not base_url:
                _logger.error(
                    "Aucune URL configurée (external_odoo.base_url). Impossible d'envoyer la facture %s",
                    self.number
                )
                return False

            url = "{}/odoo_sync/account_invoice".format(base_url)
            headers = {"Content-Type": "application/json"}  # pas de token

            # Log avant envoi
            _logger.info(
                "Données à envoyer pour Invoice %s : %s",
                self.number,
                json.dumps(data, indent=2, default=str)
            )

            response = requests.post(url, headers=headers, data=json.dumps(data, default=str), timeout=15)

            if response.status_code == 200:
                _logger.info("Invoice %s envoyé avec succès à l'Odoo externe", self.number)
            else:
                _logger.error(
                    "Erreur %s envoi Invoice %s : %s",
                    response.status_code,
                    self.number,
                    response.text
                )

        except Exception as e:
            _logger.exception("Exception lors de l'envoi Invoice %s : %s", self.number, e)
