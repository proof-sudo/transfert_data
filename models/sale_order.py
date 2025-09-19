from odoo import models, api, fields, SUPERUSER_ID
import logging
import requests
import json
import threading

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
            _logger.info("SaleOrder %s confirmée, transfert asynchrone prévu", order.name)
            threading.Thread(target=self._send_threadsafe, args=(order.id,)).start()
        return res

    @api.model
    def _send_threadsafe(self, order_id):
        """Thread sûr avec nouvel env et curseur ouvert"""
        with api.Environment.manage():
            env = api.Environment(self.env.cr, SUPERUSER_ID, {})
            order = env['sale.order'].browse(order_id)
            try:
                order._send_to_external()
            except Exception as e:
                _logger.exception("Erreur transfert SaleOrder %s : %s", order.name, e)

    @api.multi
    def _send_to_external(self):
        self.ensure_one()
        try:
            data = self.read(list(self._fields.keys()))[0]
            config = self.env['transfer_to_odoo17.config'].sudo().search([], limit=1)
            base_url = getattr(config, 'external_odoo_base_url', False)
            if not base_url:
                _logger.error("Aucune URL configurée. SaleOrder %s non envoyé", self.name)
                return

            url = f"{base_url}/odoo_sync/sale_order"
            headers = {"Content-Type": "application/json"}

            _logger.info("Envoi SaleOrder %s : %s", self.name, json.dumps(data, indent=2, default=str))
            response = requests.post(url, headers=headers, data=json.dumps(data, default=str), timeout=15)

            if response.status_code == 200:
                _logger.info("SaleOrder %s envoyé avec succès", self.name)
                self.transfer_state = 'done'
            else:
                _logger.error("Erreur %s envoi SaleOrder %s : %s", response.status_code, self.name, response.text)

        except Exception as e:
            _logger.exception("Exception lors de l'envoi SaleOrder %s : %s", self.name, e)
