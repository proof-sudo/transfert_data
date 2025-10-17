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
        """Confirme la commande et marque pour envoi"""
        res = super(PurchaseOrder, self).button_confirm()
        self.write({'transfer_state': 'pending'})
        _logger.info("📋 BCF %s confirmé, envoi programmé", self.mapped('name'))
        return res

    def _prepare_purchase_data(self):
        """Prépare les données structurées pour l'API externe"""
        self.ensure_one()
        return {
            'purchase_order': {
                'id': self.id,
                'name': self.name,
                'partner': self.partner_id and {
                    'id': self.partner_id.id,
                    'name': self.partner_id.name,
                    'email': self.partner_id.email,
                    'ref': self.partner_id.ref,
                } or None,
                'company': self.company_id and {
                    'id': self.company_id.id,
                    'name': self.company_id.name,
                } or None,
                'date_order': self.date_order.isoformat() if self.date_order else None,
                'amount_total': self.amount_total,
                'currency': self.currency_id and self.currency_id.name,
                'state': self.state,
                'order_lines': [
                    self._prepare_order_line_data(line)
                    for line in self.order_line
                ]
            }
        }

    def _prepare_order_line_data(self, line):
        """Prépare les données d'une ligne de commande"""
        return {
            'product': line.product_id and {
                'id': line.product_id.id,
                'name': line.product_id.name,
                'default_code': line.product_id.default_code,
                'barcode': line.product_id.barcode,
            } or None,
            'quantity': line.product_qty,
            'price_unit': line.price_unit,
            'price_subtotal': line.price_subtotal,
            'taxes': [
                {'id': tax.id, 'name': tax.name, 'amount': tax.amount}
                for tax in line.taxes_id
            ],
            'description': line.name,
            'date_planned': line.date_planned.isoformat() if line.date_planned else None,
            'uom': line.product_uom and {
                'id': line.product_uom.id,
                'name': line.product_uom.name,
            } or None,
        }

    @api.multi
    def send_to_external_odoo_purchase(self):
        """Envoie la commande vers Odoo 17 externe"""
        for order in self:
            try:
                data = order._prepare_purchase_data()
                base_url = self.env['transfer_to_odoo17.config'].get_external_url()
                url = f"{base_url}/odoo_sync/purchase_order"
                
                _logger.info("🚀 Transfert en cours Envoi BCF %s vers %s", order.name, url)
                response = requests.post(url, json=data, timeout=15)
                
                if response.status_code == 200:
                    order.transfer_state = 'done'
                    _logger.info("✅ BCF %s envoyé avec succès", order.name)
                else:
                    order.transfer_state = 'error'
                    _logger.error("❌ Erreur %s pour BCF %s: %s", 
                                response.status_code, order.name, response.text)
                        
            except requests.exceptions.Timeout:
                order.transfer_state = 'error'
                _logger.error("⏰ Timeout pour BCF %s", order.name)
                
            except requests.exceptions.ConnectionError:
                order.transfer_state = 'error'
                _logger.error("🔌 Erreur connexion pour BCF %s", order.name)
                
            except Exception as e:
                order.transfer_state = 'error'
                _logger.exception("❌ Exception pour BCF %s: %s", order.name, str(e))