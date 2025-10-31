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
    def send_to_external_odoo_purchase(self):
        """Envoi IMMÉDIAT vers Odoo 18"""
        for order in self:
            try:
                # Préparer les données de base
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

                # Ajouter les données supplémentaires
                data['order_lines_data'] = order_lines_data
                
                # Ajouter partner_ref s'il existe
                if order.partner_ref:
                    data['partner_ref'] = order.partner_ref
                
                # Ajouter les informations du projet s'il existe
                if order.dossier_id:
                    data['dossier_data'] = {
                        'name': order.dossier_id.name,
                        'project_name': order.dossier_id.project_name if hasattr(order.dossier_id, 'project_name') else order.dossier_id.name,
                        'ref_bc_customer': order.dossier_id.ref_bc_customer if hasattr(order.dossier_id, 'ref_bc_customer') else order.dossier_id.name,
                        'user_id': [order.dossier_id.user_id.id, order.dossier_id.user_id.name] if order.dossier_id.user_id else False,
                        'client_id': [order.dossier_id.partner_id.id, order.dossier_id.partner_id.name] if order.dossier_id.partner_id else False,
                    }
                
                # Supprimer les champs inutiles pour l'export
                if 'order_line' in data:
                    del data['order_line']
                if 'project_id' in data:
                    del data['project_id']

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
    
    def button_link_to_external_odoo_purchase(self):
        """Bouton manuel pour envoi IMMÉDIAT vers Odoo 18"""
        self.write({'transfer_state': 'pending'})
        self.send_to_external_odoo_purchase()
                