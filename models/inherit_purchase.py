from odoo import models, fields, api
import json
import requests
import logging

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
        """Confirme la commande et marque pour envoi IMMÉDIAT"""
        res = super(PurchaseOrder, self).button_confirm()
        # Marquer comme pending - la règle auto déclenchera l'envoi
        self.write({'transfer_state': 'pending'})
        _logger.info("✅ BCF %s confirmée, marquée pour envoi IMMÉDIAT", self.mapped('name'))
        return res

    @api.multi
    def send_to_external_odoo_purchase(self):
        """Envoi IMMÉDIAT vers Odoo 17"""
        for order in self:
            try:
                # Préparer les données
                data = order.read(list(order._fields.keys()))[0]

                # Construction des lignes d'achat
                order_lines_data = []
                for line in order.order_line:
                    line_data = {
                        'product_id': [line.product_id.id, line.product_id.name] if line.product_id else [False, 'Produit inconnu'],
                        'product_qty': line.product_qty,
                        'price_unit': line.price_unit,
                        'taxes_id': [(6, 0, line.taxes_id.ids)] if line.taxes_id else [],
                        'name': line.name,
                        'date_planned': str(line.date_planned),
                        'amount_total': line.price_subtotal,
                    }
                    order_lines_data.append(line_data)

                data['order_lines_data'] = order_lines_data
                if 'order_line' in data:
                    del data['order_line']

                # Récupération de l'URL
                base_url = self.env['transfer_to_odoo17.config'].get_external_url()
                url = "%s/odoo_sync/purchase_order" % base_url
                headers = {"Content-Type": "application/json"}

                _logger.info("🚀 Envoi IMMÉDIAT BCF %s vers %s", order.name, url)
                response = requests.post(url, headers=headers, data=json.dumps(data, default=str), timeout=15)

                if response.status_code == 200:
                    _logger.info("✅ BCF %s envoyé avec succès", order.name)
                    order.transfer_state = 'done'
                else:
                    _logger.error("❌ Erreur %s pour BCF %s: %s", response.status_code, order.name, response.text)
                    order.transfer_state = 'error'

            except requests.exceptions.Timeout:
                _logger.error("⏰ Timeout pour BCF %s", order.name)
                order.transfer_state = 'error'
                
            except requests.exceptions.ConnectionError:
                _logger.error("🔌 Erreur connexion pour BCF %s", order.name)
                order.transfer_state = 'error'
                
            except Exception as e:
                _logger.exception("❌ Exception pour BCF %s: %s", order.name, str(e))
                order.transfer_state = 'error'