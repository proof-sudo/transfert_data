from odoo import models, api, fields
import logging
import requests
import json

_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = "sale.order"

    transfer_state = fields.Selection([
        ('pending', 'En attente'),
        ('done', 'Terminé')
    ], string="État de transfert", default='pending')

    @api.multi
    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        for order in self:
            _logger.info("Commande %s confirmée, transfert prévu via Action Serveur", order.name)
            order.transfer_state = 'pending'
        return res

    @api.multi
    def send_to_external_odoo(self):
        for order in self:
            try:
                # Dictionnaire de base pour la commande
                data = order.read(list(order._fields.keys()))[0]

                # Construction des lignes avec les infos produit/qty/pu/taxe
                order_lines_data = []
                for line in order.order_line:
                    line_data = {
                        'product_id': [line.product_id.id, line.product_id.name] if line.product_id else [False, 'Produit inconnu'],
                        'product_uom_qty': line.product_uom_qty,
                        'price_unit': line.price_unit,
                        'taxes_id': [(6, 0, line.tax_id.ids)] if line.tax_id else [],
                        'name': line.name,
                        'amount_total': line.price_subtotal,
                    }
                    order_lines_data.append(line_data)

                data['order_lines_data'] = order_lines_data  # Ajout des lignes complètes
                # Supprimer l'ancien order_line qui ne contient qu'un ID
                if 'order_line' in data:
                    del data['order_line']

                base_url = "https://proof-sudo-neurones-project-test-24333026.dev.odoo.com"
                url = "{}/odoo_sync/sale_order".format(base_url)
                headers = {"Content-Type": "application/json"}

                _logger.info("Données à envoyer pour la commande %s : URL :: %s :: %s", order.name, url, json.dumps(data, indent=2, default=str))
                response = requests.post(url, headers=headers, data=json.dumps(data, default=str), timeout=15)

                if response.status_code == 200:
                    _logger.info("Commande %s envoyée avec succès", order.name)
                    order.transfer_state = 'done'
                else:
                    _logger.error("Erreur %s lors de l'envoi de la commande %s : %s", response.status_code, order.name, response.text)

            except Exception as e:
                _logger.exception("Exception lors de l'envoi de la commande %s : %s", order.name, e)

