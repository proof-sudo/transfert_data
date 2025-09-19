from odoo import models, api, fields
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
            # Lancement asynchrone dans un thread
            threading.Thread(target=self._send_full_record_to_external_odoo_safe, args=(order.id,)).start()
        return res

    @api.model
    def _send_full_record_to_external_odoo_safe(self, order_id):
        """Récupère la commande par ID et appelle la fonction de transfert en mode safe."""
        order = self.browse(order_id)
        try:
            order._send_to_external_odoo()
        except Exception as e:
            _logger.exception("Erreur envoi asynchrone SaleOrder %s : %s", order.name, e)

    @api.multi
    def _send_to_external_odoo(self):
        self.ensure_one()
        try:
            fields = list(self._fields.keys())
            data = self.read(fields)[0]

            base_url = self.env['transfer_to_odoo17.config'].sudo().search([], limit=1).external_odoo_base_url
            if not base_url:
                _logger.error("Aucune URL configurée. SaleOrder %s non envoyé", self.name)
                return False

            url = "{}/odoo_sync/sale_order".format(base_url)
            headers = {"Content-Type": "application/json"}

            _logger.info("Données à envoyer pour SaleOrder %s : %s", self.name, json.dumps(data, indent=2, default=str))
            response = requests.post(url, headers=headers, data=json.dumps(data, default=str), timeout=15)

            if response.status_code == 200:
                _logger.info("SaleOrder %s envoyé avec succès", self.name)
                self.transfer_state = 'done'
            else:
                _logger.error("Erreur %s envoi SaleOrder %s : %s", response.status_code, self.name, response.text)

        except Exception as e:
            _logger.exception("Exception lors de l'envoi SaleOrder %s : %s", self.name, e)
