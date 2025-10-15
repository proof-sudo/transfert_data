import json
import requests
import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    transfer_state = fields.Selection([
        ('pending', 'En attente'),
        ('done', 'Envoyé'),
        ('error', 'Erreur'),
    ], string="Statut d'envoi", default='pending')

    external_response = fields.Text("Réponse du serveur externe")

    @api.multi
    def button_confirm(self):
        res = super(PurchaseOrder, self).button_confirm()
        for order in self:
            _logger.info("Commande FOURNISSEUR  %s confirmée, transfert prévu via Action Serveur", order.name)
            order.transfer_state = 'pending'
        return res

    @api.multi
    def button_send_data(self):
        for order in self:
            try:
                # 1. Lire les données de la commande
                order_data = order.read()[0]

                # 2. Lire les lignes de commande
                order_lines = []
                for line in order.order_line:
                    line_data = line.read()[0]
                    order_lines.append(line_data)

                # 3. Ajouter les lignes au dictionnaire principal
                order_data['order_lines'] = order_lines

                # 4. Récupérer l'URL du serveur externe
                base_url = self.env['transfer_to_odoo17.config'].get_external_url()
                url = "%s/odoo_sync/purchase_order" % base_url
                headers = {"Content-Type": "application/json"}

                # 5. Debug
                _logger.info("Envoi du bon de commande fournisseur %s vers %s", order.name, url)
                _logger.debug("Payload JSON : %s", json.dumps(order_data, indent=2, default=str))

                # 6. Envoi de la requête POST
                response = requests.post(url, headers=headers, data=json.dumps(order_data, default=str), timeout=20)

                if response.status_code == 200:
                    _logger.info("Commande fournisseur %s envoyée avec succès", order.name)
                    order.transfer_state = 'done'
                else:
                    _logger.error("Erreur %s : %s", response.status_code, response.text)
                    order.transfer_state = 'error'

                order.external_response = response.text

            except Exception as e:
                _logger.exception("Exception lors de l'envoi de la commande fournisseur %s", order.name)
                order.transfer_state = 'error'
                order.external_response = str(e)
