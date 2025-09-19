from odoo import models, api, fields
import logging
import requests
import json

_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = "sale.order"

    transfer_state = fields.Selection([
        ('pending', 'Pending'),
        ('done', 'Done')
    ], string="Transfer State", default='pending')

    @api.multi
    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        for order in self:
            _logger.info("SaleOrder %s confirmée, transfert prévu via Action Server", order.name)
            # On ne lance plus de thread ici
            order.transfer_state = 'pending'
        return res

    @api.multi
    def send_to_external_odoo(self):
        """Méthode appelée via Action Server"""
        for order in self:
            try:
                data = order.read(list(order._fields.keys()))[0]

                base_url = self.env['transfer_to_odoo17.config'].sudo().search([], limit=1).external_odoo_base_url
                if not base_url:
                    _logger.error("Aucune URL configurée. SaleOrder %s non envoyé", order.name)
                    continue

                url = "{}/odoo_sync/sale_order".format(base_url)
                headers = {"Content-Type": "application/json"}

                _logger.info("Données à envoyer pour SaleOrder %s : %s", order.name, json.dumps(data, indent=2, default=str))
                response = requests.post(url, headers=headers, data=json.dumps(data, default=str), timeout=15)

                if response.status_code == 200:
                    _logger.info("SaleOrder %s envoyé avec succès", order.name)
                    order.transfer_state = 'done'
                else:
                    _logger.error("Erreur %s envoi SaleOrder %s : %s", response.status_code, order.name, response.text)

            except Exception as e:
                _logger.exception("Exception lors de l'envoi SaleOrder %s : %s", order.name, e)
