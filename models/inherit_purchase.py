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


    @api.multi
    def button_confirm(self):
        res = super(PurchaseOrder, self).button_confirm()
        for order in self:
            _logger.info("Commande FOURNISSEUR  %s confirmée, transfert prévu via Action Serveur", order.name)
            order.transfer_state = 'pending'
        return res

    @api.multi
    def send_to_external_odoo_purchase(self):
        for order in self:
            try:
                # Dictionnaire de base pour le bon de commande fournisseur
                data = order.read(list(order._fields.keys()))[0]

                # Construction des lignes d'achat
                order_lines_data = []
                for line in order.order_line: # Le champ reste 'order_line'
                    line_data = {
                        # Champs clés pour une ligne d'achat :
                        'product_id': [line.product_id.id, line.product_id.name] if line.product_id else [False, 'Produit inconnu'],
                        'product_qty': line.product_qty,        # Changement : utilise 'product_qty' au lieu de 'product_uom_qty'
                        'price_unit': line.price_unit,
                        # Le champ taxe est 'taxes_id' sur purchase.order.line
                        'taxes_id': [(6, 0, line.taxes_id.ids)] if line.taxes_id else [],
                        'name': line.name,
                        'date_planned': str(line.date_planned),  # Optionnel: Ajout de la date planifiée, convertie en string
                        'amount_total': line.price_subtotal,
                    }
                    order_lines_data.append(line_data)

                data['order_lines_data'] = order_lines_data
                if 'order_line' in data:
                    del data['order_line']

                # Récupération de l'URL du service externe
                # NOTE : Vous utiliserez probablement une URL différente pour l'achat !
                base_url = self.env['transfer_to_odoo17.config'].get_external_url()
                url = "%s/odoo_sync/purchase_order" % base_url # Changement d'endpoint (suggestion)
                headers = {"Content-Type": "application/json"}

                _logger.info("Données à envoyer pour le BCF %s : URL :: %s :: %s", order.name, url, json.dumps(data, indent=2, default=str))
                response = requests.post(url, headers=headers, data=json.dumps(data, default=str), timeout=15)

                if response.status_code == 200:
                    _logger.info("BCF %s envoyé avec succès", order.name)
                    order.transfer_state = 'done'
                else:
                    _logger.error("Erreur %s lors de l'envoi du BCF %s : %s", response.status_code, order.name, response.text)

            except Exception as e:
                _logger.exception("Exception lors de l'envoi du BCF %s : %s", order.name, e)