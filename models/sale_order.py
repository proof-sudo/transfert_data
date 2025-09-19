# -*- coding: utf-8 -*-
from odoo import models, api
import logging
import requests
import json

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.multi
    def action_confirm(self):
        """Override action_confirm pour envoyer la commande vers un autre Odoo"""
        res = super(SaleOrder, self).action_confirm()
        for order in self:
            try:
                _logger.info(u"action_confirm appelée pour SaleOrder %s", order.name)
                order._send_full_record_to_external_odoo()
            except Exception as e:
                _logger.exception(u"Erreur transfert SaleOrder %s : %s", order.name, e)
        return res

    def _send_full_record_to_external_odoo(self):
        self.ensure_one()
        try:
            # lire tous les champs dynamiquement
            fields = list(self._fields.keys())
            data = self.read(fields)[0]

            # Lecture des paramètres dynamiques
            icp = self.env['ir.config_parameter'].sudo()
            base_url = icp.get_param('external_odoo.base_url', default=False)
            token = icp.get_param('external_odoo.token', default=False)

            if not base_url:
                _logger.error(u"Aucune URL configurée (external_odoo.base_url). Impossible d'envoyer la commande %s", self.name)
                return False

            if not token:
                _logger.warning(u"Aucun token configuré (external_odoo.token). L'appel sera fait sans authentification.")

            url = "{}/odoo_sync/sale_order".format(base_url)

            headers = {"Content-Type": "application/json"}
            if token:
                headers["Authorization"] = "Bearer {}".format(token)

            # Log avant envoi
            _logger.info(
                u"Données à envoyer pour SaleOrder %s : %s",
                self.name,
                json.dumps(data, indent=2, default=str)
            )

            response = requests.post(url, headers=headers, data=json.dumps(data, default=str), timeout=15)

            if response.status_code == 200:
                _logger.info(u"SaleOrder %s envoyé avec succès à l'Odoo externe", self.name)
            else:
                _logger.error(
                    u"Erreur %s envoi SaleOrder %s : %s",
                    response.status_code,
                    self.name,
                    response.text
                )

        except Exception as e:
            _logger.exception(u"Exception lors de l'envoi SaleOrder %s : %s", self.name, e)
