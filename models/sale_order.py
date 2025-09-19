from odoo import models, api
import logging
import requests
import json

_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.multi
    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        for order in self:
            try:
                order._send_full_record_to_odoo17()
            except Exception as e:
                _logger.exception("❌ Erreur transfert SaleOrder %s : %s", order.name, e)
        return res

    def _send_full_record_to_odoo17(self):
        self.ensure_one()
        try:
            # lire tous les champs dynamiquement
            fields = list(self._fields.keys())
            data = self.read(fields)[0]

            url = "https://odoo17.example.com/odoo_sync/sale_order"
            headers = {"Content-Type": "application/json", "Authorization": "Bearer SECRET_TOKEN"}
            response = requests.post(url, headers=headers, data=json.dumps(data), timeout=15)

            if response.status_code == 200:
                _logger.info("✅ SaleOrder %s envoyé avec succès à Odoo17", self.name)
            else:
                _logger.error("❌ Erreur %s envoi SaleOrder %s : %s", response.status_code, self.name, response.text)

        except Exception as e:
            _logger.exception("⚠️ Exception lors de l'envoi SaleOrder %s : %s", self.name, e)
