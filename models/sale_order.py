# -*- coding: utf-8 -*-
from odoo import models, api, SUPERUSER_ID
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
                order._send_full_record_to_external_odoo()
            except Exception as e:
                _logger.exception("Erreur transfert SaleOrder %s : %s", order.name, e)
        return res

    def _send_full_record_to_external_odoo(self):
        self.ensure_one()
        try:
            fields = list(self._fields.keys())
            data = self.read(fields)[0]

            base_url = self.env['transfer_to_odoo17.config'].sudo().search([], limit=1).external_odoo_base_url
            _logger.info("URL récupérée pour SaleOrder %s : %s", self.name, base_url)

            if not base_url:
                _logger.error("Aucune URL configurée dans transfer_to_odoo17.config. SaleOrder %s non envoyé", self.name)
                return False

            url = "{}/odoo_sync/sale_order".format(base_url)
            headers = {"Content-Type": "application/json"}

            _logger.info("Données à envoyer pour SaleOrder %s : %s", self.name, json.dumps(data, indent=2, default=str))
            response = requests.post(url, headers=headers, data=json.dumps(data, default=str), timeout=15)

            if response.status_code == 200:
                _logger.info("SaleOrder %s envoyé avec succès à l'Odoo externe", self.name)
            else:
                _logger.error("Erreur %s envoi SaleOrder %s : %s", response.status_code, self.name, response.text)

        except Exception as e:
            _logger.exception("Exception lors de l'envoi SaleOrder %s : %s", self.name, e)
