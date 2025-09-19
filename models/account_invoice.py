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
                inv._send_full_record_to_odoo17()
            except Exception as e:
                _logger.exception("❌ Erreur transfert Invoice %s : %s", inv.number, e)
        return res

    def _send_full_record_to_odoo17(self):
        self.ensure_one()
        try:
            fields = list(self._fields.keys())
            data = self.read(fields)[0]

            url = "https://www.google.com"
            # headers = {"Content-Type": "application/json", "Authorization": "Bearer SECRET_TOKEN"}
            response = requests.post(url, data=json.dumps(data), timeout=15)

            if response.status_code == 200:
                _logger.info("✅ Invoice %s envoyé avec succès à Odoo17", self.number)
            else:
                _logger.error("❌ Erreur %s envoi Invoice %s : %s", response.status_code, self.number, response.text)
        except Exception as e:
            _logger.exception("⚠️ Exception lors de l'envoi Invoice %s : %s", self.number, e)
